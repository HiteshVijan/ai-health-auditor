/**
 * Pricing Intelligence API Service.
 * 
 * Provides access to the pricing lookup, search, and hospital comparison features.
 */

import apiClient from './api';

// Types
export interface BenchmarkPrice {
  source: string;
  rate: number;
  description?: string;
  effective_date?: string;
}

export interface PriceRange {
  low: number;
  median: number;
  high: number;
  p25?: number;
  p75?: number;
  currency: string;
}

export interface MarketPrice {
  hospital_type: string;
  city_tier: string;
  price_range: PriceRange;
  sample_size: number;
  confidence: number;
  last_updated?: string;
}

export interface PriceLookupResponse {
  procedure_name: string;
  matched_procedure: string;
  match_confidence: number;
  category: string;
  benchmarks: BenchmarkPrice[];
  market_prices: MarketPrice[];
  fair_price_range: PriceRange;
  data_points: number;
  last_updated: string;
}

export interface ProcedureSearchResult {
  id: number;
  name: string;
  category: string;
  subcategory?: string;
  cghs_rate?: number;
  pmjay_rate?: number;
  market_median?: number;
  price_point_count: number;
  match_score?: number;
}

export interface ProcedureSearchResponse {
  query: string;
  results: ProcedureSearchResult[];
  total_count: number;
}

export interface HospitalScore {
  pricing_score: number;
  transparency_score: number;
  overall_score: number;
  city_rank?: number;
  city_total?: number;
  score_trend?: string;
}

export interface Hospital {
  id: number;
  name: string;
  normalized_name: string;
  city: string;
  state: string;
  hospital_type: string;
  city_tier: string;
  is_cghs_empaneled: boolean;
  is_nabh_accredited: boolean;
  is_pmjay_empaneled: boolean;
  scores: HospitalScore;
  total_bills_analyzed: number;
  total_procedures_priced: number;
  avg_overcharge_percent: number;
  is_verified: boolean;
  created_at: string;
}

export interface HospitalSearchResponse {
  hospitals: Hospital[];
  total_count: number;
  filters_applied: Record<string, unknown>;
}

export interface DatabaseStats {
  total_price_points: number;
  total_hospitals: number;
  total_procedures: number;
  cghs_procedures: number;
  pmjay_packages: number;
  crowdsourced_points: number;
  cities_covered: number;
  states_covered: number;
  latest_contribution?: string;
  contributions_last_7_days: number;
  contributions_last_30_days: number;
  verified_percentage: number;
}

export interface CategoryInfo {
  name: string;
  procedure_count: number;
}

// API Functions

/**
 * Look up price for a procedure.
 */
export async function lookupPrice(
  procedure: string,
  city?: string,
  hospitalName?: string,
  hospitalType?: string
): Promise<PriceLookupResponse> {
  const params = new URLSearchParams({ procedure });
  if (city) params.append('city', city);
  if (hospitalName) params.append('hospital_name', hospitalName);
  if (hospitalType) params.append('hospital_type', hospitalType);
  
  const response = await apiClient.get<PriceLookupResponse>(`/pricing/lookup?${params}`);
  return response.data;
}

/**
 * Search for procedures.
 */
export async function searchProcedures(
  query: string,
  category?: string,
  limit: number = 20
): Promise<ProcedureSearchResponse> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  if (category) params.append('category', category);
  
  const response = await apiClient.get<ProcedureSearchResponse>(`/pricing/search?${params}`);
  return response.data;
}

/**
 * Get all procedure categories.
 */
export async function getCategories(): Promise<{ categories: CategoryInfo[] }> {
  const response = await apiClient.get<{ categories: CategoryInfo[] }>('/pricing/categories');
  return response.data;
}

/**
 * Search hospitals.
 */
export async function searchHospitals(params: {
  query?: string;
  city?: string;
  state?: string;
  hospitalType?: string;
  minScore?: number;
  isCghsEmpaneled?: boolean;
  sortBy?: string;
  limit?: number;
  offset?: number;
}): Promise<HospitalSearchResponse> {
  const searchParams = new URLSearchParams();
  if (params.query) searchParams.append('query', params.query);
  if (params.city) searchParams.append('city', params.city);
  if (params.state) searchParams.append('state', params.state);
  if (params.hospitalType) searchParams.append('hospital_type', params.hospitalType);
  if (params.minScore !== undefined) searchParams.append('min_score', String(params.minScore));
  if (params.isCghsEmpaneled !== undefined) searchParams.append('is_cghs_empaneled', String(params.isCghsEmpaneled));
  if (params.sortBy) searchParams.append('sort_by', params.sortBy);
  if (params.limit) searchParams.append('limit', String(params.limit));
  if (params.offset) searchParams.append('offset', String(params.offset));
  
  const response = await apiClient.get<HospitalSearchResponse>(`/pricing/hospitals/search?${searchParams}`);
  return response.data;
}

/**
 * Get database statistics.
 */
export async function getDatabaseStats(): Promise<DatabaseStats> {
  const response = await apiClient.get<DatabaseStats>('/pricing/stats');
  return response.data;
}

/**
 * Compare hospitals.
 */
export async function compareHospitals(
  hospitalIds: number[],
  procedure?: string
): Promise<{ hospitals: unknown[]; recommendation: string | null }> {
  const params = new URLSearchParams();
  hospitalIds.forEach(id => params.append('hospital_ids', String(id)));
  if (procedure) params.append('procedure', procedure);
  
  const response = await apiClient.get(`/pricing/hospitals/compare?${params}`);
  return response.data;
}

