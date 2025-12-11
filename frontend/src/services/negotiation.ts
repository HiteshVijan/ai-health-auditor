/**
 * Negotiation service for letter generation and delivery.
 */

import apiClient from './api';
import type { NegotiationRequest, NegotiationResult } from '../types';

/**
 * Generate and send negotiation letter.
 */
export async function sendNegotiation(request: NegotiationRequest): Promise<NegotiationResult> {
  const response = await apiClient.post<NegotiationResult>('/negotiations/', {
    document_id: request.documentId,
    channel: request.channel,
    tone: request.tone,
    recipient_email: request.recipientEmail,
    recipient_phone: request.recipientPhone,
  });
  return response.data;
}

/**
 * Get letter preview without sending.
 */
export async function previewLetter(
  documentId: number,
  tone: string
): Promise<{ letter: string }> {
  const response = await apiClient.get(`/negotiations/preview/${documentId}`, {
    params: { tone },
  });
  return response.data;
}

/**
 * Get negotiation history for a document.
 */
export async function getNegotiationHistory(
  documentId: number
): Promise<NegotiationResult[]> {
  const response = await apiClient.get<NegotiationResult[]>(
    `/negotiations/history/${documentId}`
  );
  return response.data;
}

/**
 * Retry a failed negotiation.
 */
export async function retryNegotiation(negotiationId: number): Promise<NegotiationResult> {
  const response = await apiClient.post<NegotiationResult>(
    `/negotiations/${negotiationId}/retry`
  );
  return response.data;
}

