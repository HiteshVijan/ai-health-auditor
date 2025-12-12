/**
 * Type definitions for the Health Bill Auditor frontend.
 */

// User types
export interface User {
  id: number;
  email: string;
  fullName: string;
  isActive: boolean;
  createdAt: string;
}

// Authentication types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  fullName: string;
}

export interface AuthResponse {
  accessToken: string;
  access_token?: string;  // Backend may return snake_case
  tokenType: string;
  token_type?: string;
}

// Document types
export interface Document {
  id: number;
  userId: number;
  filename: string;
  fileKey: string;
  contentType: string;
  fileSize: number;
  status: DocumentStatus;
  createdAt: string;
  updatedAt: string;
}

export type DocumentStatus = 'uploaded' | 'processing' | 'completed' | 'failed';

// Audit types
export interface AuditResult {
  documentId: number;
  score: number;
  totalIssues: number;
  criticalCount: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  potentialSavings: number;
  issues: AuditIssue[];
}

export interface AuditIssue {
  id: number;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  field?: string;
  expected?: string;
  actual?: string;
  amountImpact?: number;
}

// Parsed field types
export interface ParsedField {
  value: string | null;
  confidence: number;
  source: string;
  needsReview: boolean;
}

export interface ParsedFields {
  totalAmount: ParsedField;
  invoiceNumber: ParsedField;
  patientName: ParsedField;
  billDate: ParsedField;
}

// Negotiation types
export interface NegotiationRequest {
  documentId: number;
  channel: 'email' | 'whatsapp' | 'both';
  tone: 'formal' | 'friendly' | 'assertive';
  recipientEmail?: string;
  recipientPhone?: string;
}

export interface NegotiationResult {
  documentId: number;
  status: 'sent' | 'partially_sent' | 'failed';
  letterGenerated: boolean;
  channels: ChannelResult[];
  retryCount: number;
  timestamp: string;
  error?: string;
}

export interface ChannelResult {
  channel: string;
  status: string;
  messageId?: string;
  error?: string;
  timestamp: string;
}

// API response wrapper
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

