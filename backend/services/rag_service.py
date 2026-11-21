"""
RAG News Intelligence Service — FULLY REAL-TIME
- Google News RSS (primary — never blocked)
- MoneyControl + Economic Times scrapers (with rotating user agents)
- Multiple company name query variations
- FinBERT + India Credit Risk Dictionary scoring
- ChromaDB vectorisation
- Detailed logging so 0/100 never appears silently
"""
import os
import re
import asyncio
import aiohttp
import logging
import hashlib
import feedparser
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────
# ROTATING USER AGENTS (prevents blocking)
# ──────────────────────────────────────────────────────
try:
    from fake_useragent import UserAgent
    _ua = UserAgent()
    def random_ua() -> str:
        return _ua.random
except Exception:
    _USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    ]
    import random as _rnd
    def random_ua() -> str:
        return _rnd.choice(_USER_AGENTS)


# ──────────────────────────────────────────────────────
# FINBERT
# ──────────────────────────────────────────────────────
try:
    from transformers import pipeline
    finbert = pipeline("text-classification", model="yiyanghkust/finbert-tone", return_all_scores=True)
    logger.info("FinBERT loaded successfully in rag_service.")
except Exception as _fb_err:
    logger.warning(f"FinBERT not available in rag_service: {_fb_err}")
    finbert = None

# ──────────────────────────────────────────────────────
# CHROMADB
# ──────────────────────────────────────────────────────
try:
    import chromadb
    from chromadb.utils import embedding_functions
    _chroma_client = chromadb.Client()
    _ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    collection = _chroma_client.get_or_create_collection("creditiq_news_intelligence", embedding_function=_ef)
except BaseException as _ch_err:
    # BaseException: chromadb's Rust bindings can raise pyo3_runtime.PanicException.
    logger.warning(f"ChromaDB unavailable in rag_service: {_ch_err}")
    collection = None


# ──────────────────────────────────────────────────────
# INDIA CREDIT RISK DICTIONARY
# ──────────────────────────────────────────────────────
INDIA_CREDIT_RISK_DICT = {
    "HIGH": [
        "debt restructuring", "loan recall", "account npa", "insolvency petition", "winding up petition",
        "drt case filed", "promoter arrest", "ed raid", "income tax raid", "sfio investigation",
        "account classified fraud", "wilful defaulter", "nclt petition", "liquidation", "assignment of debt",
        "promoter pledging entire shareholding", "strategic debt restructuring", "one time settlement",
        "default", "dishonored cheque", "bounced", "fraud detected", "money laundering",
    ],
    "MEDIUM": [
        "cfo resignation", "ceo change", "auditor resignation", "delayed agm", "qualified audit report",
        "going concern", "working capital stress", "vendor payment delays", "rating downgrade", "negative outlook",
        "rating watch", "export order cancellation", "plant shutdown", "labour dispute", "major customer loss",
        "penalty imposed", "compliance notice",
    ],
    "LOW": [
        "management change", "expansion plans delayed", "minor regulatory notice", "tax demand under appeal",
        "competition increasing", "margin pressure",
    ],
}


def calculate_dictionary_score(text: str) -> float:
    text_lower = text.lower()
    score = 0.0
    for phrase in INDIA_CREDIT_RISK_DICT["HIGH"]:
        if phrase in text_lower:
            score += 30.0
    for phrase in INDIA_CREDIT_RISK_DICT["MEDIUM"]:
        if phrase in text_lower:
            score += 15.0
    for phrase in INDIA_CREDIT_RISK_DICT["LOW"]:
        if phrase in text_lower:
            score += 5.0
    return min(100.0, score)


def calculate_finbert_score(text: str) -> Optional[float]:
    if not finbert:
        return None
    try:
        results = finbert(text[:512])[0]
        for res in results:
            if res["label"] == "Negative":
                return res["score"] * 100.0
        return 0.0
    except Exception:
        return None


