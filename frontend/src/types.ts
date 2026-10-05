export const Verdict = {
    VERIFIED: "VERIFIED",
    MISMATCH: "MISMATCH",
    NOT_FOUND: "NOT_FOUND",
    DOI_INVALID: "DOI_INVALID",
    CANNOT_VERIFY: "CANNOT_VERIFY"
} as const;

export type Verdict = typeof Verdict[keyof typeof Verdict];

export interface ExtractedReference {
    raw: string;
    authors: string[];
    title: string;
    year?: number | null;
    venue?: string | null;
    doi?: string | null;
    type: string;
}

export interface ScholarlyCandidate {
    title: string;
    authors: string[];
    year?: number | null;
    venue?: string | null;
    doi?: string | null;
    source: string;
    url?: string | null;
}

export interface FieldDifference {
    field_name: string;
    submitted?: string | number | null;
    matched?: string | number | null;
}

export interface ReferenceResult {
    extracted_reference: ExtractedReference;
    verdict: Verdict;
    closest_candidate?: ScholarlyCandidate | null;
    similarity?: number | null;
    field_differences?: FieldDifference[] | null;
}

export interface VerifyResponse {
    results: ReferenceResult[];
    total_references: number;
    verdict_counts: Record<Verdict, number>;
    reliability_score?: number | null;
}
