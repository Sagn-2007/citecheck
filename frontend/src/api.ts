import type { VerifyResponse } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class APIError extends Error {
    public status: number;
    constructor(status: number, message: string) {
        super(message);
        this.status = status;
    }
}

async function handleResponse(response: Response): Promise<any> {
    if (!response.ok) {
        const status = response.status;
        let baseMsg = "An unexpected error occurred.";
        
        if (status === 400) {
            baseMsg = "Could not extract text from this document.";
        } else if (status === 413) {
            baseMsg = "The uploaded file is too large.";
        } else if (status === 422) {
            baseMsg = "Invalid submission. Please check your file or text.";
        } else if (status === 500) {
            baseMsg = "Citation extraction failed. Please try again.";
        } else if (status === 503 || status === 502) {
            baseMsg = "Service temporarily unavailable. Please try again later.";
        }
        
        throw new APIError(status, baseMsg);
    }
    return response.json();
}

export async function verifyText(text: string): Promise<VerifyResponse> {
    try {
        const response = await fetch(`${API_BASE_URL}/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text })
        });
        return await handleResponse(response);
    } catch (e: any) {
        if (e instanceof APIError) throw e;
        throw new APIError(0, "Unable to connect to the server. Please check your network connection.");
    }
}

export async function verifyFile(file: File): Promise<VerifyResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // Do not set Content-Type, fetch will automatically set it to multipart/form-data with the correct boundary
        const response = await fetch(`${API_BASE_URL}/verify`, {
            method: 'POST',
            body: formData
        });
        return await handleResponse(response);
    } catch (e: any) {
        if (e instanceof APIError) throw e;
        throw new APIError(0, "Unable to connect to the server. Please check your network connection.");
    }
}
