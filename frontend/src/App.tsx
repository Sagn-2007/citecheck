import { useState } from 'react';
import './App.css';
import type { VerifyResponse } from './types';
import { verifyText, verifyFile } from './api';
import { InputPanel } from './components/InputPanel';
import { LoadingState } from './components/LoadingState';
import { ResultsSummary } from './components/ResultsSummary';
import { ReferenceResultCard } from './components/ReferenceResultCard';
import { AlertCircle } from 'lucide-react';

function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<VerifyResponse | null>(null);

  const handleVerifyText = async (text: string) => {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const res = await verifyText(text);
      setResults(res);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyFile = async (file: File) => {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const res = await verifyFile(file);
      setResults(res);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>CiteCheck</h1>
        <h2>Citation Verifier for AI-Written Reports</h2>
      </header>

      <main className="main-content">
        <InputPanel 
          onVerifyText={handleVerifyText} 
          onVerifyFile={handleVerifyFile} 
          disabled={loading} 
          onError={setError}
        />

        {error && (
          <div className="error-message">
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        {loading && <LoadingState />}

        {!loading && !error && !results && (
          <div className="empty-state">
            <h3>Ready to verify citations</h3>
            <p>Paste a bibliography or upload a report to verify its citations against scholarly databases.</p>
          </div>
        )}

        {!loading && results && (
          <>
            {results.total_references === 0 ? (
              <div className="empty-state">
                <h3>No references found</h3>
                <p>We couldn't detect any valid citations in the provided text/document.</p>
              </div>
            ) : (
              <>
                <ResultsSummary response={results} />
                <div className="reference-list">
                  {results.results.map((res, i) => (
                    <ReferenceResultCard key={i} result={res} />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
