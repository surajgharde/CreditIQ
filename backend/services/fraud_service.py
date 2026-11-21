"""
Fraud screening: GST mismatch, circular trading and director cross-entity checks.

Each check runs against real data — statement lines pulled out of the uploaded
documents, or the GSTN/MCA APIs when credentials are configured. When the data
is not there, the check reports UNKNOWN and says what is missing. It does not
manufacture a finding.

Demo mode
---------
Setting CREDITIQ_DEMO_MODE=true makes the missing checks fall back to
procedurally generated signals, so the pipeline can be walked through end to end
without live API credentials. Everything generated that way is marked
`"synthetic": True`, its description is prefixed with the SYNTHETIC_PREFIX
below, and `fraud_data_synthetic` is set on the aggregate result, so a generated
finding cannot be mistaken for a real one in the API, the dashboard or the memo.
Demo mode is off unless the environment variable is set.
"""
import hashlib
import os
import random
from typing import Any, Dict, List

import networkx as nx

# Prefix carried by every generated description, all the way into the memo.
SYNTHETIC_PREFIX = "[SYNTHETIC — DEMO MODE, NOT REAL DATA] "


def demo_mode_enabled() -> bool:
    """True when CREDITIQ_DEMO_MODE is set to an affirmative value."""
    return os.getenv("CREDITIQ_DEMO_MODE", "").strip().lower() in ("1", "true", "yes", "on")


def _get_seeded_random(seed_str: str) -> random.Random:
    """Deterministic generator, so one company's demo signals do not change per run."""
    return random.Random(int(hashlib.md5(seed_str.encode()).hexdigest(), 16))


def _unavailable(signal_type: str, source: str, description: str) -> Dict[str, Any]:
    """
    The result of a check that could not run.

    risk_level is UNKNOWN and confidence is 0: a check that did not run is not
    the same as a check that passed, and several of these used to return GOOD
    with 100% confidence, which read as a clean bill of health on the memo.
    """
    return {
        "signal_type": signal_type,
        "risk_level": "UNKNOWN",
        "description": description,
        "evidence_amount": 0.0,
        "confidence_score": 0.0,
        "source": source,
        "synthetic": False,
        "data_available": False,
        "raw_data": {},
    }

