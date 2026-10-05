import type { VerifyResponse } from '../types';
import { Verdict } from '../types';

interface ResultsSummaryProps {
    response: VerifyResponse;
}

export function ResultsSummary({ response }: ResultsSummaryProps) {
    const hasScore = response.reliability_score !== null && response.reliability_score !== undefined;
    
    return (
        <div className="results-summary">
            <div className="score-display">
                {hasScore ? (
                    <>
                        <span className="score-value">{Math.round(response.reliability_score! * 100)}%</span>
                        <span className="score-label">Reliability</span>
                    </>
                ) : (
                    <span className="score-label">No checkable references</span>
                )}
            </div>
            
            <div className="stats-grid">
                <div className="stat-item">
                    <span className="stat-val">{response.total_references}</span>
                    <span className="stat-lbl">Total Refs</span>
                </div>
                <div className="stat-item">
                    <span className="stat-val">{response.verdict_counts[Verdict.VERIFIED] || 0}</span>
                    <span className="stat-lbl">Verified</span>
                </div>
                <div className="stat-item">
                    <span className="stat-val">{response.verdict_counts[Verdict.MISMATCH] || 0}</span>
                    <span className="stat-lbl">Mismatch</span>
                </div>
                <div className="stat-item">
                    <span className="stat-val">{response.verdict_counts[Verdict.NOT_FOUND] || 0}</span>
                    <span className="stat-lbl">Not Found</span>
                </div>
                <div className="stat-item">
                    <span className="stat-val">{response.verdict_counts[Verdict.DOI_INVALID] || 0}</span>
                    <span className="stat-lbl">Invalid DOI</span>
                </div>
                <div className="stat-item">
                    <span className="stat-val">{response.verdict_counts[Verdict.CANNOT_VERIFY] || 0}</span>
                    <span className="stat-lbl">Can't Verify</span>
                </div>
            </div>
        </div>
    );
}
