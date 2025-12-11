/**
 * Authentication service for login, register, and user management.
 */

import apiClient from './api';
import type { LoginRequest, RegisterRequest, AuthResponse, User } from '../types';

/**
 * Login with email and password.
 */
export async function login(credentials: LoginRequest): Promise<AuthResponse> {
  const formData = new URLSearchParams();
  formData.append('username', credentials.email);
  formData.append('password', credentials.password);

  const response = await apiClient.post<AuthResponse>('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  // Store token - use access_token to match api.ts interceptor
  const token = response.data.access_token || response.data.accessToken;
  localStorage.setItem('access_token', token);

  return response.data;
}

/**
 * Register a new user.
 */
export async function register(data: RegisterRequest): Promise<User> {
  const response = await apiClient.post<User>('/auth/register', {
    email: data.email,
    password: data.password,
    full_name: data.fullName,
  });
  return response.data;
}

/**
 * Logout current user.
 */
export function logout(): void {
  localStorage.removeItem('access_token');
  window.location.href = '/login';
}

/**
 * Get current user profile.
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/users/me');
  return response.data;
}

/**
 * Check if user is authenticated.
 */
export function isAuthenticated(): boolean {
  return !!localStorage.getItem('access_token');
}

