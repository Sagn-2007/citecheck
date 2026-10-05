import { useState } from 'react';
import type { ReferenceResult } from '../types';
import { VerdictBadge } from './VerdictBadge';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface ReferenceResultCardProps {
    result: ReferenceResult;
}

export function ReferenceResultCard({ result }: ReferenceResultCardProps) {
    const [expanded, setExpanded] = useState(false);
    const { extracted_reference: ext, verdict, closest_candidate: cand, field_differences: diffs } = result;

    const getExplanation = () => {
        switch (verdict) {
            case 'VERIFIED': return 'The submitted metadata closely matches a known scholarly record.';
            case 'MISMATCH': return 'A candidate was found, but key metadata (like title, authors, or year) contradicts the submitted reference.';
            case 'NOT_FOUND': return 'No sufficiently strong scholarly match was found by the verification pipeline.';
            case 'DOI_INVALID': return 'The provided DOI is invalid or resolves to a different paper.';
            case 'CANNOT_VERIFY': return 'Unable to establish a reliable scholarly match (e.g., website or unsupported type). Unable to verify is not the same as proven fake.';
            default: return '';
        }
    };

    return (
        <div className="reference-card">
            <div className="card-header" onClick={() => setExpanded(!expanded)}>
                <div className="card-main-info">
                    <div className="ref-title">{ext.title || ext.raw}</div>
                    <div className="ref-summary">
                        {ext.authors.length > 0 ? ext.authors.join(', ') : 'Unknown Authors'}
                        {ext.year ? ` (${ext.year})` : ''}
                    </div>
                </div>
                <div className="card-actions">
                    <VerdictBadge verdict={verdict} />
                    {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
            </div>

            {expanded && (
                <div className="card-details">
                    <div className="verdict-explanation">
                        <strong>Verdict Explanation:</strong> {getExplanation()}
                    </div>

                    <div className="detail-columns">
                        <div className="detail-section">
                            <h4>Submitted Metadata</h4>
                            <div className="detail-row"><span className="detail-label">Raw:</span> {ext.raw}</div>
                            <div className="detail-row"><span className="detail-label">Type:</span> {ext.type}</div>
                            {ext.doi && <div className="detail-row"><span className="detail-label">DOI:</span> {ext.doi}</div>}
                            {ext.venue && <div className="detail-row"><span className="detail-label">Venue:</span> {ext.venue}</div>}
                        </div>

                        <div className="detail-section">
                            <h4>Matched Candidate {cand?.source ? `(Source: ${cand.source})` : ''}</h4>
                            {cand ? (
                                <>
                                    <div className="detail-row"><span className="detail-label">Title:</span> {cand.title}</div>
                                    {cand.authors?.length > 0 && <div className="detail-row"><span className="detail-label">Authors:</span> {cand.authors.join(', ')}</div>}
                                    {cand.year && <div className="detail-row"><span className="detail-label">Year:</span> {cand.year}</div>}
                                    {cand.url && <div className="detail-row"><span className="detail-label">URL:</span> <a href={cand.url} target="_blank" rel="noreferrer">{cand.url}</a></div>}
                                    {result.similarity !== undefined && result.similarity !== null && (
                                        <div className="detail-row"><span className="detail-label">Similarity Match:</span> {Math.round(result.similarity)}%</div>
                                    )}
                                </>
                            ) : (
                                <div className="detail-row">No candidate found.</div>
                            )}
                        </div>
                    </div>
                    
                    {diffs && diffs.length > 0 && (
                        <div className="diff-section">
                            <h4>Key Differences</h4>
                            <div className="diff-grid">
                                {diffs.map((diff, idx) => (
                                    <div key={idx} className="diff-card">
                                        <div className="diff-field-name">{diff.field_name.toUpperCase()}</div>
                                        <div className="diff-row diff-submitted">
                                            <span className="diff-indicator">Submitted:</span> {diff.submitted ?? 'None'}
                                        </div>
                                        <div className="diff-row diff-matched">
                                            <span className="diff-indicator">Matched:</span> {diff.matched ?? 'None'}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
