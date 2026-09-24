/**
 * API service for communicating with the ConsistencyMesh backend.
 * All API calls go through this service — components never call fetch directly.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/** Generate a unique session ID for cross-session isolation. */
function getSessionId(): string {
  let sessionId = sessionStorage.getItem('cm_session_id');
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem('cm_session_id', sessionId);
  }
  return sessionId;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  page_count: number;
  clause_count: number;
}

export interface AnalysisRequest {
  document_ids: string[];
  session_id: string;
}

export interface EvidenceSpan {
  document_id: string;
  clause_id: string;
  page: number;
  text_span: string;
}

export interface Finding {
  finding_id: string;
  relationship_type: 'CONSISTENT' | 'CONFLICT' | 'OVERRIDE' | 'AMBIGUOUS' | 'UNADDRESSED';
  confidence: 'STATED' | 'INTERPRETED' | 'NOT_ESTABLISHED';
  explanation: string;
  evidence: EvidenceSpan[];
  uncertainty: string | null;
  validated: boolean;
}

export interface ConsistencyEdge {
  source_clause_id: string;
  target_clause_id: string;
  finding_id: string;
  relationship_type: string;
}

export interface ConsistencyGraph {
  nodes: string[];
  document_nodes: string[];
  edges: ConsistencyEdge[];
}

export interface Document {
  document_id: string;
  filename: string;
  page_count: number;
  uploaded_at: string;
}

export interface AnalysisResult {
  job_id: string;
  state: string;
  documents: Document[];
  findings: Finding[];
  graph: ConsistencyGraph;
  metrics: Record<string, number>;
  error_message: string | null;
}

export interface AnalysisStatusResponse {
  job_id: string;
  state: string;
  progress_detail: string;
  result: AnalysisResult | null;
}

export interface QAResponse {
  answer: string;
  confidence: 'STATED' | 'INTERPRETED' | 'NOT_ESTABLISHED';
  evidence: EvidenceSpan[];
  uncertainty: string | null;
}

export interface MetricsResponse {
  job_id: string;
  metrics: Record<string, number>;
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ message: 'Request failed' }));
    throw new ApiError(body.message || 'Request failed', response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  /** Upload a document file. */
  async uploadDocument(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', getSessionId());

    const response = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<UploadResponse>(response);
  },

  /** List all documents for the current session. */
  async listDocuments(): Promise<Document[]> {
    const response = await fetch(
      `${API_BASE}/documents/?session_id=${getSessionId()}`
    );
    return handleResponse<Document[]>(response);
  },

  /** Start a new analysis job. */
  async createAnalysis(documentIds: string[]): Promise<{ job_id: string; state: string }> {
    const response = await fetch(`${API_BASE}/analysis/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_ids: documentIds,
        session_id: getSessionId(),
      }),
    });
    return handleResponse<{ job_id: string; state: string }>(response);
  },

  /** Poll the status of an analysis job. */
  async getAnalysisStatus(jobId: string): Promise<AnalysisStatusResponse> {
    const response = await fetch(
      `${API_BASE}/analysis/${jobId}?session_id=${getSessionId()}`
    );
    return handleResponse<AnalysisStatusResponse>(response);
  },

  /** Get job metrics. */
  async getMetrics(jobId: string): Promise<MetricsResponse> {
    const response = await fetch(`${API_BASE}/analysis/${jobId}/metrics`);
    return handleResponse<MetricsResponse>(response);
  },

  /** Ask a follow-up question. */
  async askQuestion(jobId: string, question: string): Promise<QAResponse> {
    const response = await fetch(`${API_BASE}/qa/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: jobId,
        question,
        session_id: getSessionId(),
      }),
    });
    return handleResponse<QAResponse>(response);
  },
};
