import { useParams, Link, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Card, Button, Badge } from '../components/common';
import apiClient from '../services/api';

// =============================================================================
// TYPES
// =============================================================================

interface AuditIssue {
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  amount_impact: number | null;
  fair_price?: number;
  recommendation?: string;
}

interface CompetitorPrice {
  name: string;
  price: number;
  test?: string;
}

interface MarketComparison {
  hospital_type?: string;
  price_tier?: string;
  competitor_prices?: CompetitorPrice[];
  cghs_rate?: number;
  market_average?: number;
}

interface NegotiationStrategy {
  success_probability?: string;
  expected_discount?: string;
  best_approach?: string;
  scripts?: string[];
  escalation_path?: string;
  timing?: string;
}

interface ScanSummary {
  text_length: number;
  lines_detected: number;
  ocr_confidence: string;
}

interface CategoryBreakdown {
  category: string;
  amount: number;
  percent_of_total: number;
  status?: string;
}

interface KeyMetrics {
  total_bill: number;
  tax_amount: number;
  payments_made: number;
  largest_category?: string;
  largest_category_amount: number;
}

interface DocumentBreakdown {
  scan_summary?: ScanSummary;
  hospital_name?: string;
  hospital_type?: string;
  bill_number?: string;
  bill_date?: string;
  patient_name?: string;
  categories?: CategoryBreakdown[];
  key_metrics?: KeyMetrics;
  raw_text_preview?: string;
}

interface InsiderAnalysis {
  hospital_profit_margin?: string;
  negotiation_window?: string;
  decision_maker?: string;
  best_time_to_call?: string;
  leverage_points?: string[];
  red_flags?: string[];
  priority_items?: string[];
}

interface AuditData {
  document_id?: number;
  score: number;
  total_issues: number;
  potential_savings: number;
  currency: string;
  region: string;
  issues: AuditIssue[];
  market_comparison?: MarketComparison;
  insider_tips?: string[];
  negotiation_strategy?: NegotiationStrategy;
  document_breakdown?: DocumentBreakdown;
  insider_analysis?: InsiderAnalysis;
  summary?: string;
  ocr_used?: boolean;
  ai_provider?: string;
  disclaimer?: string;
}

// =============================================================================
// COMPONENTS
// =============================================================================

function ScoreGauge({ score }: { score: number }) {
  const getColor = (s: number) => {
    if (s >= 80) return { ring: 'text-green-500', bg: 'bg-green-100' };
    if (s >= 60) return { ring: 'text-yellow-500', bg: 'bg-yellow-100' };
    return { ring: 'text-red-500', bg: 'bg-red-100' };
  };
  const colors = getColor(score);
  
  return (
    <div className={`relative w-32 h-32 ${colors.bg} rounded-full flex items-center justify-center`}>
      <svg className="absolute w-full h-full -rotate-90">
        <circle cx="64" cy="64" r="56" fill="none" stroke="#e5e7eb" strokeWidth="12" />
        <circle 
          cx="64" cy="64" r="56" fill="none" 
          className={colors.ring}
          strokeWidth="12"
          strokeDasharray={`${score * 3.52} 352`}
          strokeLinecap="round"
        />
      </svg>
      <div className="text-center">
        <div className={`text-3xl font-bold ${colors.ring.replace('text-', 'text-')}`}>{score}</div>
        <div className="text-xs text-gray-500">/100</div>
      </div>
    </div>
  );
}

function CategoryBar({ category, amount, percent, currency }: { 
  category: string; amount: number; percent: number; currency: string 
}) {
  const formatAmount = (amt: number) => {
    if (currency === '₹') return `₹${amt.toLocaleString('en-IN')}`;
    return `$${amt.toFixed(2)}`;
  };
  
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{category}</span>
        <span className="text-gray-600">{formatAmount(amount)} ({percent.toFixed(1)}%)</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div 
          className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
    </div>
  );
}

function InsiderTip({ tip, index }: { tip: string; index: number }) {
  const icons = ['💡', '🎯', '⚡', '🔑', '💪'];
  return (
    <div className="flex gap-3 p-3 bg-amber-50 border-l-4 border-amber-400 rounded-r-lg">
      <span className="text-xl">{icons[index % icons.length]}</span>
      <p className="text-gray-700">{tip}</p>
    </div>
  );
}