# Sub-system 1: Real GST Lie Detector
def analyze_gst_mismatches(gstin: str, uploaded_gst_data: List[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    Compares GSTR-2A (Vendor declared) vs GSTR-3B (Company claimed) 
    over a 12-month period to detect Input Tax Credit (ITC) fraud.
    """
    total_2a_amount = 0.0
    total_3b_amount = 0.0
    late_filings = 0

    if uploaded_gst_data:
        gst_records = uploaded_gst_data
    else:
        from services.external_apis import get_filing_history
        api_data = get_filing_history(gstin)
        if api_data and isinstance(api_data[0], dict) and "error" in api_data[0]:
             return _unavailable(
                 "GST_MISMATCH",
                 "GSTN API",
                 f"GST source offline: {api_data[0]['error']}. GSTR-2A against "
                 "GSTR-3B could not be compared, so input tax credit mismatch "
                 "was not tested.",
             )
        gst_records = []
        for rec in api_data:
            gst_records.append({
                "month": rec.get("return_period", "Unknown"),
                "gstr_2a": float(rec.get("tax_payable", 0.0)),
                "gstr_3b": float(rec.get("tax_paid", 0.0)),
                "filed_on_time": rec.get("status", "").lower() == "filed"
            })
            
    if not gst_records:
        return _unavailable(
            "GST_MISMATCH",
            "GSTN API",
            "No GST return data available from the uploaded documents or the "
            "GSTN API, so input tax credit mismatch was not tested.",
        )

    for record in gst_records:
        try:
            total_2a_amount += float(record.get("gstr_2a", 0.0))
            total_3b_amount += float(record.get("gstr_3b", 0.0))
        except (ValueError, TypeError):
            pass
            
        if "filed_on_time" in record and not record["filed_on_time"]:
            late_filings += 1

    mismatch_amount = abs(total_3b_amount - total_2a_amount)
    
    # Mathematical confidence based on total volume
    mismatch_percentage = 0.0
    if total_3b_amount > 0:
        mismatch_percentage = (mismatch_amount / total_3b_amount) * 100

    # User defined strict risk thresholds
    if mismatch_percentage > 30.0:
        risk_level = "HIGH"
    elif mismatch_percentage > 15.0:
        risk_level = "MEDIUM"
    elif mismatch_percentage > 5.0:
        risk_level = "LOW"
    else:
        risk_level = "GOOD"

    confidence_score = min(100.0, mismatch_percentage * 3.0) # Scales confidence up as mismatch grows

    return {
        "signal_type": "GST_MISMATCH",
        "risk_level": risk_level,
        "description": f"Annual GSTR-2A shows ₹{total_2a_amount:,.2f} while GSTR-3B claims ₹{total_3b_amount:,.2f}. Exact mismatch of ₹{mismatch_amount:,.2f} ({mismatch_percentage:.1f}%). {late_filings} late filings detected.",
        "evidence_amount": float(mismatch_amount),
        "confidence_score": round(confidence_score, 1),
        "source": "GSTN Document/API Comparison",
        "synthetic": False,
        "data_available": True,
        "raw_data": {
            "mismatch_percentage": round(mismatch_percentage, 2),
            "late_filings": late_filings
        }
    }


# Sub-system 2: Real Circular Trading Graph
def detect_circular_trading(target_gstin: str, transaction_ledgers: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Constructs a Directed Graph of all buyers/suppliers and runs NetworkX 
    cycle detection to find money moving in loops definitively.
    """
    G = nx.DiGraph()

    if not transaction_ledgers:
        unavailable = _unavailable(
            "CIRCULAR_TRADING",
            "NetworkX Analysis",
            "No bank statement or ledger transactions were provided, so cycle "
            "detection did not run and circular trading was not tested.",
        )
        unavailable["graph_data"] = {"nodes": [], "edges": []}
        return unavailable

    # Build the Actual NetworkX Mathematical Graph
    for trx in transaction_ledgers:
        u = trx["from_node"]
        v = trx["to_node"]
        amt = trx["amount"]
        # If edge exists, add to weight (multi-invoice)
        if G.has_edge(u, v):
            G[u][v]['weight'] += amt
        else:
            G.add_edge(u, v, weight=amt)
            
    # Execute actual simple cycle detection mapping algorithms
    cycles = list(nx.simple_cycles(G))
    
    suspicious_cycles = []
    total_rotated = 0.0
    circular_nodes_set = set()

    # Filter out trivial 2-node loops unless amounts perfectly match (Accomodation Bills)
    for cycle in cycles:
        if len(cycle) >= 3:
            # Check edge weights inside the cycle 
            cycle_amounts = []
            for i in range(len(cycle)):
                u = cycle[i]
                v = cycle[(i + 1) % len(cycle)]
                cycle_amounts.append(G[u][v]['weight'])
            
            # If standard deviation of amounts is extremely low, it's highly suspicious exact-value rotation
            min_amt = min(cycle_amounts)
            max_amt = max(cycle_amounts)
            
            # If all transfers in the loop are identical or within 5% of each other
            if (max_amt - min_amt) / max_amt < 0.05:
                suspicious_cycles.append({
                    "entities": cycle,
                    "volume": max_amt
                })
                total_rotated += max_amt
                for n in cycle:
                    circular_nodes_set.add(n)

    # Build exact PyVis readable formatting
    nodes_data = []
    for node in G.nodes():
        if node == "Target Firm" or node == target_gstin:
            color = "#1C335B" # Primary Blue
        elif node in circular_nodes_set:
            color = "#FF0000" # RED: Active in Fraud Loop
        elif any(G.has_edge(node, fraud) for fraud in circular_nodes_set):
            color = "#FFA500" # ORANGE: Transacting with bad actors
        else:
            color = "#008000" # GREEN: Clean
            
        nodes_data.append({"id": node, "label": node, "color": color})

    edges_data = []
    for u, v, data in G.edges(data=True):
        edges_data.append({
            "from": u,
            "to": v,
            "label": f"₹{data['weight']:,.0f}"
        })

    if not suspicious_cycles:
        return {
            "signal_type": "CIRCULAR_TRADING",
            "risk_level": "GOOD",
            "description": f"NetworkX cycle detection ran on {len(G.nodes())} transactional entities. No identical value loops found. Clean network.",
            "evidence_amount": 0.0,
            "confidence_score": 100.0,
            "source": "NetworkX Analysis",
            "synthetic": False,
            "data_available": True,
            "graph_data": {"nodes": nodes_data, "edges": edges_data}
        }

    return {
        "signal_type": "CIRCULAR_TRADING",
        "risk_level": "HIGH",
        "description": f"Suspicious exactly-matched value loops detected across {len(circular_nodes_set)} entities rotating ₹{total_rotated:,.2f} continuously.",
        "evidence_amount": float(total_rotated),
        "confidence_score": 98.5, # High network certainty
        "source": "NetworkX Graph Cycle Detection",
        "synthetic": False,
        "data_available": True,
        "graph_data": {
            "nodes": nodes_data,
            "edges": edges_data
        }
    }


# Sub-system 3: MCA Director cross-entity check
def analyze_mca_directors(dins: List[str]) -> Dict[str, Any]:
    """
    Queries MCA21 to map a promoter or director across their multi-entity
    corporate footprint, looking for Section 164 disqualification and defaults
    at associated entities.
    """
    total_exposure = 0.0
    highest_risk_level = "LOW"
    disqualified = False
    findings = []
    unreachable_dins: List[str] = []
    from services.external_apis import get_director_details

    if not dins:
        return _unavailable(
            "MCA_DIRECTOR",
            "MCA21",
            "No director identification numbers were supplied with the "
            "application, so the cross-entity director check did not run.",
        )

    evidence_val = 0.0

    for din in dins:
        dir_data = get_director_details(din)
        if "error" in dir_data:
             # The registry could not be reached for this DIN. Previously this
             # branch invented a corporate footprint for the director — an
             # exposure figure and, one time in twenty, a historical default at
             # a named entity. A finding about a real person's regulatory
             # history cannot be generated; the DIN is recorded as unchecked.
             unreachable_dins.append(din)
             findings.append(
                 f"DIN {din}: MCA21 lookup failed ({dir_data['error']}). Not checked."
             )
             continue
        # Parse the structured return natively from our external_apis layer
        data = dir_data
        
        if data.get("status") == "Disqualified":
            disqualified = True
            highest_risk_level = "HIGH"
            findings.append(f"Director {data.get('name')} ({din}) is formally disqualified.")
            
        # Our external_apis mock for get_director_details doesn't return companies natively unless we query further,
        # but to satisfy types let's safely read if present
        for co in data.get("companies", []):
            try:
                exp = float(co.get("exposure", 0.0))
                total_exposure += exp
                if co.get("default"):
                    highest_risk_level = "HIGH"
                    evidence_val += exp
                    findings.append(f"Associated Entity ({co.get('name')}) defaulted on ₹{exp:,.0f} in {co.get('default_year')}.")
            except Exception:
                pass
                    
    # Saftey Ratio checks: High exposure relative to known thresholds
    if highest_risk_level != "HIGH" and total_exposure > 500000000.0:
        highest_risk_level = "MEDIUM"
        findings.append(f"Director cross-entity financial exposure is abnormally large (₹{total_exposure:,.0f}).")

    checked = [din for din in dins if din not in unreachable_dins]
    if not checked:
        # Nothing was actually looked up.
        unavailable = _unavailable(
            "MCA_DIRECTOR",
            "MCA21",
            "MCA21 could not be reached for any supplied DIN, so the "
            "cross-entity director check did not run. " + " | ".join(findings),
        )
        unavailable["raw_data"] = {"dins_supplied": list(dins), "dins_checked": []}
        return unavailable

    if highest_risk_level != "HIGH" and total_exposure > 500000000.0:
        highest_risk_level = "MEDIUM"
        findings.append(f"Director cross-entity financial exposure is abnormally large (₹{total_exposure:,.0f}).")

    if not findings:
        highest_risk_level = "LOW"
        findings.append("All associated historical entities carry clean regulatory and debt histories.")

    return {
        "signal_type": "MCA_DIRECTOR",
        "risk_level": highest_risk_level,
        "description": " | ".join(findings),
        "evidence_amount": float(evidence_val) if evidence_val > 0 else float(total_exposure),
        "confidence_score": round(100.0 * len(checked) / len(dins), 1),
        "source": "MCA21 Regulatory Database & CIBIL",
        "synthetic": False,
        "data_available": True,
        "raw_data": {
            "is_disqualified": disqualified,
            "total_corporate_footprint": total_exposure,
            "dins_supplied": list(dins),
            "dins_checked": checked,
            "dins_unreachable": unreachable_dins,
        }
    }


# ---------------------------------------------------------------------------
# DEMO MODE GENERATORS
#
# Only reachable when CREDITIQ_DEMO_MODE is set. Everything they produce is
# marked synthetic by _mark_synthetic below before it leaves this module.
# ---------------------------------------------------------------------------
def _demo_gst_records(generator: random.Random, ocr_revenue: float) -> List[Dict[str, Any]]:
    """Twelve months of GSTR-2A/3B figures around the extracted revenue."""
    variance = ocr_revenue * 0.12
    monthly_base = ocr_revenue / 12.0
    records = []
    for month in ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"):
        gstr_2a = monthly_base + generator.uniform(-variance, variance)
        gstr_3b = gstr_2a + generator.uniform(-variance * 0.5, variance * 2.0)
        records.append({
            "month": month,
            "gstr_2a": gstr_2a,
            "gstr_3b": gstr_3b,
            "filed_on_time": generator.random() > 0.15,
        })
    return records


def _demo_transaction_ledger(generator: random.Random, gstin: str,
                             ocr_revenue: float) -> List[Dict[str, Any]]:
    """A vendor network, half the time containing an exact-value three-hop loop."""
    variance = ocr_revenue * 0.12
    ledger: List[Dict[str, Any]] = []
    for _ in range(8):
        vendor = f"Vendor_0x{generator.randint(1000, 9999)}"
        ledger.append({"from_node": gstin, "to_node": vendor,
                       "amount": generator.uniform(100000, variance)})
        ledger.append({"from_node": vendor, "to_node": gstin,
                       "amount": generator.uniform(50000, variance * 0.8)})

    if generator.random() > 0.5:
        loop_amount = float(generator.randint(800000, 2500000))
        first = f"Shell_Company_{generator.randint(10, 99)}"
        second = f"Logistics_Corp_0x{generator.randint(10, 99)}"
        ledger.append({"from_node": gstin, "to_node": first, "amount": loop_amount})
        ledger.append({"from_node": first, "to_node": second, "amount": loop_amount})
        ledger.append({"from_node": second, "to_node": gstin, "amount": loop_amount})
    return ledger


def _mark_synthetic(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Stamp a generated signal so it cannot be read as a real finding."""
    signal["synthetic"] = True
    signal["data_available"] = False
    description = signal.get("description", "")
    if not description.startswith(SYNTHETIC_PREFIX):
        signal["description"] = SYNTHETIC_PREFIX + description
    return signal


# MAIN EXPORT: The master aggregation function called by 'routers/analyze.py'
def run_fraud_detection(gstin: str, cin: str, dins: List[str] = None, gst_data: List[Dict] = None, trx_data: List[Dict] = None, ocr_revenue: float = 50000000.0) -> Dict[str, Any]:
    """
    Run the three checks against whatever real data is available.

    A check with no data reports UNKNOWN and names what is missing — unless
    CREDITIQ_DEMO_MODE is set, in which case it runs on generated data and every
    resulting signal is marked synthetic.
    """
    demo = demo_mode_enabled()
    generator = _get_seeded_random(gstin + cin)
    synthetic_signals: List[str] = []

    # 1. GST: GSTR-2A against GSTR-3B.
    gst_synthetic = False
    if not gst_data and demo:
        gst_data = _demo_gst_records(generator, ocr_revenue)
        gst_synthetic = True
    signal_1_gst = analyze_gst_mismatches(gstin, gst_data)
    if gst_synthetic:
        _mark_synthetic(signal_1_gst)
        synthetic_signals.append("GST_MISMATCH")

    # 2. Circular trading: NetworkX cycle detection over the transaction graph.
    trx_synthetic = False
    if not trx_data and demo:
        trx_data = _demo_transaction_ledger(generator, gstin, ocr_revenue)
        trx_synthetic = True
    signal_2_circ = detect_circular_trading(gstin, trx_data)
    if trx_synthetic:
        _mark_synthetic(signal_2_circ)
        synthetic_signals.append("CIRCULAR_TRADING")

    # 3. MCA director cross-entity check.
    if not dins and demo:
        demo_din = f"0{generator.randint(1000000, 9999999)}"
        signal_3_mca = _mark_synthetic({
            "signal_type": "MCA_DIRECTOR",
            "risk_level": "LOW",
            "description": (
                f"Cross-entity audit of generated DIN {demo_din} across three "
                "connected holdings shows no disqualification and no historical "
                "debt default."
            ),
            "evidence_amount": 0.0,
            "confidence_score": 0.0,
            "source": "Generated in demo mode (MCA21 not queried)",
            "raw_data": {
                "is_disqualified": False,
                "total_corporate_footprint": generator.uniform(50000000, 200000000),
                "generated_din": demo_din,
            },
        })
        if generator.random() > 0.85:
            default_amount = float(generator.randint(10000000, 80000000))
            signal_3_mca["risk_level"] = "HIGH"
            signal_3_mca["description"] = (
                SYNTHETIC_PREFIX
                + f"Generated DIN {demo_din} maps to a suspended entity with a "
                f"historical default of ₹{default_amount:,.0f}. This is "
                "generated demo data about a fictitious entity."
            )
            signal_3_mca["evidence_amount"] = default_amount
        synthetic_signals.append("MCA_DIRECTOR")
    else:
        signal_3_mca = analyze_mca_directors(dins)

    signals_list = [signal_1_gst, signal_2_circ, signal_3_mca]

    # Aggregate: the worst real level wins. A synthetic signal never sets the
    # overall level, because that level drives the decision and the price.
    overall_risk = "LOW"
    total_evidence = 0.0
    checks_run = 0
    for signal in signals_list:
        if signal.get("synthetic"):
            continue
        if not signal.get("data_available", True):
            continue
        checks_run += 1
        total_evidence += signal.get("evidence_amount", 0.0)
        risk = signal.get("risk_level", "LOW")
        if risk == "HIGH":
            overall_risk = "HIGH"
        elif risk == "MEDIUM" and overall_risk != "HIGH":
            overall_risk = "MEDIUM"

    if checks_run == 0:
        overall_risk = "UNKNOWN"

    return {
        "fraud_risk_level": overall_risk,
        "total_evidence_amount": float(total_evidence),
        "signals": signals_list,
        "checks_run": checks_run,
        "checks_total": len(signals_list),
        "demo_mode": demo,
        "fraud_data_synthetic": bool(synthetic_signals),
        "synthetic_signal_types": synthetic_signals,
        # Expose the specific network graph up to the router layer trivially
        "graph_data": signal_2_circ.get("graph_data", {"nodes": [], "edges": []})
    }

