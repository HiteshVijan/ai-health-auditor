/**
 * B2B Hospital Dashboard Page
 * 
 * Main dashboard for hospital administrators.
 * Shows pricing comparisons, scores, and analytics.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getB2BAdmin, b2bLogout, isB2BAuthenticated } from '../../services/b2bAuth';
import {
  getDashboardStats,
  getPricingOverview,
  getCompetitorAnalysis,
  getCategoryBreakdown,
  DashboardStats,
  PricingOverview,
  CompetitorAnalysis,
  CategoryData,
} from '../../services/b2bDashboard';

export default function B2BDashboardPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'pricing' | 'competitors' | 'categories'>('overview');

  // Data
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pricing, setPricing] = useState<PricingOverview | null>(null);
  const [competitors, setCompetitors] = useState<CompetitorAnalysis | null>(null);
  const [categories, setCategories] = useState<CategoryData[]>([]);

  const admin = getB2BAdmin();

  useEffect(() => {
    if (!isB2BAuthenticated()) {
      navigate('/b2b/login');
      return;
    }
    loadDashboard();
  }, [navigate]);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);

    try {
      const [statsData, pricingData, competitorsData, categoriesData] = await Promise.all([
        getDashboardStats(),
        getPricingOverview(),
        getCompetitorAnalysis(),
        getCategoryBreakdown(),
      ]);

      setStats(statsData);
      setPricing(pricingData);
      setCompetitors(competitorsData);
      setCategories(categoriesData.categories);
    } catch (err: unknown) {
      console.error('Dashboard error:', err);
      const error = err as { response?: { status?: number; data?: { detail?: string } } };
      if (error.response?.status === 401) {
        navigate('/b2b/login');
      } else {
        setError(error.response?.data?.detail || 'Failed to load dashboard');
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-400 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Header */}
      <header className="bg-white/5 backdrop-blur-lg border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-2xl">🏥</div>
            <div>
              <h1 className="text-xl font-bold text-white">{stats?.hospital_name || 'Hospital Dashboard'}</h1>
              <p className="text-sm text-gray-400">{stats?.city}, {stats?.state}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-white font-medium">{admin?.full_name}</p>
              <p className="text-gray-400 text-sm">{admin?.designation}</p>
            </div>
            <button
              onClick={b2bLogout}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-400">
            {error}
          </div>
        )}

        {/* Score Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <ScoreCard
            title="Overall Score"
            value={stats?.overall_score || 0}
            suffix="/100"
            color="blue"
          />
          <ScoreCard
            title="Pricing Score"
            value={stats?.pricing_score || 0}
            suffix="/100"
            subtitle="vs market average"
            color="cyan"
          />
          <ScoreCard
            title="City Rank"
            value={stats?.city_rank || 0}
            prefix="#"
            subtitle={`of ${stats?.city_total || 0} hospitals`}
            color="purple"
          />
          <ScoreCard
            title="Bills Analyzed"
            value={stats?.total_bills_analyzed || 0}
            color="green"
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto">
          {(['overview', 'pricing', 'competitors', 'categories'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2.5 rounded-xl font-medium capitalize transition-colors whitespace-nowrap ${
                activeTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'bg-white/5 text-gray-400 hover:bg-white/10'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === 'overview' && (
            <OverviewTab stats={stats} pricing={pricing} competitors={competitors} />
          )}
          {activeTab === 'pricing' && (
            <PricingTab pricing={pricing} />
          )}
          {activeTab === 'competitors' && (
            <CompetitorsTab competitors={competitors} />
          )}
          {activeTab === 'categories' && (
            <CategoriesTab categories={categories} />
          )}
        </div>
      </main>
    </div>
  );
}

// ============================================
// Sub-components
// ============================================

interface ScoreCardProps {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  subtitle?: string;
  color: 'blue' | 'cyan' | 'purple' | 'green';
}

function ScoreCard({ title, value, prefix, suffix, subtitle, color }: ScoreCardProps) {
  const colors = {
    blue: 'from-blue-600 to-blue-800',
    cyan: 'from-cyan-600 to-cyan-800',
    purple: 'from-purple-600 to-purple-800',
    green: 'from-green-600 to-green-800',
  };

  return (
    <div className={`bg-gradient-to-br ${colors[color]} rounded-2xl p-6 border border-white/10`}>
      <p className="text-white/70 text-sm font-medium mb-2">{title}</p>
      <div className="flex items-baseline gap-1">
        {prefix && <span className="text-2xl font-bold text-white">{prefix}</span>}
        <span className="text-4xl font-bold text-white">{Math.round(value)}</span>
        {suffix && <span className="text-white/50">{suffix}</span>}
      </div>
      {subtitle && <p className="text-white/50 text-sm mt-1">{subtitle}</p>}
    </div>
  );
}

function OverviewTab({ stats, pricing, competitors }: {
  stats: DashboardStats | null;
  pricing: PricingOverview | null;
  competitors: CompetitorAnalysis | null;
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Quick Stats */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Pricing Summary</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 bg-green-500/10 rounded-xl">
            <p className="text-3xl font-bold text-green-400">{pricing?.competitive_count || 0}</p>
            <p className="text-green-400/70 text-sm">Competitive</p>
          </div>
          <div className="text-center p-4 bg-yellow-500/10 rounded-xl">
            <p className="text-3xl font-bold text-yellow-400">{pricing?.overpriced_count || 0}</p>
            <p className="text-yellow-400/70 text-sm">Above Market</p>
          </div>
          <div className="text-center p-4 bg-blue-500/10 rounded-xl">
            <p className="text-3xl font-bold text-blue-400">{pricing?.underpriced_count || 0}</p>
            <p className="text-blue-400/70 text-sm">Below Market</p>
          </div>
        </div>
      </div>

      {/* Market Position */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Market Position</h3>
        {competitors?.segments.map((seg, i) => (
          <div key={i} className="mb-4 last:mb-0">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-400">{seg.segment}</span>
              <span className={seg.your_position === 'competitive' ? 'text-green-400' : seg.your_position === 'above' ? 'text-yellow-400' : 'text-blue-400'}>
                {seg.difference_percent > 0 ? '+' : ''}{seg.difference_percent}%
              </span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${seg.your_position === 'competitive' ? 'bg-green-500' : seg.your_position === 'above' ? 'bg-yellow-500' : 'bg-blue-500'}`}
                style={{ width: `${Math.min(100, 50 + seg.difference_percent)}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Recommendations */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10 lg:col-span-2">
        <h3 className="text-lg font-semibold text-white mb-4">Recommendations</h3>
        <div className="space-y-3">
          {pricing?.recommendations.map((rec, i) => (
            <div key={i} className="flex items-start gap-3 p-3 bg-white/5 rounded-lg">
              <span className="text-blue-400">💡</span>
              <p className="text-gray-300">{rec}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PricingTab({ pricing }: { pricing: PricingOverview | null }) {
  if (!pricing) return <div className="text-gray-400">No pricing data available</div>;

  return (
    <div className="bg-white/5 backdrop-blur-lg rounded-2xl border border-white/10 overflow-hidden">
      <table className="w-full">
        <thead className="bg-white/5">
          <tr>
            <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Procedure</th>
            <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">Your Price</th>
            <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">Market Avg</th>
            <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">CGHS Rate</th>
            <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">vs Market</th>
            <th className="px-6 py-4 text-center text-sm font-medium text-gray-400">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {pricing.procedures.slice(0, 20).map((proc) => (
            <tr key={proc.procedure_id} className="hover:bg-white/5">
              <td className="px-6 py-4">
                <p className="text-white font-medium">{proc.procedure_name}</p>
                <p className="text-gray-500 text-sm capitalize">{proc.category}</p>
              </td>
              <td className="px-6 py-4 text-right text-white">
                {proc.your_price ? `₹${proc.your_price.toLocaleString()}` : '-'}
              </td>
              <td className="px-6 py-4 text-right text-gray-400">
                {proc.market_average ? `₹${proc.market_average.toLocaleString()}` : '-'}
              </td>
              <td className="px-6 py-4 text-right text-gray-400">
                {proc.cghs_rate ? `₹${proc.cghs_rate.toLocaleString()}` : '-'}
              </td>
              <td className="px-6 py-4 text-right">
                {proc.vs_market_percent !== null && (
                  <span className={proc.vs_market_percent > 0 ? 'text-red-400' : 'text-green-400'}>
                    {proc.vs_market_percent > 0 ? '+' : ''}{proc.vs_market_percent}%
                  </span>
                )}
              </td>
              <td className="px-6 py-4 text-center">
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  proc.status === 'competitive' ? 'bg-green-500/20 text-green-400' :
                  proc.status === 'overpriced' ? 'bg-red-500/20 text-red-400' :
                  'bg-blue-500/20 text-blue-400'
                }`}>
                  {proc.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CompetitorsTab({ competitors }: { competitors: CompetitorAnalysis | null }) {
  if (!competitors) return <div className="text-gray-400">No competitor data available</div>;

  return (
    <div className="space-y-6">
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Competitor Segments</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {competitors.segments.map((seg, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-5">
              <p className="text-gray-400 text-sm mb-2">{seg.segment}</p>
              <div className="flex items-end justify-between">
                <div>
                  <p className="text-2xl font-bold text-white">₹{seg.avg_price.toLocaleString()}</p>
                  <p className="text-gray-500 text-sm">Market Average</p>
                </div>
                <div className="text-right">
                  <p className={`text-xl font-bold ${seg.your_position === 'competitive' ? 'text-green-400' : seg.your_position === 'above' ? 'text-yellow-400' : 'text-blue-400'}`}>
                    {seg.difference_percent > 0 ? '+' : ''}{seg.difference_percent}%
                  </p>
                  <p className="text-gray-500 text-sm capitalize">{seg.your_position}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Insights</h3>
        <div className="space-y-2">
          {competitors.insights.map((insight, i) => (
            <p key={i} className="text-gray-300 flex items-start gap-2">
              <span className="text-blue-400">ℹ️</span>
              {insight}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

function CategoriesTab({ categories }: { categories: CategoryData[] }) {
  if (!categories.length) return <div className="text-gray-400">No category data available</div>;

  return (
    <div className="bg-white/5 backdrop-blur-lg rounded-2xl border border-white/10 overflow-hidden">
      <table className="w-full">
        <thead className="bg-white/5">
          <tr>
            <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Category</th>
            <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">Observations</th>
            <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">Avg Price</th>
            <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">vs Benchmark</th>
            <th className="px-6 py-4 text-center text-sm font-medium text-gray-400">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {categories.map((cat) => (
            <tr key={cat.category} className="hover:bg-white/5">
              <td className="px-6 py-4 text-white font-medium capitalize">{cat.category}</td>
              <td className="px-6 py-4 text-right text-gray-400">{cat.observation_count}</td>
              <td className="px-6 py-4 text-right text-white">₹{cat.avg_price.toLocaleString()}</td>
              <td className="px-6 py-4 text-right">
                <span className={cat.vs_benchmark > 0 ? 'text-red-400' : 'text-green-400'}>
                  {cat.vs_benchmark > 0 ? '+' : ''}{cat.vs_benchmark}%
                </span>
              </td>
              <td className="px-6 py-4 text-center">
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  cat.status === 'competitive' ? 'bg-green-500/20 text-green-400' :
                  cat.status === 'overpriced' ? 'bg-red-500/20 text-red-400' :
                  'bg-blue-500/20 text-blue-400'
                }`}>
                  {cat.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