function NegotiationScript({ script, index }: { script: string; index: number }) {
  const [copied, setCopied] = useState(false);
  
  const copyToClipboard = () => {
    navigator.clipboard.writeText(script);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className="relative p-4 bg-gray-800 text-gray-100 rounded-lg font-mono text-sm">
      <button 
        onClick={copyToClipboard}
        className="absolute top-2 right-2 text-gray-400 hover:text-white"
      >
        {copied ? '✓ Copied!' : '📋 Copy'}
      </button>
      <div className="text-gray-400 text-xs mb-2">Script #{index + 1}</div>
      "{script}"
    </div>
  );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

function AuditResultsPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [audit, setAudit] = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'issues' | 'breakdown' | 'insider' | 'strategy'>('issues');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Add cache-busting timestamp to prevent stale data
        const response = await apiClient.get<AuditData>(
          `/audit/${documentId}?t=${Date.now()}`
        );
        setAudit(response.data);
        setError(null);
      } catch (err: any) {
        console.error('Failed to fetch audit:', err);
        setError(err.response?.data?.detail || 'Failed to load audit results');
      } finally {
        setLoading(false);
      }
    };

    if (documentId) {
      fetchData();
    }
  }, [documentId]);

  const formatCurrency = (amount: number, currency: string = '₹') => {
    if (currency === '₹') return `₹${amount.toLocaleString('en-IN')}`;
    return `$${amount.toFixed(2)}`;
  };

  const handleDelete = async () => {
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true);
      return;
    }

    setIsDeleting(true);
    try {
      await apiClient.delete(`/documents/${documentId}`);
      navigate('/history', { replace: true });
    } catch (err: any) {
      console.error('Failed to delete:', err);
      alert(err.response?.data?.detail || 'Failed to delete document');
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <p className="text-gray-500">Analyzing your bill with AI...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 text-xl mb-4">⚠️ {error}</div>
        <Link to="/history"><Button>Back to History</Button></Link>
      </div>
    );
  }

  if (!audit) return null;

  const db = audit.document_breakdown;
  const ia = audit.insider_analysis;
  const ns = audit.negotiation_strategy;
  const mc = audit.market_comparison;

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex flex-col md:flex-row justify-between items-start gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">🏥 Audit Results</h1>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className="text-gray-600">Document #{documentId}</span>
            <Badge variant={audit.region === 'IN' ? 'info' : 'default'}>
              {audit.region === 'IN' ? '🇮🇳 India' : '🇺🇸 US'}
            </Badge>
            {audit.ai_provider && (
              <Badge variant="success">🤖 {audit.ai_provider.toUpperCase()} AI</Badge>
            )}
            {audit.ocr_used && (
              <Badge variant="default">📷 OCR Used</Badge>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {showDeleteConfirm ? (
            <div className="flex items-center gap-2 bg-red-50 px-3 py-2 rounded-lg border border-red-200">
              <span className="text-red-700 text-sm font-medium">Delete this audit?</span>
              <Button 
                onClick={handleDelete}
                disabled={isDeleting}
                className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 text-sm"
              >
                {isDeleting ? 'Deleting...' : 'Yes, Delete'}
              </Button>
              <Button 
                onClick={() => setShowDeleteConfirm(false)}
                className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-3 py-1 text-sm"
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button 
              onClick={handleDelete}
              className="bg-red-100 hover:bg-red-200 text-red-600 border border-red-200"
            >
              🗑️ Delete
            </Button>
          )}
          <Link to={`/negotiate/${documentId}`}>
            <Button className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700">
              ✉️ Generate Negotiation Letter
            </Button>
          </Link>
        </div>
      </div>

      {/* Score Overview Cards */}
      <div className="grid md:grid-cols-4 gap-4 mb-8">
        <Card className="text-center p-6">
          <div className="text-sm text-gray-500 mb-3">Audit Score</div>
          <div className="flex justify-center">
            <ScoreGauge score={audit.score} />
          </div>
        </Card>

        <Card className="text-center p-6">
          <div className="text-sm text-gray-500 mb-2">Issues Found</div>
          <div className="text-4xl font-bold text-gray-900">{audit.total_issues}</div>
          <div className="flex justify-center gap-1 mt-2">
            {audit.issues.filter(i => i.severity === 'critical').length > 0 && (
              <Badge variant="danger">{audit.issues.filter(i => i.severity === 'critical').length} Critical</Badge>
            )}
            {audit.issues.filter(i => i.severity === 'high').length > 0 && (
              <Badge variant="warning">{audit.issues.filter(i => i.severity === 'high').length} High</Badge>
            )}
          </div>
        </Card>

        <Card className="text-center p-6">
          <div className="text-sm text-gray-500 mb-2">Potential Savings</div>
          <div className="text-4xl font-bold text-green-600">
            {formatCurrency(audit.potential_savings, audit.currency)}
          </div>
          <div className="text-sm text-gray-500 mt-1">estimated</div>
        </Card>

        <Card className="text-center p-6">
          <div className="text-sm text-gray-500 mb-2">Success Rate</div>
          <div className="text-4xl font-bold text-blue-600">
            {ns?.success_probability?.toUpperCase() || 'N/A'}
          </div>
          <div className="text-sm text-gray-500 mt-1">
            {ns?.expected_discount || 'Contact for discount'}
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex border-b mb-6 overflow-x-auto">
        {[
          { id: 'issues', label: '🔍 Issues', count: audit.total_issues },
          { id: 'breakdown', label: '📊 Bill Breakdown' },
          { id: 'insider', label: '🤫 Insider Tips' },
          { id: 'strategy', label: '💪 Negotiation Strategy' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab.id 
                ? 'border-blue-600 text-blue-600' 
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className="ml-2 px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-xs">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {/* Issues Tab */}
        {activeTab === 'issues' && (
          <div className="space-y-4">
            {audit.issues.length === 0 ? (
              <Card className="text-center py-12">
                <div className="text-6xl mb-4">✅</div>
                <p className="text-xl text-gray-700">No issues found!</p>
                <p className="text-gray-500 mt-2">Your bill appears to be accurate.</p>
              </Card>
            ) : (
              audit.issues.map((issue, index) => (
                <Card key={index} className="hover:shadow-lg transition-shadow">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-start gap-4">
                      <Badge
                        variant={
                          issue.severity === 'critical' ? 'danger' :
                          issue.severity === 'high' ? 'warning' :
                          issue.severity === 'medium' ? 'info' : 'default'
                        }
                        className="mt-1"
                      >
                        {issue.severity.toUpperCase()}
                      </Badge>
                      <div>
                        <p className="font-semibold text-gray-900">{issue.type}</p>
                        <p className="text-gray-600 mt-1">{issue.description}</p>
                        {issue.recommendation && (
                          <p className="text-sm text-blue-600 mt-2">
                            💡 {issue.recommendation}
                          </p>
                        )}
                      </div>
                    </div>
                    {issue.amount_impact && (
                      <div className="text-right md:min-w-[120px]">
                        <p className="text-xl font-bold text-red-600">
                          {formatCurrency(issue.amount_impact, audit.currency)}
                        </p>
                        <p className="text-sm text-gray-500">impact</p>
                        {issue.fair_price && (
                          <p className="text-xs text-green-600 mt-1">
                            Fair: {formatCurrency(issue.fair_price, audit.currency)}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </Card>
              ))
            )}
          </div>
        )}

        {/* Bill Breakdown Tab */}
        {activeTab === 'breakdown' && db && (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Scan Summary */}
            <Card title="📄 Document Scan Summary">
              <div className="space-y-3">
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">Hospital</span>
                  <span className="font-medium">{db.hospital_name || 'N/A'}</span>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">Type</span>
                  <Badge variant="info">{db.hospital_type || 'Private'}</Badge>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">Patient</span>
                  <span className="font-medium">{db.patient_name || 'N/A'}</span>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">OCR Confidence</span>
                  <Badge variant={db.scan_summary?.ocr_confidence === 'high' ? 'success' : 'warning'}>
                    {db.scan_summary?.ocr_confidence?.toUpperCase() || 'MEDIUM'}
                  </Badge>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-gray-600">Text Extracted</span>
                  <span>{db.scan_summary?.text_length?.toLocaleString() || 0} chars</span>
                </div>
              </div>
            </Card>

            {/* Key Metrics */}
            {db.key_metrics && (
              <Card title="📈 Key Metrics">
                <div className="space-y-3">
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-gray-600">Total Bill</span>
                    <span className="text-2xl font-bold">
                      {formatCurrency(db.key_metrics.total_bill, audit.currency)}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-gray-600">Taxes (GST)</span>
                    <span>{formatCurrency(db.key_metrics.tax_amount, audit.currency)}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-gray-600">Largest Category</span>
                    <span className="font-medium">{db.key_metrics.largest_category || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b bg-green-50 -mx-4 px-4">
                    <span className="text-green-700 font-medium">Potential Savings</span>
                    <span className="text-xl font-bold text-green-600">
                      {formatCurrency(audit.potential_savings, audit.currency)}
                    </span>
                  </div>
                </div>
              </Card>
            )}

            {/* Category Breakdown */}
            {db.categories && db.categories.length > 0 && (
              <Card title="📊 Category Breakdown" className="md:col-span-2">
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    {db.categories.slice(0, Math.ceil(db.categories.length / 2)).map((cat, i) => (
                      <CategoryBar 
                        key={i}
                        category={cat.category}
                        amount={cat.amount}
                        percent={cat.percent_of_total}
                        currency={audit.currency}
                      />
                    ))}
                  </div>
                  <div>
                    {db.categories.slice(Math.ceil(db.categories.length / 2)).map((cat, i) => (
                      <CategoryBar 
                        key={i}
                        category={cat.category}
                        amount={cat.amount}
                        percent={cat.percent_of_total}
                        currency={audit.currency}
                      />
                    ))}
                  </div>
                </div>
              </Card>
            )}

            {/* Market Comparison */}
            {mc && (
              <Card title="🏪 Market Comparison" className="md:col-span-2">
                <div className="grid md:grid-cols-3 gap-4">
                  {mc.competitor_prices?.map((cp, i) => (
                    <div key={i} className="p-4 bg-gray-50 rounded-lg text-center">
                      <div className="font-medium text-gray-700">{cp.name}</div>
                      <div className="text-2xl font-bold text-blue-600 mt-2">
                        {formatCurrency(cp.price, audit.currency)}
                      </div>
                      {cp.test && <div className="text-sm text-gray-500 mt-1">{cp.test}</div>}
                    </div>
                  ))}
                </div>
                {mc.cghs_rate && (
                  <div className="mt-4 p-4 bg-green-50 rounded-lg flex justify-between items-center">
                    <span className="text-green-700 font-medium">CGHS Government Rate</span>
                    <span className="text-2xl font-bold text-green-600">
                      {formatCurrency(mc.cghs_rate, audit.currency)}
                    </span>
                  </div>
                )}
              </Card>
            )}
          </div>
        )}

        {/* Insider Tips Tab */}
        {activeTab === 'insider' && (
          <div className="space-y-6">
            {/* Insider Tips */}
            {audit.insider_tips && audit.insider_tips.length > 0 && (
              <Card title="🤫 Insider Tips">
                <div className="space-y-3">
                  {audit.insider_tips.map((tip, i) => (
                    <InsiderTip key={i} tip={tip} index={i} />
                  ))}
                </div>
              </Card>
            )}

            {/* Insider Analysis */}
            {ia && (
              <>
                <Card title="🔍 Hospital Analysis">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <div className="text-sm text-blue-600 font-medium">Hospital Profit Margin</div>
                      <div className="text-lg font-semibold mt-1">{ia.hospital_profit_margin || 'N/A'}</div>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg">
                      <div className="text-sm text-green-600 font-medium">Negotiation Window</div>
                      <div className="text-lg font-semibold mt-1">{ia.negotiation_window || 'N/A'}</div>
                    </div>
                    <div className="p-4 bg-purple-50 rounded-lg">
                      <div className="text-sm text-purple-600 font-medium">Decision Maker</div>
                      <div className="text-lg font-semibold mt-1">{ia.decision_maker || 'N/A'}</div>
                    </div>
                    <div className="p-4 bg-orange-50 rounded-lg">
                      <div className="text-sm text-orange-600 font-medium">Best Time to Call</div>
                      <div className="text-lg font-semibold mt-1">{ia.best_time_to_call || 'N/A'}</div>
                    </div>
                  </div>
                </Card>

                {ia.leverage_points && ia.leverage_points.length > 0 && (
                  <Card title="💪 Your Leverage Points">
                    <div className="space-y-2">
                      {ia.leverage_points.map((point, i) => (
                        <div key={i} className="flex gap-3 p-3 bg-green-50 rounded-lg">
                          <span className="text-green-600 font-bold">✓</span>
                          <span>{point}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {ia.priority_items && ia.priority_items.length > 0 && (
                  <Card title="🎯 Priority Items to Negotiate">
                    <ol className="list-decimal list-inside space-y-2">
                      {ia.priority_items.map((item, i) => (
                        <li key={i} className="text-gray-700 py-2 border-b last:border-0">{item}</li>
                      ))}
                    </ol>
                  </Card>
                )}
              </>
            )}
          </div>
        )}

        {/* Negotiation Strategy Tab */}
        {activeTab === 'strategy' && ns && (
          <div className="space-y-6">
            {/* Strategy Overview */}
            <Card title="📋 Strategy Overview">
              <div className="grid md:grid-cols-3 gap-4">
                <div className="text-center p-6 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl text-white">
                  <div className="text-sm opacity-80">Success Probability</div>
                  <div className="text-3xl font-bold mt-2">
                    {ns.success_probability?.toUpperCase() || 'MEDIUM'}
                  </div>
                </div>
                <div className="text-center p-6 bg-gradient-to-br from-green-500 to-green-600 rounded-xl text-white">
                  <div className="text-sm opacity-80">Expected Discount</div>
                  <div className="text-3xl font-bold mt-2">{ns.expected_discount || '10-20%'}</div>
                </div>
                <div className="text-center p-6 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl text-white">
                  <div className="text-sm opacity-80">Best Time</div>
                  <div className="text-lg font-bold mt-2">{ns.timing || 'Before Payment'}</div>
                </div>
              </div>
            </Card>

            {/* Best Approach */}
            {ns.best_approach && (
              <Card title="🎯 Best Approach">
                <p className="text-lg text-gray-700 leading-relaxed">{ns.best_approach}</p>
              </Card>
            )}

            {/* Scripts */}
            {ns.scripts && ns.scripts.length > 0 && (
              <Card title="📝 Ready-to-Use Scripts">
                <div className="space-y-4">
                  {ns.scripts.map((script, i) => (
                    <NegotiationScript key={i} script={script} index={i} />
                  ))}
                </div>
              </Card>
            )}

            {/* Escalation Path */}
            {ns.escalation_path && (
              <Card title="📞 Escalation Path">
                <div className="flex flex-wrap items-center gap-2">
                  {ns.escalation_path.split('→').map((step, i, arr) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className={`px-4 py-2 rounded-full ${
                        i === 0 ? 'bg-blue-100 text-blue-700' :
                        i === arr.length - 1 ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {step.trim()}
                      </div>
                      {i < arr.length - 1 && <span className="text-gray-400">→</span>}
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* CTA */}
            <Card className="bg-gradient-to-r from-green-500 to-green-600 text-white">
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div>
                  <h3 className="text-xl font-bold">Ready to Negotiate?</h3>
                  <p className="opacity-90 mt-1">Generate a personalized letter with all the details</p>
                </div>
                <Link to={`/negotiate/${documentId}`}>
                  <Button className="bg-white text-green-600 hover:bg-gray-100">
                    ✉️ Generate Letter Now
                  </Button>
                </Link>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Summary */}
      {audit.summary && (
        <Card className="mt-8 bg-blue-50 border-blue-200">
          <h3 className="font-semibold text-blue-900 mb-2">📋 Summary</h3>
          <p className="text-blue-800">{audit.summary}</p>
        </Card>
      )}

      {/* Disclaimer */}
      <div className="mt-8 p-4 bg-gray-100 rounded-lg text-sm text-gray-600">
        <p className="font-medium text-gray-700 mb-1">⚠️ Disclaimer</p>
        <p>{audit.disclaimer || 'AI-generated analysis. Prices are estimates. Verify with official sources.'}</p>
      </div>
    </div>
  );
}

export default AuditResultsPage;
