import client from '../api/client';

export interface Extraction {
  id: string;
  document_id: string;
  extraction_method: string;
  raw_text?: string;
  structured_data: Record<string, unknown>;
  confidence_scores: Record<string, unknown>;
  extracted_at: string;
  extraction_metadata?: Record<string, unknown>;
}

export function getExtraction(documentId: string): Promise<Extraction> {
  return client.get<Extraction>(`/documents/${documentId}/extraction`).then((r) => r.data);
}

export function retryExtraction(documentId: string): Promise<Extraction> {
  return client.post<Extraction>(`/documents/${documentId}/extraction/retry`).then((r) => r.data);
}
