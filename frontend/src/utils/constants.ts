/**
 * Application constants.
 */

export const APP_NAME = 'Health Bill Auditor';

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  UPLOAD: '/upload',
  AUDIT: '/audit',
  NEGOTIATE: '/negotiate',
  HISTORY: '/history',
  SETTINGS: '/settings',
} as const;

export const SEVERITY_COLORS = {
  critical: 'text-red-700 bg-red-100',
  high: 'text-orange-700 bg-orange-100',
  medium: 'text-yellow-700 bg-yellow-100',
  low: 'text-blue-700 bg-blue-100',
} as const;

export const STATUS_COLORS = {
  uploaded: 'text-blue-700 bg-blue-100',
  processing: 'text-yellow-700 bg-yellow-100',
  completed: 'text-green-700 bg-green-100',
  failed: 'text-red-700 bg-red-100',
} as const;

export const TONE_OPTIONS = [
  { value: 'formal', label: 'Formal', description: 'Professional and business-like' },
  { value: 'friendly', label: 'Friendly', description: 'Warm and collaborative' },
  { value: 'assertive', label: 'Assertive', description: 'Direct and firm' },
] as const;

export const CHANNEL_OPTIONS = [
  { value: 'email', label: 'Email', icon: '📧' },
  { value: 'whatsapp', label: 'WhatsApp', icon: '💬' },
  { value: 'both', label: 'Both', icon: '📱' },
] as const;

