/**
 * API Client with Sentry Error Tracking.
 *
 * Axios-based HTTP client with automatic error reporting to Sentry.
 */

import axios, { AxiosError, AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { trackApiError, addBreadcrumb } from '../lib/sentry';

/**
 * API Error response structure.
 */
interface ApiErrorResponse {
  detail?: string;
  message?: string;
  errors?: Record<string, string[]>;
}

/**
 * Create and configure the API client.
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // Add auth token if available
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Add breadcrumb for request
      addBreadcrumb(
        `API Request: ${config.method?.toUpperCase()} ${config.url}`,
        'api',
        'info',
        {
          method: config.method,
          url: config.url,
        }
      );

      return config;
    },
    (error: AxiosError) => {
      trackApiError(
        error,
        error.config?.url || 'unknown',
        error.config?.method || 'unknown'
      );
      return Promise.reject(error);
    }
  );

  // Response interceptor
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      // Add breadcrumb for successful response
      addBreadcrumb(
        `API Response: ${response.status}`,
        'api',
        'info',
        {
          status: response.status,
          url: response.config.url,
        }
      );

      return response;
    },
    (error: AxiosError<ApiErrorResponse>) => {
      // Don't track cancelled requests
      if (axios.isCancel(error)) {
        return Promise.reject(error);
      }

      const endpoint = error.config?.url || 'unknown';
      const method = error.config?.method?.toUpperCase() || 'unknown';
      const statusCode = error.response?.status;

      // Add error breadcrumb
      addBreadcrumb(
        `API Error: ${statusCode || 'Network Error'}`,
        'api',
        'error',
        {
          endpoint,
          method,
          status: statusCode,
          message: error.message,
        }
      );

      // Track specific error types
      if (statusCode) {
        // Server errors (5xx)
        if (statusCode >= 500) {
          trackApiError(
            new Error(`Server error: ${statusCode} on ${method} ${endpoint}`),
            endpoint,
            method,
            statusCode
          );
        }
        // Auth errors (401, 403)
        else if (statusCode === 401 || statusCode === 403) {
          trackApiError(
            new Error(`Auth error: ${statusCode} on ${method} ${endpoint}`),
            endpoint,
            method,
            statusCode
          );
        }
        // Rate limiting (429)
        else if (statusCode === 429) {
          trackApiError(
            new Error(`Rate limited on ${method} ${endpoint}`),
            endpoint,
            method,
            statusCode
          );
        }
      } else {
        // Network errors
        trackApiError(
          new Error(`Network error on ${method} ${endpoint}: ${error.message}`),
          endpoint,
          method
        );
      }

      return Promise.reject(error);
    }
  );

  return client;
};

const apiClient = createApiClient();

export default apiClient;

/**
 * Helper to extract error message from API response.
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorResponse>;
    
    if (axiosError.response?.data) {
      const data = axiosError.response.data;
      return data.detail || data.message || 'An error occurred';
    }
    
    if (axiosError.message) {
      return axiosError.message;
    }
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
}
