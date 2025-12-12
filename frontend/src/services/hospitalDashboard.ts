/**
 * Hospital Dashboard API Service
 * 
 * B2B feature for hospital administrators to view:
 * - Pricing comparisons vs market
 * - Hospital scores and rankings
 * - Competitor analysis
 * - Trends over time
 */

import apiClient from './api';

// ============================================
// Types
// ============================================

export interface HospitalDashboardStats {
  hospital_id: number;
  hospital_name: string;
  city: string;
  hospital_type: string;
  overall_score: number;
  pricing_score: number;
  transparency_score: number;
  city_rank: number | null;
  city_total: number | null;
  state_rank: number | null;
  state_total: number | null;
  national_rank: number | null;
  national_total: number | null;
  total_procedures_priced: number;
  total_bills_analyzed: number;
  avg_overcharge_percent: number;
  score_change_30d: number | null;
  bills_last_30d: number;
}

export interface ProcedurePricing {
  procedure_id: number;
  procedure_name: string;
  category: string;
  your_price: number | null;
  market_average: number | null;
  market_low: number | null;
  market_high: number | null;
  cghs_rate: number | null;
  pmjay_rate: number | null;
  vs_market_percent: number | null;
  vs_cghs_percent: number | null;
  sample_count: number;
  status: 'competitive' | 'overpriced' | 'underpriced';
}

export interface PricingComparison {
  procedures: ProcedurePricing[];
  summary: {
    total_procedures: number;
    overpriced: number;
    competitive: number;
    underpriced: number;
  };
  recommendations: string[];
}

export interface CompetitorSummary {
  hospital_type: string;
  city_tier: string;
  avg_price: number;
  sample_count: number;
}

export interface CompetitorAnalysis {
  your_hospital: string;
  competitors: CompetitorSummary[];
  your_position: 'above_average' | 'competitive' | 'below_average' | 'unknown';
  insights: string[];
}

export interface TrendsData {
  hospital_name: string;
  period: string;
  score_trend: Array<{
    date: string;
    overall_score: number;
    pricing_score: number;
  }>;
  daily_observations: Array<{
    date: string;
    observations: number;
    avg_amount: number;
  }>;
  summary: {
    total_observations: number;
    avg_daily_observations: number;
  };
}

export interface CategoryBreakdown {
  hospital_name: string;
  categories: Array<{
    category: string;
    observation_count: number;
    avg_price: number;
    vs_benchmark_percent: number;
    status: 'competitive' | 'overpriced' | 'underpriced';
  }>;
  total_categories: number;
}

export interface AvailableHospital {
  id: number;
  name: string;
  city: string;
  state: string;
  hospital_type: string;
  is_verified: boolean;
  total_bills_analyzed: number;
}

export interface HospitalClaimRequest {
  hospital_id: number;
  verification_type: string;
  contact_email: string;
  contact_phone?: string;
  designation: string;
  notes?: string;
}

export interface HospitalClaimResponse {
  claim_id: number;
  status: string;
  message: string;
}

// ============================================
// API Functions
// ============================================

/**
 * Get hospital dashboard statistics
 */
export async function getDashboardStats(hospitalId?: number): Promise<HospitalDashboardStats> {
  const params = hospitalId ? { hospital_id: hospitalId } : {};
  const response = await apiClient.get('/hospital/stats', { params });
  return response.data;
}

/**
 * Get pricing comparison for hospital
 */
export async function getPricingComparison(
  hospitalId?: number,
  category?: string,
  limit: number = 50
): Promise<PricingComparison> {
  const params: Record<string, unknown> = { limit };
  if (hospitalId) params.hospital_id = hospitalId;
  if (category) params.category = category;
  
  const response = await apiClient.get('/hospital/pricing', { params });
  return response.data;
}

/**
 * Get competitor analysis
 */
export async function getCompetitorAnalysis(
  hospitalId?: number,
  procedureId?: number
): Promise<CompetitorAnalysis> {
  const params: Record<string, unknown> = {};
  if (hospitalId) params.hospital_id = hospitalId;
  if (procedureId) params.procedure_id = procedureId;
  
  const response = await apiClient.get('/hospital/competitors', { params });
  return response.data;
}

/**
 * Get pricing trends over time
 */
export async function getPricingTrends(
  hospitalId?: number,
  period: '7d' | '30d' | '90d' | '1y' = '30d'
): Promise<TrendsData> {
  const params: Record<string, unknown> = { period };
  if (hospitalId) params.hospital_id = hospitalId;
  
  const response = await apiClient.get('/hospital/trends', { params });
  return response.data;
}

/**
 * Get category breakdown
 */
export async function getCategoryBreakdown(hospitalId?: number): Promise<CategoryBreakdown> {
  const params = hospitalId ? { hospital_id: hospitalId } : {};
  const response = await apiClient.get('/hospital/categories', { params });
  return response.data;
}

/**
 * List available hospitals to claim
 */
export async function getAvailableHospitals(
  city?: string,
  search?: string,
  limit: number = 50
): Promise<{ hospitals: AvailableHospital[]; total: number }> {
  const params: Record<string, unknown> = { limit };
  if (city) params.city = city;
  if (search) params.search = search;
  
  const response = await apiClient.get('/hospital/available-hospitals', { params });
  return response.data;
}

/**
 * Claim a hospital
 */
export async function claimHospital(request: HospitalClaimRequest): Promise<HospitalClaimResponse> {
  const response = await apiClient.post('/hospital/claim', request);
  return response.data;
}

