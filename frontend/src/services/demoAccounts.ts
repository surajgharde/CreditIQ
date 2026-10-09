/**
 * Demo company data — the single source of truth.
 *
 * Analysis.tsx gates on these identifiers and Dashboard.tsx renders the matching
 * payload. They used to keep separate copies of the identifier list, which drifted
 * apart and produced "No matching company data found" for a valid input: the gate
 * accepted one set while the dashboard matched another. Both now read from here.
 *
 * The backend demo lookup in backend/routers/cam.py keys off the same PANs, so
 * changing an identifier here means changing it there too.
 *
 * Every company below is fictional. No figure describes a real entity.
 */

export interface DemoResults {
    company: { company_name: string; cin_number: string; pan_number: string };
    decision: {
        decision: string;
        probability_of_default: number;
        recommended_loan_amount: number;
        recommended_interest_rate: number;
        data_quality_score: number;
    };
    fraud: {
        overall_fraud_risk: string;
        total_signals_found: number;
        signals: { description: string; confidence_score: number }[];
    };
    news: { news_risk_score: number; top_signals: { risk: string; signal: string }[] };
    recommendation: {
        decision_reasoning: string;
        conditions: string[];
        interest_rate_breakdown: string;
    };
    shap: {
        base_risk: number;
        final_pd: number;
        shap_factors: { name: string; impact: string }[];
    };
}

export interface DemoAccount {
    /** Identifiers that unlock this record: PAN and account number. */
    keys: string[];
    accountNumber: string;
    results: DemoResults;
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
    {
        keys: ['ZZZCS1001A', '45678219304'],
        accountNumber: '45678219304',
        results: {
            company: {
                company_name: 'Suryanex Industries Limited',
                cin_number: 'U28990MH2015PTC100001',
                pan_number: 'ZZZCS1001A',
            },
            decision: {
                decision: 'APPROVE',
                probability_of_default: 12.5,
                recommended_loan_amount: 30000000,
                recommended_interest_rate: 10.5,
                data_quality_score: 95,
            },
            fraud: { overall_fraud_risk: 'LOW', total_signals_found: 0, signals: [] },
            news: { news_risk_score: 15, top_signals: [] },
            recommendation: {
                decision_reasoning:
                    'Strong financial stability, consistent transactions, no fraud signals.',
                conditions: [],
                interest_rate_breakdown: 'Base 8% + Risk Premium 2.5%',
            },
            shap: {
                base_risk: 15,
                final_pd: 12.5,
                shap_factors: [
                    { name: 'Stable Cash Flow', impact: '-1.5' },
                    { name: 'High Revenue Growth', impact: '-1.0' },
                ],
            },
        },
    },
    {
        keys: ['ZZZCZ1002B', '58923104765'],
        accountNumber: '58923104765',
        results: {
            company: {
                company_name: 'Zentara Polymers Limited',
                cin_number: 'U24100MH2012PTC100002',
                pan_number: 'ZZZCZ1002B',
            },
            decision: {
                decision: 'REJECT',
                probability_of_default: 85.2,
                recommended_loan_amount: 0,
                recommended_interest_rate: 0,
                data_quality_score: 88,
            },
            fraud: {
                overall_fraud_risk: 'HIGH',
                total_signals_found: 3,
                signals: [
                    { description: 'Suspicious transactions', confidence_score: 92 },
                    { description: 'GST mismatch', confidence_score: 85 },
                    { description: 'High liabilities', confidence_score: 78 },
                ],
            },
            news: {
                news_risk_score: 80,
                top_signals: [{ risk: 'HIGH', signal: 'Negative market sentiment' }],
            },
            recommendation: {
                decision_reasoning: 'Suspicious transactions, GST mismatch, high liabilities.',
                conditions: [],
                interest_rate_breakdown: 'N/A',
            },
            shap: {
                base_risk: 15,
                final_pd: 85.2,
                shap_factors: [
                    { name: 'GST Mismatch', impact: '+40.5' },
                    { name: 'Suspicious Transactions', impact: '+29.7' },
                ],
            },
        },
    },
    {
        keys: ['ZZZCV1003C', '67289103452'],
        accountNumber: '67289103452',
        results: {
            company: {
                company_name: 'Velmora Agritech Limited',
                cin_number: 'U01100KA2016PTC100003',
                pan_number: 'ZZZCV1003C',
            },
            decision: {
                decision: 'CONDITIONAL',
                probability_of_default: 25.4,
                recommended_loan_amount: 20000000,
                recommended_interest_rate: 12.5,
                data_quality_score: 90,
            },
            fraud: {
                overall_fraud_risk: 'MEDIUM',
                total_signals_found: 1,
                signals: [{ description: 'Moderate cash flow risk', confidence_score: 65 }],
            },
            news: { news_risk_score: 40, top_signals: [] },
            recommendation: {
                decision_reasoning:
                    'Requires verification, moderate cash flow risk, manual review needed.',
                conditions: [
                    'Submit updated bank statement',
                    'Manual verification of liabilities',
                ],
                interest_rate_breakdown: 'Base 8% + Risk Premium 4.5%',
            },
            shap: {
                base_risk: 15,
                final_pd: 25.4,
                shap_factors: [{ name: 'Moderate Cash Flow Risk', impact: '+10.4' }],
            },
        },
    },
];

/** Normalises user input the same way everywhere: trimmed and upper-cased. */
export const normaliseDemoInput = (value: string): string => value.trim().toUpperCase();

/** Looks up a demo record by PAN or account number. */
export const findDemoAccount = (value: string): DemoAccount | undefined => {
    const input = normaliseDemoInput(value);
    return DEMO_ACCOUNTS.find(account => account.keys.includes(input));
};

/** True when the input unlocks a demo record. */
export const isDemoInput = (value: string): boolean => Boolean(findDemoAccount(value));

/** Every accepted identifier, for placeholders and hint text. */
export const DEMO_HINTS = DEMO_ACCOUNTS.map(a => ({
    company: a.results.company.company_name,
    pan: a.results.company.pan_number,
    accountNumber: a.accountNumber,
    decision: a.results.decision.decision,
}));
