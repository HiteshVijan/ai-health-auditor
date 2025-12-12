/**
 * B2B Authentication Service
 * 
 * Separate authentication for hospital administrators.
 * Uses different token storage from B2C auth.
 */

import apiClient from './api';

const B2B_TOKEN_KEY = 'b2b_access_token';
const B2B_ADMIN_KEY = 'b2b_admin';

// ============================================
// Types
// ============================================

export interface B2BAdmin {
  id: number;
  email: string;
  full_name: string;
  designation: string;
  hospital_id: number;
  hospital_name: string;
  hospital_city?: string;
  is_primary: boolean;
  permissions?: string[];
}

export interface B2BRegisterRequest {
  email: string;
  password: string;
  full_name: string;
  designation: string;
  phone?: string;
  hospital_name: string;
  hospital_city: string;
  hospital_state: string;
  hospital_type?: string;
}

export interface B2BLoginRequest {
  email: string;
  password: string;
}

export interface B2BTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  admin: B2BAdmin;
}

// ============================================
// API Functions
// ============================================

/**
 * Register a new hospital admin
 */
export async function b2bRegister(request: B2BRegisterRequest): Promise<B2BTokenResponse> {
  const response = await apiClient.post('/b2b/auth/register', request);
  const data = response.data as B2BTokenResponse;
  
  // Store token and admin info
  localStorage.setItem(B2B_TOKEN_KEY, data.access_token);
  localStorage.setItem(B2B_ADMIN_KEY, JSON.stringify(data.admin));
  
  return data;
}

/**
 * Login as hospital admin
 */
export async function b2bLogin(request: B2BLoginRequest): Promise<B2BTokenResponse> {
  const response = await apiClient.post('/b2b/auth/login', request);
  const data = response.data as B2BTokenResponse;
  
  // Store token and admin info
  localStorage.setItem(B2B_TOKEN_KEY, data.access_token);
  localStorage.setItem(B2B_ADMIN_KEY, JSON.stringify(data.admin));
  
  return data;
}

/**
 * Logout B2B admin
 */
export function b2bLogout(): void {
  localStorage.removeItem(B2B_TOKEN_KEY);
  localStorage.removeItem(B2B_ADMIN_KEY);
  window.location.href = '/b2b/login';
}

/**
 * Get current B2B admin from storage
 */
export function getB2BAdmin(): B2BAdmin | null {
  const stored = localStorage.getItem(B2B_ADMIN_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      return null;
    }
  }
  return null;
}

/**
 * Get B2B token
 */
export function getB2BToken(): string | null {
  return localStorage.getItem(B2B_TOKEN_KEY);
}

/**
 * Check if B2B admin is authenticated
 */
export function isB2BAuthenticated(): boolean {
  return !!getB2BToken();
}

/**
 * Refresh B2B admin info from server
 */
export async function refreshB2BAdmin(): Promise<B2BAdmin> {
  const response = await apiClient.get('/b2b/auth/me', {
    headers: {
      Authorization: `Bearer ${getB2BToken()}`,
    },
  });
  const admin = response.data as B2BAdmin;
  localStorage.setItem(B2B_ADMIN_KEY, JSON.stringify(admin));
  return admin;
}

/**
 * Create an axios instance with B2B auth header
 */
export function getB2BApiClient() {
  const token = getB2BToken();
  return {
    get: (url: string, config = {}) => 
      apiClient.get(url, { 
        ...config, 
        headers: { ...((config as { headers?: Record<string, string> }).headers || {}), Authorization: `Bearer ${token}` } 
      }),
    post: (url: string, data?: unknown, config = {}) => 
      apiClient.post(url, data, { 
        ...config, 
        headers: { ...((config as { headers?: Record<string, string> }).headers || {}), Authorization: `Bearer ${token}` } 
      }),
  };
}

