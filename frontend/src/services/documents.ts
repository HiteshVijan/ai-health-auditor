/**
 * Document service for upload and management.
 */

import apiClient from './api';
import type { Document, PaginatedResponse } from '../types';

/**
 * Upload a document for processing.
 */
export async function uploadDocument(file: File): Promise<{ documentId: number; status: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/uploads/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return response.data;
}

/**
 * Get document by ID.
 */
export async function getDocument(documentId: number): Promise<Document> {
  const response = await apiClient.get<Document>(`/documents/${documentId}`);
  return response.data;
}

/**
 * Get all documents for current user.
 */
export async function getDocuments(
  page: number = 1,
  pageSize: number = 10
): Promise<PaginatedResponse<Document>> {
  const response = await apiClient.get<PaginatedResponse<Document>>('/documents/', {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

/**
 * Delete a document.
 */
export async function deleteDocument(documentId: number): Promise<void> {
  await apiClient.delete(`/documents/${documentId}`);
}

/**
 * Get document processing status.
 */
export async function getDocumentStatus(documentId: number): Promise<{ status: string }> {
  const response = await apiClient.get(`/documents/${documentId}/status`);
  return response.data;
}