# ──────────────────────────────────────────────────────
# GOOGLE NEWS RSS  (primary — never blocked)
# ──────────────────────────────────────────────────────
def scrape_google_news_rss(query: str) -> List[Dict[str, Any]]:
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(url)
        results = []
        cutoff = datetime.now() - timedelta(days=90)
        for entry in feed.entries[:15]:
            pub = datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") and entry.published_parsed else datetime.now()
            if pub < cutoff:
                continue
            results.append({
                "source": "Google News RSS",
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("title", ""))[:300],
                "date": pub.strftime("%Y-%m-%d"),
                "text": entry.get("title", "") + " " + entry.get("summary", ""),
                "url": entry.get("link", ""),
            })
        logger.info(f"Google News RSS returned {len(results)} articles for query: {query[:60]}")
        return results
    except Exception as e:
        logger.warning(f"Google News RSS failed for '{query}': {e}")
        return []


# ──────────────────────────────────────────────────────
# NEWSAPI.ORG  (secondary, requires key)
# ──────────────────────────────────────────────────────
def scrape_newsapi(query: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("NEWS_API_KEY", "")
    if not api_key:
        return []
    try:
        import requests
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "apiKey": api_key,
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": 10,
                "from": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            },
            timeout=8,
        )
        data = r.json()
        results = []
        for art in data.get("articles", []):
            title = art.get("title", "") or ""
            desc = art.get("description", "") or ""
            results.append({
                "source": f"NewsAPI ({art.get('source', {}).get('name', 'Unknown')})",
                "title": title,
                "summary": desc[:300],
                "date": (art.get("publishedAt", "") or "")[:10] or datetime.now().strftime("%Y-%m-%d"),
                "text": title + " " + desc,
                "url": art.get("url", ""),
            })
        logger.info(f"NewsAPI returned {len(results)} articles for query: {query[:60]}")
        return results
    except Exception as e:
        logger.warning(f"NewsAPI failed for '{query}': {e}")
        return []


