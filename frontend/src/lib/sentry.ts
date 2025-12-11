/**
 * Sentry Integration Module.
 *
 * Configures Sentry for error tracking, performance monitoring,
 * and logging for the React frontend application.
 */

import * as Sentry from '@sentry/react';

/**
 * Sentry configuration options.
 */
interface SentryConfig {
  dsn?: string;
  environment?: string;
  release?: string;
  sampleRate?: number;
  tracesSampleRate?: number;
  replaysSessionSampleRate?: number;
  replaysOnErrorSampleRate?: number;
}

/**
 * Initialize Sentry SDK for React application.
 */
export function initSentry(config: SentryConfig = {}): void {
  const dsn = config.dsn || import.meta.env.VITE_SENTRY_DSN;

  if (!dsn) {
    console.warn('Sentry DSN not configured. Error tracking disabled.');
    return;
  }

  const environment = config.environment || import.meta.env.VITE_ENVIRONMENT || 'development';
  const release = config.release || import.meta.env.VITE_APP_VERSION || '1.0.0';

  Sentry.init({
    dsn,
    environment,
    release: `ai-health-auditor-frontend@${release}`,

    // Sample rates
    sampleRate: config.sampleRate ?? 1.0,
    tracesSampleRate: config.tracesSampleRate ?? 0.1,

    // Session Replay
    replaysSessionSampleRate: config.replaysSessionSampleRate ?? 0.1,
    replaysOnErrorSampleRate: config.replaysOnErrorSampleRate ?? 1.0,

    // Integrations
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
      Sentry.breadcrumbsIntegration({
        console: true,
        dom: true,
        fetch: true,
        history: true,
        xhr: true,
      }),
    ],

    // Filter events before sending
    beforeSend(event, hint) {
      // Filter out specific errors
      const error = hint.originalException as Error | undefined;
      
      if (error) {
        // Ignore network errors that are expected
        if (error.message?.includes('Network Error')) {
          return null;
        }
        
        // Ignore cancelled requests
        if (error.name === 'AbortError' || error.message?.includes('aborted')) {
          return null;
        }
        
        // Ignore ResizeObserver errors (common browser quirk)
        if (error.message?.includes('ResizeObserver')) {
          return null;
        }
      }

      // Scrub sensitive data from event
      if (event.request?.headers) {
        const sensitiveHeaders = ['authorization', 'cookie', 'x-api-key'];
        sensitiveHeaders.forEach(header => {
          if (event.request?.headers?.[header]) {
            event.request.headers[header] = '[Filtered]';
          }
        });
      }

      return event;
    },

    // Filter breadcrumbs
    beforeBreadcrumb(breadcrumb) {
      // Filter out noisy console logs
      if (breadcrumb.category === 'console' && breadcrumb.level === 'debug') {
        return null;
      }

      // Filter out specific URLs
      if (breadcrumb.category === 'fetch' || breadcrumb.category === 'xhr') {
        const url = breadcrumb.data?.url || '';
        if (url.includes('/metrics') || url.includes('/health')) {
          return null;
        }
      }

      return breadcrumb;
    },

    // Ignore specific errors
    ignoreErrors: [
      'ResizeObserver loop limit exceeded',
      'ResizeObserver loop completed with undelivered notifications',
      'Non-Error promise rejection captured',
      'Load failed',
      'Failed to fetch',
      'NetworkError',
      'ChunkLoadError',
    ],

    // Deny URLs
    denyUrls: [
      // Chrome extensions
      /extensions\//i,
      /^chrome:\/\//i,
      /^chrome-extension:\/\//i,
      // Firefox extensions
      /^moz-extension:\/\//i,
      // Safari extensions
      /^safari-extension:\/\//i,
    ],
  });

  console.log(`Sentry initialized for environment: ${environment}`);
}

/**
 * Capture an exception with additional context.
 */
export function captureException(
  error: Error,
  context?: Record<string, unknown>,
  tags?: Record<string, string>
): string | undefined {
  return Sentry.withScope((scope) => {
    if (context) {
      Object.entries(context).forEach(([key, value]) => {
        scope.setContext(key, value as Record<string, unknown>);
      });
    }

    if (tags) {
      Object.entries(tags).forEach(([key, value]) => {
        scope.setTag(key, value);
      });
    }

    return Sentry.captureException(error);
  });
}

/**
 * Capture a message event.
 */
export function captureMessage(
  message: string,
  level: Sentry.SeverityLevel = 'info',
  context?: Record<string, unknown>
): string | undefined {
  return Sentry.withScope((scope) => {
    scope.setLevel(level);

    if (context) {
      Object.entries(context).forEach(([key, value]) => {
        scope.setContext(key, value as Record<string, unknown>);
      });
    }

    return Sentry.captureMessage(message);
  });
}

/**
 * Set user context for all subsequent events.
 */
export function setUserContext(user: {
  id?: string;
  email?: string;
  username?: string;
} | null): void {
  if (user) {
    Sentry.setUser({
      id: user.id,
      email: user.email,
      username: user.username,
    });
  } else {
    Sentry.setUser(null);
  }
}

/**
 * Add a breadcrumb for debugging context.
 */
export function addBreadcrumb(
  message: string,
  category: string = 'custom',
  level: Sentry.SeverityLevel = 'info',
  data?: Record<string, unknown>
): void {
  Sentry.addBreadcrumb({
    message,
    category,
    level,
    data,
  });
}

/**
 * Track an API error with context.
 */
export function trackApiError(
  error: Error,
  endpoint: string,
  method: string,
  statusCode?: number
): string | undefined {
  return captureException(error, {
    api_call: {
      endpoint,
      method,
      status_code: statusCode,
    },
  }, {
    error_type: 'api_error',
    endpoint,
  });
}

/**
 * Track an LLM API error with context.
 */
export function trackLLMError(
  error: Error,
  provider: string,
  operation: string,
  promptLength?: number
): string | undefined {
  return captureException(error, {
    llm: {
      provider,
      operation,
      prompt_length: promptLength,
    },
  }, {
    error_type: 'llm_error',
    llm_provider: provider,
  });
}

/**
 * Create a performance transaction span.
 */
export function startTransaction(
  name: string,
  op: string
): Sentry.Span | undefined {
  return Sentry.startInactiveSpan({
    name,
    op,
  });
}

/**
 * Sentry Error Boundary wrapper component.
 */
export const SentryErrorBoundary = Sentry.ErrorBoundary;

/**
 * HOC to wrap components with Sentry profiling.
 */
export const withSentryProfiler = Sentry.withProfiler;

/**
 * Export Sentry for direct access when needed.
 */
export { Sentry };

