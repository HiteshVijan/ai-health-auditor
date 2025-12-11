import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Badge, Loader } from '../components/common';
import apiClient from '../services/api';

/**
 * Audit issue structure.
 */
export interface AuditIssue {
  id: number;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  field?: string;
  expected?: string;
  actual?: string;
  amountImpact?: number;
}

/**
 * LLM summary key issue.
 */
export interface KeyIssue {
  id: number;
  description: string;
  recommendation: string;
}

/**
 * LLM summary structure.
 */
export interface LLMSummary {
  summaryBullets: string[];
  keyIssues: KeyIssue[];
}

/**
 * Complete audit result.
 */
export interface AuditResult {
  documentId: number;
  fileName: string;
  auditDate: string;
  score: number;
  totalIssues: number;
  criticalCount: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  potentialSavings: number;
  issues: AuditIssue[];
  llmSummary: LLMSummary;
}

/**
 * Score ring visualization component.
 */
function ScoreRing({ score }: { score: number }) {
  const radius = 60;
  const stroke = 8;
  const normalizedRadius = radius - stroke / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const getScoreColor = () => {
    if (score >= 80) return '#10B981'; // green
    if (score >= 60) return '#F59E0B'; // yellow
    if (score >= 40) return '#F97316'; // orange
    return '#EF4444'; // red
  };

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg height={radius * 2} width={radius * 2} className="-rotate-90">
        <circle
          stroke="#E5E7EB"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke={getScoreColor()}
          fill="transparent"
          strokeWidth={stroke}
          strokeDasharray={`${circumference} ${circumference}`}
          style={{ strokeDashoffset, transition: 'stroke-dashoffset 0.5s ease-in-out' }}
          strokeLinecap="round"
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-bold" style={{ color: getScoreColor() }}>
          {score}
        </span>
        <span className="text-xs text-gray-500">/ 100</span>
      </div>
    </div>
  );
}

/**
 * Severity badge component.
 */
