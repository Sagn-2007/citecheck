import { useState, useRef } from 'react';
import { UploadCloud, Type } from 'lucide-react';

interface InputPanelProps {
    onVerifyText: (text: string) => void;
    onVerifyFile: (file: File) => void;
    disabled: boolean;
    onError: (msg: string) => void;
}

export function InputPanel({ onVerifyText, onVerifyFile, disabled, onError }: InputPanelProps) {
    const [mode, setMode] = useState<'text' | 'file'>('text');
    const [text, setText] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleVerify = () => {
        if (mode === 'text') {
            if (text.trim()) {
                onVerifyText(text);
            }
        } else {
            if (file) {
                onVerifyFile(file);
            }
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const selected = e.target.files[0];
            const name = selected.name.toLowerCase();
            if (name.endsWith('.pdf') || name.endsWith('.docx')) {
                setFile(selected);
                onError(''); // clear any existing error
            } else {
                setFile(null);
                onError('Invalid file type. Please upload a PDF or DOCX file.');
            }
        }
    };

    return (
        <div className="input-panel">
            <div className="input-modes">
                <button 
                    className={`mode-btn ${mode === 'text' ? 'active' : ''}`}
                    onClick={() => setMode('text')}
                    disabled={disabled}
                >
                    <Type size={16} style={{ display: 'inline', marginRight: 6, verticalAlign: 'text-bottom' }} />
                    Paste Bibliography
                </button>
                <button 
                    className={`mode-btn ${mode === 'file' ? 'active' : ''}`}
                    onClick={() => setMode('file')}
                    disabled={disabled}
                >
                    <UploadCloud size={16} style={{ display: 'inline', marginRight: 6, verticalAlign: 'text-bottom' }} />
                    Upload PDF / DOCX
                </button>
            </div>

            <div className="input-area">
                {mode === 'text' ? (
                    <textarea 
                        className="text-input" 
                        placeholder="Paste your bibliography here..."
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        disabled={disabled}
                    />
                ) : (
                    <div 
                        className="file-upload-zone"
                        onClick={() => !disabled && fileInputRef.current?.click()}
                    >
                        <input 
                            type="file" 
                            ref={fileInputRef} 
                            style={{ display: 'none' }}
                            accept=".pdf,.docx"
                            onChange={handleFileChange}
                            disabled={disabled}
                        />
                        <UploadCloud size={48} color="var(--accent)" />
                        {file ? (
                            <p><strong>Selected file:</strong> {file.name}</p>
                        ) : (
                            <p>Click to upload a PDF or DOCX file</p>
                        )}
                    </div>
                )}
            </div>

            <button 
                className="verify-btn" 
                onClick={handleVerify}
                disabled={disabled || (mode === 'text' && !text.trim()) || (mode === 'file' && !file)}
            >
                {disabled ? 'Verifying citations... Extracting references and checking scholarly sources.' : 'Verify Citations'}
            </button>
        </div>
    );
}
