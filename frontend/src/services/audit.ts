/**
 * Audit service for fetching and managing audit results.
 */

import apiClient from './api';
import type { AuditResult, ParsedFields } from '../types';

/**
 * Get audit results for a document.
 */
export async function getAuditResults(documentId: number): Promise<AuditResult> {
  const response = await apiClient.get<AuditResult>(`/audits/${documentId}`);
  return response.data;
}

/**
 * Get parsed fields for a document.
 */
export async function getParsedFields(documentId: number): Promise<ParsedFields> {
  const response = await apiClient.get<ParsedFields>(`/audits/${documentId}/fields`);
  return response.data;
}

/**
 * Get audit summary text.
 */
export async function getAuditSummary(documentId: number): Promise<{ summary: string[] }> {
  const response = await apiClient.get(`/audits/${documentId}/summary`);
  return response.data;
}

/**
 * Re-run audit for a document.
 */
export async function rerunAudit(documentId: number): Promise<{ status: string }> {
  const response = await apiClient.post(`/audits/${documentId}/rerun`);
  return response.data;
}