# ──────────────────────────────────────────────────────
# ASYNC SCRAPERS  (rotating UA)
# ──────────────────────────────────────────────────────
async def _fetch(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(
            url,
            headers={"User-Agent": random_ua()},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status == 200:
                return await r.text()
    except Exception:
        pass
    return ""


async def scrape_moneycontrol(session, query: str) -> List[Dict[str, Any]]:
    slug = query.lower().replace(" ", "-")[:50]
    url = f"https://www.moneycontrol.com/news/tags/{slug}.html"
    html = await _fetch(session, url)
    results = []
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.find_all("li", class_="clearfix")[:6]:
            h2 = item.find("h2")
            if not h2:
                continue
            title = h2.get_text(strip=True)
            p = item.find("p")
            summary = p.get_text(strip=True) if p else title
            results.append({
                "source": "MoneyControl",
                "title": title,
                "summary": summary,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "text": title + " " + summary,
            })
    logger.info(f"MoneyControl returned {len(results)} for '{query[:40]}'")
    return results


async def scrape_economic_times(session, query: str) -> List[Dict[str, Any]]:
    slug = query.replace(" ", "-")[:50]
    url = f"https://economictimes.indiatimes.com/topic/{slug}"
    html = await _fetch(session, url)
    results = []
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.find_all("div", class_="flr mt15")[:6]:
            h3 = item.find("h3")
            if not h3:
                continue
            title = h3.get_text(strip=True)
            p = item.find("p")
            summary = p.get_text(strip=True) if p else title
            results.append({
                "source": "Economic Times",
                "title": title,
                "summary": summary,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "text": title + " " + summary,
            })
    logger.info(f"Economic Times returned {len(results)} for '{query[:40]}'")
    return results


def build_queries(company_name: str, promoter_names: List[str] = None) -> List[str]:
    """The query variations tried for one company, in order."""
    promoters = promoter_names or []

    # Strip common suffixes for shorter query
    short_name = re.sub(
        r"\s+(pvt|private|ltd|limited|llp|inc|corp|co)\.?$",
        "",
        company_name,
        flags=re.IGNORECASE,
    ).strip()

    queries = [
        company_name,                        # Q1 exact
        short_name,                          # Q2 short
        f"{short_name} India",               # Q3 + India
        f"{short_name} fraud NBFC",          # Q4 risk context
    ]
    queries.extend(promoters[:2])            # Q5,Q6 promoter names
    return queries


async def run_all_scrapers(company_name: str, promoter_names: List[str] = None) -> List[Dict[str, Any]]:
    """Every query variation run across every source."""
    queries = build_queries(company_name, promoter_names)

    all_articles: List[Dict[str, Any]] = []
    seen_titles = set()

    # Google News RSS for all queries (sync, but fast)
    for q in queries:
        for art in scrape_google_news_rss(q):
            if art["title"] not in seen_titles:
                seen_titles.add(art["title"])
                all_articles.append(art)

    # NewsAPI
    for q in queries[:3]:
        for art in scrape_newsapi(q):
            if art["title"] not in seen_titles:
                seen_titles.add(art["title"])
                all_articles.append(art)

    # Async scrapers
    async with aiohttp.ClientSession() as session:
        tasks = []
        for q in queries[:2]:
            tasks.append(scrape_moneycontrol(session, q))
            tasks.append(scrape_economic_times(session, q))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                for art in res:
                    if art["title"] not in seen_titles:
                        seen_titles.add(art["title"])
                        all_articles.append(art)

    logger.info(f"Total unique articles gathered for '{company_name}': {len(all_articles)}")
    return all_articles


# ──────────────────────────────────────────────────────
# NO COVERAGE FOUND
# ──────────────────────────────────────────────────────
# There is deliberately no fallback article generator here. The previous one
# invented headlines about the named company when every scraper came back empty
# — "CFO exits <company> amid internal restructuring", "NSE flags <company> for
# disclosure delay" — and those strings then appeared in the credit memo as
# adverse media, attributed to Economic Times or MoneyControl, with a risk score
# derived from them. A headline about a real, named company must never be
# synthesised. When nothing is found, nothing is reported.
NO_COVERAGE_NOTE = (
    "No news coverage was found for this company. Every source returned empty: "
    "Google News RSS, NewsAPI (if a key is configured), MoneyControl and "
    "Economic Times. This is an absence of evidence, not evidence of good "
    "standing — a company with no media footprint scores the same as one with "
    "clean coverage, and the adverse-media check should be treated as not "
    "performed."
)


def _no_coverage_result(company_name: str, queries_tried: int) -> Dict[str, Any]:
    """The honest empty result: a neutral score and a statement that it is empty."""
    logger.warning("No news coverage found for '%s' across %d queries", company_name, queries_tried)
    return {
        "news_risk_score": 0.0,
        "signals": [],
        "total_articles_scanned": 0,
        "articles_scored": 0,
        "news_data_available": False,
        "note": NO_COVERAGE_NOTE,
        "date_range": "Last 90 Days",
        "sources_used": [],
        "query_variations_tried": queries_tried,
    }


# ──────────────────────────────────────────────────────
# MAIN CONTROLLER
# ──────────────────────────────────────────────────────
from services.external_apis import cache_get, cache_set


def get_news_intelligence(company_name: str, gstin: str) -> Dict[str, Any]:
    """
    MASTER PIPELINE: Scrape → Score → Vectorise → Return

    A score of 0 with `news_data_available: False` means no coverage was found.
    That is reported as such; no article is ever invented to fill the gap.
    """
    cache_key = f"news_rag_{hashlib.md5(company_name.encode()).hexdigest()}"
    cached = cache_get(cache_key)
    if cached:
        logger.info(f"News intelligence served from cache for '{company_name}'")
        return cached

    # 1. Scrape (async runners inside sync context)
    try:
        raw_articles = asyncio.run(run_all_scrapers(company_name))
    except Exception as e:
        logger.error(f"Scraper gather failed: {e}")
        raw_articles = []

    # 2. Nothing found: say so, with a neutral score, and stop.
    if not raw_articles:
        empty = _no_coverage_result(company_name, len(build_queries(company_name)))
        cache_set(cache_key, empty, 15 * 60)  # short cache: coverage may appear
        return empty

    # 3. Score every article
    processed: List[Dict[str, Any]] = []
    total_score = 0.0

    for art in raw_articles:
        full_text = art.get("text", art.get("title", ""))
        dict_score = calculate_dictionary_score(full_text)
        bert_score = calculate_finbert_score(full_text)

        if bert_score is None:
            final_score = dict_score
            logger.debug(f"  FinBERT unavailable for '{art['title'][:60]}' → dict_score={dict_score:.1f}")
        else:
            final_score = dict_score * 0.6 + bert_score * 0.4
            logger.debug(f"  '{art['title'][:60]}' dict={dict_score:.1f} bert={bert_score:.1f} final={final_score:.1f}")

        art["risk_score"] = round(final_score, 1)
        art["risk_level"] = (
            "CRITICAL" if final_score >= 70 else
            "HIGH" if final_score >= 40 else
            "MEDIUM" if final_score >= 15 else
            "LOW"
        )
        processed.append(art)
        total_score += final_score

    # 4. Aggregate score
    overall_score = round(total_score / len(processed), 1) if processed else 0.0
    logger.info(
        f"News intelligence for '{company_name}': {len(processed)} articles, "
        f"overall_score={overall_score}"
    )

    # 5. ChromaDB vectorisation (failure never skips article)
    if collection and processed:
        try:
            docs, metas, ids = [], [], []
            for i, art in enumerate(processed):
                docs.append(art["text"][:2000])
                metas.append({
                    "source": art["source"],
                    "date": art["date"],
                    "risk_score": art["risk_score"],
                    "company": company_name,
                })
                ids.append(f"{company_name.replace(' ', '_')}_{i}_{hashlib.md5(art['title'].encode()).hexdigest()[:8]}")
            collection.upsert(documents=docs, metadatas=metas, ids=ids)
        except Exception as e:
            logger.warning(f"ChromaDB upsert failed (articles still scored): {e}")

    # 6. Top signals
    processed.sort(key=lambda x: x["risk_score"], reverse=True)
    signals_output = [
        {
            "signal": art["title"],
            "source": art["source"],
            "date": art["date"],
            "risk": art["risk_level"],
            "exact_quote": art["summary"][:150] + "..." if len(art.get("summary", "")) > 150 else art.get("summary", ""),
        }
        for art in processed[:5]
    ]

    result = {
        "news_risk_score": overall_score,
        "signals": signals_output,
        "total_articles_scanned": len(raw_articles),
        "articles_scored": len(processed),
        "news_data_available": True,
        "date_range": "Last 90 Days",
        "sources_used": list({a["source"] for a in processed}),
        "query_variations_tried": len(build_queries(company_name)),
    }

    cache_set(cache_key, result, 2 * 3600)  # 2-hour cache (was 6h)
    return result


# ──────────────────────────────────────────────────────
# CHROMADB RETRIEVAL
# ──────────────────────────────────────────────────────
def query_news_context(company_name: str, question: str, n_results: int = 4) -> Dict[str, Any]:
    """
    Retrieve the stored coverage most similar to `question` for one company.

    This is the vector search the collection was being populated for. It
    replaces a function in scoring_service that returned three hardcoded
    constants — among them a flat +12.5 added to every company's news score —
    under a comment saying it "mocks the LangChain execution against ChromaDB".

    Returns the retrieved documents, or an explicit unavailable/empty result.
    Nothing here modifies any score.
    """
    if collection is None:
        return {"available": False, "reason": "ChromaDB is not available in this process", "documents": []}

    try:
        hits = collection.query(
            query_texts=[question],
            n_results=n_results,
            where={"company": company_name},
        )
    except Exception as exc:
        logger.warning("ChromaDB query failed for '%s': %s", company_name, exc)
        return {"available": False, "reason": f"query failed: {exc}", "documents": []}

    documents = (hits.get("documents") or [[]])[0]
    metadatas = (hits.get("metadatas") or [[]])[0]
    distances = (hits.get("distances") or [[]])[0]

    return {
        "available": True,
        "query": question,
        "documents": [
            {
                "text": text,
                "source": (meta or {}).get("source"),
                "date": (meta or {}).get("date"),
                "risk_score": (meta or {}).get("risk_score"),
                "distance": round(float(distance), 4) if distance is not None else None,
            }
            for text, meta, distance in zip(documents, metadatas, distances)
        ],
    }
