/**
 * Hospital Dashboard Page
 * 
 * B2B feature for hospital administrators to:
 * - View pricing comparisons vs market
 * - See hospital scores and rankings
 * - Analyze competitor pricing
 * - Track trends over time
 */

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  getDashboardStats,
  getPricingComparison,
  getCompetitorAnalysis,
  getCategoryBreakdown,
  getAvailableHospitals,
  claimHospital,
  HospitalDashboardStats,
  PricingComparison,
  CompetitorAnalysis,
  CategoryBreakdown,
  AvailableHospital,
} from '../services/hospitalDashboard';

// ============================================
// Component
// ============================================

export default function HospitalDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasHospital, setHasHospital] = useState<boolean | null>(null);
  
  // Dashboard data
  const [stats, setStats] = useState<HospitalDashboardStats | null>(null);
  const [pricing, setPricing] = useState<PricingComparison | null>(null);
  const [competitors, setCompetitors] = useState<CompetitorAnalysis | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdown | null>(null);
  
  // Hospital claim flow
  const [availableHospitals, setAvailableHospitals] = useState<AvailableHospital[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [claimingHospital, setClaimingHospital] = useState<AvailableHospital | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [claimError, setClaimError] = useState<string | null>(null);
  const [claimForm, setClaimForm] = useState({
    contact_email: '',
    designation: '',
  });

  // Active tab
  const [activeTab, setActiveTab] = useState<'overview' | 'pricing' | 'competitors' | 'categories'>('overview');

  useEffect(() => {
    loadDashboard();
    // Also pre-load available hospitals for claim flow
    loadAvailableHospitals();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Try to load dashboard stats
      const statsData = await getDashboardStats();
      setStats(statsData);
      setHasHospital(true);
      
      // Load other data in parallel
      const [pricingData, competitorsData, categoriesData] = await Promise.all([
        getPricingComparison(),
        getCompetitorAnalysis(),
        getCategoryBreakdown(),
      ]);
      
      setPricing(pricingData);
      setCompetitors(competitorsData);
      setCategories(categoriesData);
    } catch (err: unknown) {
      console.error('Dashboard load error:', err);
      const error = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      const status = error.response?.status;
      const detail = error.response?.data?.detail || '';
      
      // Check for 403 or hospital-related errors
      if (status === 403 || detail.includes('hospital') || detail.includes('Hospital')) {
        // User doesn't have a hospital - show claim flow
        setHasHospital(false);
        await loadAvailableHospitals();
      } else {
        // For any other error, also show claim flow (better UX)
        setHasHospital(false);
        setError(null); // Clear error, show claim flow instead
        await loadAvailableHospitals();
      }
    } finally {
      setLoading(false);
    }
  };

  const loadAvailableHospitals = async () => {
    try {
      const data = await getAvailableHospitals(undefined, searchQuery || undefined);
      setAvailableHospitals(data.hospitals);
    } catch (err) {
      console.error('Failed to load hospitals:', err);
    }
  };

  const handleClaimHospital = async () => {
    if (!claimingHospital) return;
    
    // Validate form
    if (!claimForm.contact_email || !claimForm.designation) {
      setClaimError('Please fill in all fields');
      return;
    }
    
    setIsSubmitting(true);
    setClaimError(null);
    
    try {
      console.log('Claiming hospital:', claimingHospital.id);
      const result = await claimHospital({
        hospital_id: claimingHospital.id,
        verification_type: 'email',
        contact_email: claimForm.contact_email,
        designation: claimForm.designation,
      });
      console.log('Claim result:', result);
      
      // Success! Close modal and reload dashboard
      alert(`✅ Success! You are now the admin for ${claimingHospital.name}`);
      setClaimingHospital(null);
      setClaimForm({ contact_email: '', designation: '' });
      
      // Reload to show dashboard
      window.location.reload();
    } catch (err: unknown) {
      console.error('Claim error:', err);
      const error = err as { response?: { data?: { detail?: string } } };
      setClaimError(error.response?.data?.detail || 'Failed to claim hospital. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // ============================================
  // Render: Loading
  // ============================================
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-400"></div>
      </div>
    );
  }

  // ============================================
  // Render: No Hospital - Claim Flow
  // Show claim flow if: explicitly no hospital OR stats failed to load
  // ============================================
  if (hasHospital === false || (hasHospital === null && !stats)) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-2">Hospital Dashboard</h1>
          <p className="text-gray-400 mb-8">Claim your hospital to access the dashboard</p>
          
          {/* Search */}
          <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10 mb-6">
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="Search hospitals..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <button
                onClick={loadAvailableHospitals}
                className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-medium transition-colors"
              >
                Search
              </button>
            </div>
          </div>
          
          {/* Available Hospitals */}
          <div className="grid gap-4">
            {availableHospitals.map((hospital) => (
              <div
                key={hospital.id}
                className="bg-white/5 backdrop-blur-lg rounded-xl p-5 border border-white/10 hover:border-purple-500/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">{hospital.name}</h3>
                    <p className="text-gray-400">
                      {hospital.city}, {hospital.state} • {hospital.hospital_type}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      {hospital.total_bills_analyzed} bills analyzed
                    </p>
                  </div>
                  <button
                    onClick={() => setClaimingHospital(hospital)}
                    className="px-5 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-medium hover:opacity-90 transition-opacity"
                  >
                    Claim
                  </button>
                </div>
              </div>
            ))}
            
            {availableHospitals.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                No hospitals found. Try a different search term.
              </div>
            )}
          </div>
          
          {/* Claim Modal - Using Portal to render at document body */}
          {claimingHospital && createPortal(
            <div 
              className="fixed inset-0 bg-black/70 flex items-center justify-center p-4"
              style={{ zIndex: 99999 }}
              onClick={(e) => {
                if (e.target === e.currentTarget) {
                  setClaimingHospital(null);
                  setClaimError(null);
                }
              }}
            >
              <div 
                className="bg-slate-800 rounded-2xl p-8 max-w-md w-full border border-white/10 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                <h2 className="text-xl font-bold text-white mb-4">
                  Claim {claimingHospital.name}
                </h2>
                <p className="text-gray-400 mb-6">
                  Provide your details to verify your association with this hospital.
                </p>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Work Email
                    </label>
                    <input
                      type="email"
                      value={claimForm.contact_email}
                      onChange={(e) => setClaimForm({ ...claimForm, contact_email: e.target.value })}
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="admin@hospital.com"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Designation
                    </label>
                    <input
                      type="text"
                      value={claimForm.designation}
                      onChange={(e) => setClaimForm({ ...claimForm, designation: e.target.value })}
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="e.g., Billing Manager"
                    />
                  </div>
                </div>
                
                {claimError && (
                  <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                    {claimError}
                  </div>
                )}
                
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => {
                      setClaimingHospital(null);
                      setClaimError(null);
                    }}
                    disabled={isSubmitting}
                    className="flex-1 px-4 py-3 bg-white/10 text-white rounded-xl font-medium hover:bg-white/20 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleClaimHospital}
                    disabled={isSubmitting}
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    {isSubmitting ? 'Claiming...' : 'Submit Claim'}
                  </button>
                </div>
              </div>
            </div>,
            document.body
          )}
        </div>
      </div>
    );
  }

  // ============================================
  // Render: Dashboard
  // ============================================
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            🏥 {stats?.hospital_name || 'Hospital Dashboard'}
          </h1>
          <p className="text-gray-400">
            {stats?.city} • {stats?.hospital_type}
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 mb-6 text-red-400">
            {error}
          </div>
        )}

        {/* Score Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <ScoreCard
            title="Overall Score"
            score={stats?.overall_score || 0}
            change={stats?.score_change_30d}
            color="purple"
          />
          <ScoreCard
            title="Pricing Score"
            score={stats?.pricing_score || 0}
            subtitle="vs market average"
            color="blue"
          />
          <ScoreCard
            title="City Rank"
            score={stats?.city_rank || 0}
            subtitle={`of ${stats?.city_total || 0} hospitals`}
            isRank
            color="green"
          />
          <ScoreCard
            title="Bills Analyzed"
            score={stats?.total_bills_analyzed || 0}
            subtitle={`+${stats?.bills_last_30d || 0} last 30 days`}
            isCount
            color="orange"
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
                  ? 'bg-purple-600 text-white'
                  : 'bg-white/5 text-gray-400 hover:bg-white/10'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <OverviewTab
            stats={stats}
            competitors={competitors}
            categories={categories}
          />
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
    </div>
  );
}

// ============================================
// Sub-Components
// ============================================

interface ScoreCardProps {
  title: string;
  score: number;
  subtitle?: string;
  change?: number | null;
  isRank?: boolean;
  isCount?: boolean;
  color: 'purple' | 'blue' | 'green' | 'orange';
}

function ScoreCard({ title, score, subtitle, change, isRank, isCount, color }: ScoreCardProps) {
  const colorClasses = {
    purple: 'from-purple-600 to-purple-800',
    blue: 'from-blue-600 to-blue-800',
    green: 'from-green-600 to-green-800',
    orange: 'from-orange-600 to-orange-800',
  };

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} rounded-2xl p-6 border border-white/10`}>
      <p className="text-white/70 text-sm font-medium mb-2">{title}</p>
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-bold text-white">
          {isRank ? `#${score}` : isCount ? score.toLocaleString() : Math.round(score)}
        </span>
        {!isRank && !isCount && <span className="text-white/50">/100</span>}
      </div>
      {subtitle && <p className="text-white/50 text-sm mt-1">{subtitle}</p>}
      {change !== undefined && change !== null && (
        <p className={`text-sm mt-2 ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)} pts (30d)
        </p>
      )}
    </div>
  );
}

interface OverviewTabProps {
  stats: HospitalDashboardStats | null;
  competitors: CompetitorAnalysis | null;
  categories: CategoryBreakdown | null;
}

function OverviewTab({ stats, competitors, categories }: OverviewTabProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Position Card */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Market Position</h3>
        {competitors && (
          <div className="space-y-4">
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ${
              competitors.your_position === 'competitive' ? 'bg-green-500/20 text-green-400' :
              competitors.your_position === 'above_average' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              <span className="text-lg">
                {competitors.your_position === 'competitive' ? '✅' :
                 competitors.your_position === 'above_average' ? '⚠️' : '📉'}
              </span>
              <span className="font-medium capitalize">
                {competitors.your_position.replace('_', ' ')}
              </span>
            </div>
            <div className="space-y-2">
              {competitors.insights.map((insight, i) => (
                <p key={i} className="text-gray-300 text-sm">{insight}</p>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Rankings */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Rankings</h3>
        <div className="space-y-4">
          {stats?.city_rank && (
            <RankingRow
              label={`${stats.city} Rank`}
              rank={stats.city_rank}
              total={stats.city_total || 0}
            />
          )}
          {stats?.state_rank && (
            <RankingRow
              label="State Rank"
              rank={stats.state_rank}
              total={stats.state_total || 0}
            />
          )}
          {stats?.national_rank && (
            <RankingRow
              label="National Rank"
              rank={stats.national_rank}
              total={stats.national_total || 0}
            />
          )}
        </div>
      </div>

      {/* Top Categories */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10 lg:col-span-2">
        <h3 className="text-lg font-semibold text-white mb-4">Category Performance</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {categories?.categories.slice(0, 6).map((cat) => (
            <div key={cat.category} className="bg-white/5 rounded-xl p-4">
              <p className="text-white font-medium capitalize">{cat.category}</p>
              <p className="text-2xl font-bold text-white mt-1">
                ₹{cat.avg_price.toLocaleString()}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className={`text-sm ${
                  cat.status === 'competitive' ? 'text-green-400' :
                  cat.status === 'overpriced' ? 'text-red-400' : 'text-blue-400'
                }`}>
                  {cat.vs_benchmark_percent > 0 ? '+' : ''}{cat.vs_benchmark_percent}% vs benchmark
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RankingRow({ label, rank, total }: { label: string; rank: number; total: number }) {
  const percentile = Math.round((1 - rank / total) * 100);
  
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-white font-medium">#{rank} of {total}</span>
      </div>
      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
          style={{ width: `${percentile}%` }}
        />
      </div>
    </div>
  );
}

function PricingTab({ pricing }: { pricing: PricingComparison | null }) {
  if (!pricing) return <div className="text-gray-400">No pricing data available</div>;

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-green-400">{pricing.summary.competitive}</p>
          <p className="text-green-400/70 text-sm">Competitive</p>
        </div>
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-yellow-400">{pricing.summary.overpriced}</p>
          <p className="text-yellow-400/70 text-sm">Above Market</p>
        </div>
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-blue-400">{pricing.summary.underpriced}</p>
          <p className="text-blue-400/70 text-sm">Below Market</p>
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Recommendations</h3>
        <div className="space-y-3">
          {pricing.recommendations.map((rec, i) => (
            <p key={i} className="text-gray-300">{rec}</p>
          ))}
        </div>
      </div>

      {/* Procedure Table */}
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
            {pricing.procedures.map((proc) => (
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
    </div>
  );
}

function CompetitorsTab({ competitors }: { competitors: CompetitorAnalysis | null }) {
  if (!competitors) return <div className="text-gray-400">No competitor data available</div>;

  return (
    <div className="space-y-6">
      {/* Your Position */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Your Market Position</h3>
        <div className={`inline-flex items-center gap-3 px-6 py-3 rounded-xl ${
          competitors.your_position === 'competitive' ? 'bg-green-500/20' :
          competitors.your_position === 'above_average' ? 'bg-yellow-500/20' :
          'bg-blue-500/20'
        }`}>
          <span className="text-3xl">
            {competitors.your_position === 'competitive' ? '✅' :
             competitors.your_position === 'above_average' ? '⚠️' : '📉'}
          </span>
          <div>
            <p className="text-white font-semibold capitalize">
              {competitors.your_position.replace('_', ' ')}
            </p>
            <p className="text-gray-400 text-sm">in {competitors.your_hospital}</p>
          </div>
        </div>
      </div>

      {/* Insights */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Insights</h3>
        <div className="space-y-3">
          {competitors.insights.map((insight, i) => (
            <div key={i} className="flex items-start gap-3">
              <span className="text-purple-400 mt-1">💡</span>
              <p className="text-gray-300">{insight}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Competitor Breakdown */}
      <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Competitor Breakdown (Anonymized)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {competitors.competitors.map((comp, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-4">
              <p className="text-gray-400 text-sm capitalize">{comp.hospital_type} • {comp.city_tier}</p>
              <p className="text-2xl font-bold text-white mt-1">
                ₹{Math.round(comp.avg_price).toLocaleString()}
              </p>
              <p className="text-gray-500 text-sm mt-1">{comp.sample_count} observations</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CategoriesTab({ categories }: { categories: CategoryBreakdown | null }) {
  if (!categories) return <div className="text-gray-400">No category data available</div>;

  return (
    <div className="space-y-6">
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
            {categories.categories.map((cat) => (
              <tr key={cat.category} className="hover:bg-white/5">
                <td className="px-6 py-4">
                  <p className="text-white font-medium capitalize">{cat.category}</p>
                </td>
                <td className="px-6 py-4 text-right text-gray-400">
                  {cat.observation_count}
                </td>
                <td className="px-6 py-4 text-right text-white">
                  ₹{cat.avg_price.toLocaleString()}
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={cat.vs_benchmark_percent > 0 ? 'text-red-400' : 'text-green-400'}>
                    {cat.vs_benchmark_percent > 0 ? '+' : ''}{cat.vs_benchmark_percent}%
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
    </div>
  );
}

