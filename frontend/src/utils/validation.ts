/**
 * Validation utilities.
 */

/**
 * Validate email format.
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate password strength.
 */
export function isValidPassword(password: string): boolean {
  return password.length >= 8;
}

/**
 * Validate phone number format.
 */
export function isValidPhone(phone: string): boolean {
  const phoneRegex = /^\+?[\d\s\-()]{10,}$/;
  return phoneRegex.test(phone);
}

/**
 * Get password strength.
 */
export function getPasswordStrength(password: string): 'weak' | 'medium' | 'strong' {
  if (password.length < 8) return 'weak';

  let strength = 0;
  if (/[a-z]/.test(password)) strength++;
  if (/[A-Z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  if (/[^a-zA-Z0-9]/.test(password)) strength++;

  if (strength >= 4 && password.length >= 12) return 'strong';
  if (strength >= 3) return 'medium';
  return 'weak';
}

/**
 * Validate file type for upload.
 */
export function isValidFileType(file: File): boolean {
  const allowedTypes = [
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/tiff',
  ];
  return allowedTypes.includes(file.type);
}

/**
 * Validate file size (max 10MB).
 */
export function isValidFileSize(file: File, maxSizeMB: number = 10): boolean {
  const maxBytes = maxSizeMB * 1024 * 1024;
  return file.size <= maxBytes;
}