function SeverityBadge({ severity }: { severity: AuditIssue['severity'] }) {
  const variants: Record<AuditIssue['severity'], 'danger' | 'warning' | 'info' | 'default'> = {
    critical: 'danger',
    high: 'danger',
    medium: 'warning',
    low: 'info',
  };

  const icons: Record<AuditIssue['severity'], string> = {
    critical: '🚨',
    high: '⚠️',
    medium: '⚡',
    low: 'ℹ️',
  };

  return (
    <Badge variant={variants[severity]} size="sm">
      {icons[severity]} {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </Badge>
  );
}

/**
 * Format issue type for display.
 */
function formatIssueType(type: string): string {
  return type
    .replace(/_/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Format currency amount.
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

/**
 * AuditPage component for displaying audit results and LLM summary.
 */
function AuditPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();

  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [expandedIssue, setExpandedIssue] = useState<number | null>(null);

  /**
   * Fetch audit data on mount.
   */
  useEffect(() => {
    const fetchAuditData = async () => {
      if (!documentId) {
        setError('No document ID provided');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);

        const response = await apiClient.get<AuditResult>(`/audits/${documentId}`);
        setAuditResult(response.data);
      } catch (err: any) {
        console.error('Error fetching audit data:', err);
        setError(err.response?.data?.detail || 'Failed to load audit results');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAuditData();
  }, [documentId]);

  /**
   * Export audit report as PDF.
   */
  const handleExportPdf = useCallback(async () => {
    if (!documentId) return;

    try {
      setIsExporting(true);

      const response = await apiClient.get(`/audits/${documentId}/export`, {
        responseType: 'blob',
      });

      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `audit-report-${documentId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Error exporting PDF:', err);
      setError('Failed to export PDF report');
    } finally {
      setIsExporting(false);
    }
  }, [documentId]);

  /**
   * Toggle issue expansion.
   */
  const toggleIssue = (issueId: number) => {
    setExpandedIssue((prev) => (prev === issueId ? null : issueId));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="loading-state">
        <div className="text-center">
          <Loader size="lg" />
          <p className="text-gray-600 mt-4">Analyzing your bill...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="error-state">
        <div className="text-center">
          <span className="text-5xl">⚠️</span>
          <h2 className="text-xl font-semibold text-gray-900 mt-4">Something went wrong</h2>
          <p className="text-gray-600 mt-2">{error}</p>
          <Button variant="secondary" className="mt-4" onClick={() => navigate('/dashboard')}>
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  if (!auditResult) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="no-data-state">
        <div className="text-center">
          <span className="text-5xl">📄</span>
          <h2 className="text-xl font-semibold text-gray-900 mt-4">No audit data found</h2>
          <Button variant="secondary" className="mt-4" onClick={() => navigate('/upload')}>
            Upload a Bill
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="audit-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Audit Results</h1>
          <p className="text-gray-600 mt-1">
            {auditResult.fileName} • Analyzed on{' '}
            {new Date(auditResult.auditDate).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={() => navigate(`/documents/${documentId}`)}
          >
            View Document
          </Button>
          <Button
            onClick={handleExportPdf}
            isLoading={isExporting}
            data-testid="export-pdf-button"
          >
            📥 Export PDF
          </Button>
        </div>
      </div>

      {/* Score & Stats Overview */}
      <div className="grid md:grid-cols-4 gap-6 mb-8">
        {/* Score Card */}
        <Card className="text-center" data-testid="score-card">
          <h3 className="text-sm font-medium text-gray-500 mb-4">Audit Score</h3>
          <ScoreRing score={auditResult.score} />
          <p className="text-sm text-gray-600 mt-4">
            {auditResult.score >= 80
              ? 'Bill looks accurate'
              : auditResult.score >= 60
              ? 'Some issues found'
              : 'Significant issues detected'}
          </p>
        </Card>

        {/* Stats Cards */}
        <Card data-testid="issues-card">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Total Issues</h3>
          <p className="text-3xl font-bold text-gray-900" data-testid="total-issues">
            {auditResult.totalIssues}
          </p>
          <div className="flex gap-2 mt-3 flex-wrap">
            {auditResult.criticalCount > 0 && (
              <Badge variant="danger" size="sm" data-testid="critical-count">
                {auditResult.criticalCount} Critical
              </Badge>
            )}
            {auditResult.highCount > 0 && (
              <Badge variant="danger" size="sm" data-testid="high-count">
                {auditResult.highCount} High
              </Badge>
            )}
            {auditResult.mediumCount > 0 && (
              <Badge variant="warning" size="sm" data-testid="medium-count">
                {auditResult.mediumCount} Medium
              </Badge>
            )}
            {auditResult.lowCount > 0 && (
              <Badge variant="info" size="sm" data-testid="low-count">
                {auditResult.lowCount} Low
              </Badge>
            )}
          </div>
        </Card>

        <Card data-testid="savings-card">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Potential Savings</h3>
          <p className="text-3xl font-bold text-green-600" data-testid="potential-savings">
            {formatCurrency(auditResult.potentialSavings)}
          </p>
          <p className="text-sm text-gray-500 mt-1">Based on detected issues</p>
        </Card>

        <Card>
          <h3 className="text-sm font-medium text-gray-500 mb-2">Quick Actions</h3>
          <div className="space-y-2">
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => navigate(`/negotiate/${documentId}`)}
            >
              📝 Generate Letter
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => navigate(`/documents/${documentId}`)}
            >
              📄 Review Document
            </Button>
          </div>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Issues List */}
        <div className="lg:col-span-2">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Issues Detected</h2>
              <span className="text-sm text-gray-500">
                {auditResult.issues.length} issue{auditResult.issues.length !== 1 ? 's' : ''}
              </span>
            </div>

            {auditResult.issues.length === 0 ? (
              <div className="text-center py-8" data-testid="no-issues">
                <span className="text-4xl">✅</span>
                <p className="text-gray-600 mt-2">No issues detected. Your bill looks accurate!</p>
              </div>
            ) : (
              <div className="space-y-3" data-testid="issues-list">
                {auditResult.issues.map((issue) => (
                  <div
                    key={issue.id}
                    className={`
                      border rounded-lg transition-all duration-200 cursor-pointer
                      ${expandedIssue === issue.id 
                        ? 'border-primary-300 bg-primary-50' 
                        : 'border-gray-200 hover:border-gray-300'
                      }
                    `}
                    onClick={() => toggleIssue(issue.id)}
                    data-testid={`issue-item-${issue.id}`}
                  >
                    <div className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <SeverityBadge severity={issue.severity} />
                            <span className="text-sm text-gray-500">
                              #{issue.id} • {formatIssueType(issue.type)}
                            </span>
                          </div>
                          <p className="text-gray-900" data-testid={`issue-description-${issue.id}`}>
                            {issue.description}
                          </p>
                        </div>
                        {issue.amountImpact && issue.amountImpact > 0 && (
                          <span className="text-sm font-medium text-red-600 ml-4">
                            {formatCurrency(issue.amountImpact)}
                          </span>
                        )}
                      </div>

                      {/* Expanded Details */}
                      {expandedIssue === issue.id && (
                        <div 
                          className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-2 gap-4 text-sm"
                          data-testid={`issue-details-${issue.id}`}
                        >
                          {issue.field && (
                            <div>
                              <span className="text-gray-500">Field:</span>
                              <p className="font-medium">{issue.field}</p>
                            </div>
                          )}
                          {issue.expected && (
                            <div>
                              <span className="text-gray-500">Expected:</span>
                              <p className="font-medium text-green-600">{issue.expected}</p>
                            </div>
                          )}
                          {issue.actual && (
                            <div>
                              <span className="text-gray-500">Actual:</span>
                              <p className="font-medium text-red-600">{issue.actual}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* LLM Summary Panel */}
        <div>
          <Card data-testid="llm-summary-card">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xl">🤖</span>
              <h2 className="text-lg font-semibold text-gray-900">AI Summary</h2>
            </div>

            {/* Summary Bullets */}
            {auditResult.llmSummary.summaryBullets.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-500 mb-3">Overview</h3>
                <ul className="space-y-2" data-testid="summary-bullets">
                  {auditResult.llmSummary.summaryBullets.map((bullet, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-2 text-sm text-gray-700"
                      data-testid={`summary-bullet-${index}`}
                    >
                      <span className="text-primary-500 mt-1">•</span>
                      {bullet}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Key Issues & Recommendations */}
            {auditResult.llmSummary.keyIssues.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-3">Key Recommendations</h3>
                <div className="space-y-3" data-testid="key-issues">
                  {auditResult.llmSummary.keyIssues.map((keyIssue) => (
                    <div
                      key={keyIssue.id}
                      className="p-3 bg-gray-50 rounded-lg"
                      data-testid={`key-issue-${keyIssue.id}`}
                    >
                      <p className="text-sm text-gray-900 mb-2">{keyIssue.description}</p>
                      <p className="text-xs text-primary-600 flex items-center gap-1">
                        <span>💡</span>
                        {keyIssue.recommendation}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {auditResult.llmSummary.summaryBullets.length === 0 &&
              auditResult.llmSummary.keyIssues.length === 0 && (
                <p className="text-gray-500 text-center py-4">
                  No AI summary available yet
                </p>
              )}
          </Card>

          {/* Action Card */}
          <Card className="mt-4">
            <h3 className="font-medium text-gray-900 mb-3">Next Steps</h3>
            <div className="space-y-2 text-sm">
              {auditResult.potentialSavings > 0 ? (
                <>
                  <p className="text-gray-600">
                    We found potential savings of{' '}
                    <strong className="text-green-600">
                      {formatCurrency(auditResult.potentialSavings)}
                    </strong>
                    . Consider:
                  </p>
                  <ul className="list-disc list-inside text-gray-600 space-y-1 ml-2">
                    <li>Generating a dispute letter</li>
                    <li>Contacting your provider</li>
                    <li>Reviewing line items in detail</li>
                  </ul>
                </>
              ) : (
                <p className="text-gray-600">
                  Your bill appears accurate. If you have concerns, you can still review the
                  document in detail.
                </p>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default AuditPage;

