/**
 * B2B Dashboard Service
 * 
 * API calls for hospital dashboard using B2B authentication.
 */

import { getB2BToken } from './b2bAuth';
import apiClient from './api';

// ============================================
// Types
// ============================================

export interface DashboardStats {
  hospital_id: number;
  hospital_name: string;
  city: string;
  state: string;
  hospital_type: string;
  overall_score: number;
  pricing_score: number;
  transparency_score: number;
  city_rank: number | null;
  city_total: number | null;
  state_rank: number | null;
  national_rank: number | null;
  total_procedures_priced: number;
  total_bills_analyzed: number;
  avg_overcharge_percent: number;
  admin_name: string;
  admin_designation: string;
}

export interface ProcedurePricing {
  procedure_id: number;
  procedure_name: string;
  category: string;
  your_price: number | null;
  market_average: number | null;
  cghs_rate: number | null;
  pmjay_rate: number | null;
  vs_market_percent: number | null;
  status: 'competitive' | 'overpriced' | 'underpriced';
}

export interface PricingOverview {
  total_procedures: number;
  competitive_count: number;
  overpriced_count: number;
  underpriced_count: number;
  procedures: ProcedurePricing[];
  recommendations: string[];
}

export interface CompetitorSegment {
  segment: string;
  avg_price: number;
  sample_count: number;
  your_avg: number;
  difference_percent: number;
  your_position: string;
}

export interface CompetitorAnalysis {
  hospital_name: string;
  segments: CompetitorSegment[];
  insights: string[];
}

export interface TrendData {
  date: string;
  observations: number;
  avg_amount: number;
}

export interface CategoryData {
  category: string;
  observation_count: number;
  avg_price: number;
  vs_benchmark: number;
  status: string;
}

// ============================================
// Helper
// ============================================

function getAuthHeaders() {
  const token = getB2BToken();
  return { Authorization: `Bearer ${token}` };
}

// ============================================
// API Functions
// ============================================

export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await apiClient.get('/b2b/dashboard/stats', {
    headers: getAuthHeaders(),
  });
  return response.data;
}

export async function getPricingOverview(category?: string): Promise<PricingOverview> {
  const params = category ? { category } : {};
  const response = await apiClient.get('/b2b/dashboard/pricing', {
    headers: getAuthHeaders(),
    params,
  });
  return response.data;
}

export async function getCompetitorAnalysis(): Promise<CompetitorAnalysis> {
  const response = await apiClient.get('/b2b/dashboard/competitors', {
    headers: getAuthHeaders(),
  });
  return response.data;
}

export async function getPricingTrends(period: '7d' | '30d' | '90d' = '30d'): Promise<{
  hospital_name: string;
  period: string;
  data: TrendData[];
  summary: { total_observations: number; period_days: number };
}> {
  const response = await apiClient.get('/b2b/dashboard/trends', {
    headers: getAuthHeaders(),
    params: { period },
  });
  return response.data;
}

export async function getCategoryBreakdown(): Promise<{
  hospital_name: string;
  categories: CategoryData[];
}> {
  const response = await apiClient.get('/b2b/dashboard/categories', {
    headers: getAuthHeaders(),
  });
  return response.data;
}

