import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Button } from '../components/common';
import { useLanguage } from '../contexts/LanguageContext';
import apiClient from '../services/api';

// =============================================================================
// TYPES
// =============================================================================

interface RecentAudit {
  document_id: number;
  filename: string;
  score: number | null;
  issues_count: number;
  potential_savings: number;
  currency: string;
  region: string;
  uploaded_at: string;
}

interface DashboardStats {
  total_documents: number;
  documents_this_month: number;
  total_audits: number;
  avg_score: number;
  total_issues_found: number;
  total_potential_savings: number;
  currency: string;
  letters_generated: number;
  recent_audits: RecentAudit[];
  primary_region: string;
}

// =============================================================================
// STAT CARD COMPONENT
// =============================================================================

function StatCard({ 
  icon, 
  value, 
  label, 
  sublabel,
  variant = 'emerald' 
}: {
  icon: React.ReactNode;
  value: string;
  label: string;
  sublabel?: string;
  variant?: 'emerald' | 'amber' | 'rose' | 'violet';
}) {
  const variants = {
    emerald: {
      iconBg: 'bg-emerald-100',
      iconColor: 'text-emerald-600',
      accent: 'bg-emerald-500',
    },
    amber: {
      iconBg: 'bg-amber-100',
      iconColor: 'text-amber-600',
      accent: 'bg-amber-500',
    },
    rose: {
      iconBg: 'bg-rose-100',
      iconColor: 'text-rose-600',
      accent: 'bg-rose-500',
    },
    violet: {
      iconBg: 'bg-violet-100',
      iconColor: 'text-violet-600',
      accent: 'bg-violet-500',
    },
  };

  const v = variants[variant];

  return (
    <div className="stat-card group">
      {/* Top accent bar */}
      <div className={`absolute top-0 left-0 right-0 h-1 ${v.accent} rounded-t-2xl`} />
      
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 mb-1">{label}</p>
          <p className="text-3xl font-bold text-gray-900 font-number">{value}</p>
          {sublabel && (
            <p className="text-xs text-gray-400 mt-1">{sublabel}</p>
          )}
        </div>
        <div className={`w-12 h-12 rounded-xl ${v.iconBg} ${v.iconColor} flex items-center justify-center
                        group-hover:scale-110 transition-transform duration-300`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// RECENT AUDIT ROW
// =============================================================================

function RecentAuditRow({ 
  audit, 
  onDelete 
}: { 
  audit: RecentAudit;
  onDelete: (documentId: number) => void;
}) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const formatCurrency = (amount: number, currency: string) => {
    if (currency === '₹') return `₹${amount.toLocaleString('en-IN')}`;
    return `$${amount.toLocaleString()}`;
  };

  const getScoreColor = (score: number | null) => {
    if (!score) return 'bg-gray-100 text-gray-500';
    if (score >= 80) return 'bg-emerald-100 text-emerald-700';
    if (score >= 60) return 'bg-amber-100 text-amber-700';
    return 'bg-rose-100 text-rose-700';
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!showConfirm) {
      setShowConfirm(true);
      return;
    }

    setIsDeleting(true);
    try {
      await onDelete(audit.document_id);
      setShowConfirm(false);
    } catch (error) {
      console.error('Delete failed:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="group flex items-center gap-4 p-4 rounded-xl hover:bg-gray-50 transition-all duration-200 relative">
      <Link 
        to={`/audit/${audit.document_id}`}
        className="flex items-center gap-4 flex-1 min-w-0"
      >
        {/* Region Flag */}
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-50 to-gray-100 
                        flex items-center justify-center text-lg border border-gray-100
                        group-hover:scale-105 transition-transform">
          {audit.region === 'IN' ? '🇮🇳' : '🇺🇸'}
        </div>

        {/* File Info */}
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900 truncate group-hover:text-emerald-600 transition-colors">
            {audit.filename}
          </p>
          <p className="text-sm text-gray-400">{formatDate(audit.uploaded_at)}</p>
        </div>

        {/* Savings */}
        <div className="text-right">
          <p className="font-semibold text-emerald-600">
            {formatCurrency(audit.potential_savings, audit.currency)}
          </p>
          <p className="text-xs text-gray-400">savings</p>
        </div>

        {/* Score Badge */}
        <div className={`px-3 py-1.5 rounded-lg text-sm font-semibold ${getScoreColor(audit.score)}`}>
          {audit.score || '--'}/100
        </div>

        {/* Arrow */}
        <svg className="w-5 h-5 text-gray-300 group-hover:text-emerald-500 group-hover:translate-x-1 transition-all" 
             fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </Link>

      {/* Delete Button */}
      <button
        onClick={handleDelete}
        disabled={isDeleting}
        className={`ml-2 p-2 rounded-lg transition-all duration-200 ${
          showConfirm
            ? 'bg-rose-100 text-rose-600 hover:bg-rose-200'
            : 'bg-transparent text-gray-400 hover:bg-rose-50 hover:text-rose-600 opacity-0 group-hover:opacity-100'
        } ${isDeleting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        title={showConfirm ? 'Click again to confirm delete' : 'Delete audit'}
      >
        {isDeleting ? (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        ) : (
          <svg 
            className="w-4 h-4" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" 
            />
          </svg>
        )}
      </button>
    </div>
  );
}

// =============================================================================
// MAIN DASHBOARD PAGE
// =============================================================================

function DashboardPage() {
  const { t } = useLanguage();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get<DashboardStats>(`/dashboard/stats?t=${Date.now()}`);
      setStats(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard');
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (documentId: number) => {
    try {
      await apiClient.delete(`/documents/${documentId}`);
      // Refresh stats after deletion
      await fetchStats();
    } catch (err) {
      console.error('Delete failed:', err);
      throw err;
    }
  };

  const formatSavings = (amount: number, currency: string) => {
    if (currency === '₹') {
      if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
      if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}K`;
      return `₹${amount.toFixed(0)}`;
    }
    if (amount >= 1000) return `$${(amount / 1000).toFixed(1)}K`;
    return `$${amount.toFixed(0)}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">
            <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          </div>
          <p className="text-gray-500">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card text-center py-12">
        <p className="text-rose-600 mb-4">{error}</p>
        <Button onClick={fetchStats}>Retry</Button>
      </div>
    );
  }

  const regionFlag = stats?.primary_region === 'IN' ? '🇮🇳' : '🇺🇸';
  const regionName = stats?.primary_region === 'IN' ? t('region.india') : t('region.us');

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">{regionFlag}</span>
            <span className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-sm font-medium">
              {regionName}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{t('dashboard.welcome')}</h1>
          <p className="text-gray-500 mt-1">{t('dashboard.overview')}</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
        <StatCard
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
          value={String(stats?.total_documents || 0)}
          label={t('dashboard.totalDocs')}
          sublabel={`${stats?.documents_this_month || 0} this month`}
          variant="emerald"
        />

        <StatCard
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          }
          value={String(stats?.total_issues_found || 0)}
          label={t('dashboard.issuesFound')}
          sublabel={`Avg score: ${stats?.avg_score?.toFixed(0) || '--'}/100`}
          variant="amber"
        />

        <StatCard
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          value={formatSavings(stats?.total_potential_savings || 0, stats?.currency || '₹')}
          label={t('dashboard.potentialSavings')}
          sublabel="Across all audits"
          variant="rose"
        />

        <StatCard
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          }
          value={String(stats?.letters_generated || 0)}
          label={t('dashboard.lettersGenerated')}
          sublabel="Ready to send"
          variant="violet"
        />
      </div>

      {/* Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Upload Card */}
        <div className="card-hover group cursor-pointer" onClick={() => window.location.href = '/upload'}>
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-500 
                            flex items-center justify-center text-white text-2xl
                            group-hover:scale-110 transition-transform duration-300 shadow-lg"
                 style={{ boxShadow: '0 8px 24px -8px rgba(16, 185, 129, 0.4)' }}>
              📤
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900 text-lg">{t('dashboard.uploadNew')}</h3>
              <p className="text-gray-500 text-sm mt-1 mb-4">{t('dashboard.uploadDesc')}</p>
              <Link to="/upload">
                <Button className="btn-primary">
                  {t('nav.upload')}
                  <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Negotiate Card */}
        <div className="card-hover group cursor-pointer" onClick={() => window.location.href = '/negotiate'}>
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-500 
                            flex items-center justify-center text-white text-2xl
                            group-hover:scale-110 transition-transform duration-300 shadow-lg"
                 style={{ boxShadow: '0 8px 24px -8px rgba(139, 92, 246, 0.4)' }}>
              ✉️
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900 text-lg">{t('dashboard.generateLetter')}</h3>
              <p className="text-gray-500 text-sm mt-1 mb-4">{t('dashboard.generateDesc')}</p>
              <Link to="/negotiate">
                <Button className="btn-secondary border-violet-200 text-violet-600 hover:bg-violet-50">
                  {t('nav.negotiate')}
                  <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Audits */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">{t('dashboard.recentAudits')}</h2>
          <Link 
            to="/history" 
            className="text-sm font-medium text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
          >
            {t('dashboard.viewAll')}
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>

        {stats?.recent_audits && stats.recent_audits.length > 0 ? (
          <div className="divide-y divide-gray-100 -mx-4">
            {stats.recent_audits.map((audit) => (
              <RecentAuditRow 
                key={audit.document_id} 
                audit={audit} 
                onDelete={handleDeleteDocument}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-gray-500">{t('dashboard.noActivity')}</p>
            <Link to="/upload" className="inline-block mt-4">
              <Button className="btn-primary">{t('nav.upload')}</Button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default DashboardPage;
