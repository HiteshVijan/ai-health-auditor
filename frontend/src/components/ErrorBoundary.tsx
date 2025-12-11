/**
 * Error Boundary Component with Sentry Integration.
 *
 * Catches React errors and reports them to Sentry while
 * displaying a user-friendly fallback UI.
 */

import { Component, ReactNode, ErrorInfo } from 'react';
import * as Sentry from '@sentry/react';
import { Button, Card } from './common';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showDetails?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorId: string | null;
}

/**
 * Error Boundary component that catches React errors.
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Report to Sentry
    const errorId = Sentry.captureException(error, {
      extra: {
        componentStack: errorInfo.componentStack,
      },
    });

    this.setState({ errorId });

    // Call optional error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to console in development
    if (import.meta.env.DEV) {
      console.error('Error caught by ErrorBoundary:', error);
      console.error('Component stack:', errorInfo.componentStack);
    }
  }

  handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorId: null,
    });
  };

  handleReportFeedback = (): void => {
    if (this.state.errorId) {
      Sentry.showReportDialog({
        eventId: this.state.errorId,
        title: 'Something went wrong',
        subtitle: 'Our team has been notified. Would you like to provide more details?',
        subtitle2: '',
      });
    }
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <Card className="max-w-lg w-full text-center">
            <div className="text-5xl mb-4">😕</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Something went wrong
            </h1>
            <p className="text-gray-600 mb-6">
              We're sorry, but something unexpected happened. Our team has been
              notified and is working on a fix.
            </p>

            {this.props.showDetails && this.state.error && (
              <div className="mb-6 p-4 bg-gray-100 rounded-lg text-left">
                <p className="text-sm font-mono text-gray-700 break-all">
                  {this.state.error.message}
                </p>
              </div>
            )}

            {this.state.errorId && (
              <p className="text-xs text-gray-400 mb-4">
                Error ID: {this.state.errorId}
              </p>
            )}

            <div className="flex justify-center gap-3">
              <Button variant="secondary" onClick={this.handleRetry}>
                Try Again
              </Button>
              <Button onClick={() => window.location.reload()}>
                Refresh Page
              </Button>
            </div>

            {this.state.errorId && (
              <button
                onClick={this.handleReportFeedback}
                className="mt-4 text-sm text-primary-600 hover:text-primary-700 underline"
              >
                Report this issue
              </button>
            )}
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Sentry-wrapped Error Boundary with enhanced features.
 */
export const SentryErrorBoundary = Sentry.withErrorBoundary(ErrorBoundary, {
  fallback: ({ error, resetError }) => (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <Card className="max-w-lg w-full text-center">
        <div className="text-5xl mb-4">😕</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Something went wrong
        </h1>
        <p className="text-gray-600 mb-6">
          {error?.message || 'An unexpected error occurred'}
        </p>
        <div className="flex justify-center gap-3">
          <Button variant="secondary" onClick={resetError}>
            Try Again
          </Button>
          <Button onClick={() => window.location.reload()}>
            Refresh Page
          </Button>
        </div>
      </Card>
    </div>
  ),
  showDialog: true,
});

export default ErrorBoundary;

