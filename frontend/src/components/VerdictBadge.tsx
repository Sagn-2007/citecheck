import type { Verdict } from '../types';
import { Verdict as VerdictEnum } from '../types';
import { CheckCircle, AlertTriangle, HelpCircle, XCircle, FileQuestion } from 'lucide-react';

interface VerdictBadgeProps {
    verdict: Verdict;
}

export function VerdictBadge({ verdict }: VerdictBadgeProps) {
    let icon = <HelpCircle size={16} />;
    let label = verdict.toString();
    let className = 'verdict-badge';

    switch (verdict) {
        case VerdictEnum.VERIFIED:
            icon = <CheckCircle size={16} />;
            label = "Verified";
            className += ' verdict-verified';
            break;
        case VerdictEnum.MISMATCH:
            icon = <AlertTriangle size={16} />;
            label = "Mismatch";
            className += ' verdict-mismatch';
            break;
        case VerdictEnum.NOT_FOUND:
            icon = <FileQuestion size={16} />;
            label = "Not Found";
            className += ' verdict-not-found';
            break;
        case VerdictEnum.DOI_INVALID:
            icon = <XCircle size={16} />;
            label = "DOI Invalid";
            className += ' verdict-doi-invalid';
            break;
        case VerdictEnum.CANNOT_VERIFY:
            icon = <HelpCircle size={16} />;
            label = "Cannot Verify";
            className += ' verdict-cannot-verify';
            break;
    }

    return (
        <span className={className}>
            {icon}
            {label}
        </span>
    );
}
