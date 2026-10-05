import { Loader2 } from 'lucide-react';

export function LoadingState() {
    return (
        <div className="loading-state">
            <Loader2 className="spinner" size={48} />
            <p>Verifying citations...</p>
            <p className="loading-subtext">Extracting references and checking scholarly sources.</p>
        </div>
    );
}
