import { useState, useEffect } from 'react';
import { Button, Input } from '../components/common';
import {
  lookupPrice,
  searchProcedures,
  getDatabaseStats,
  PriceLookupResponse,
  ProcedureSearchResult,
  DatabaseStats,
} from '../services/pricing';

// =============================================================================
// TYPES & HELPERS
// =============================================================================

function formatCurrency(amount: number): string {
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}K`;
  return `₹${amount.toLocaleString('en-IN')}`;
}

function formatFullCurrency(amount: number): string {
  return `₹${amount.toLocaleString('en-IN')}`;
}

// =============================================================================
// STAT CARD COMPONENT
// =============================================================================

function StatCard({
  icon,
  value,
  label,
  variant = 'emerald',
}: {
  icon: React.ReactNode;
  value: string;
  label: string;
  variant?: 'emerald' | 'amber' | 'violet' | 'sky';
}) {
  const variants = {
    emerald: { bg: 'bg-emerald-100', text: 'text-emerald-600' },
    amber: { bg: 'bg-amber-100', text: 'text-amber-600' },
    violet: { bg: 'bg-violet-100', text: 'text-violet-600' },
    sky: { bg: 'bg-sky-100', text: 'text-sky-600' },
  };
  const v = variants[variant];

  return (
    <div className="card text-center">
      <div className={`w-12 h-12 mx-auto rounded-xl ${v.bg} ${v.text} flex items-center justify-center mb-3`}>
        {icon}
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  );
}

// =============================================================================
// PRICE RESULT CARD
// =============================================================================

function PriceResultCard({ result }: { result: PriceLookupResponse }) {
  const cghs = result.benchmarks.find((b) => b.source === 'CGHS');
  const pmjay = result.benchmarks.find((b) => b.source === 'PMJAY');

  return (
    <div className="card animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-xl font-bold text-gray-900">{result.matched_procedure}</h3>
          <p className="text-sm text-gray-500 mt-1">
            Category: <span className="font-medium text-gray-700">{result.category}</span>
          </p>
        </div>
        <div className="text-right">
          <span className="badge-success">
            {Math.round(result.match_confidence * 100)}% match
          </span>
        </div>
      </div>

      {/* Fair Price Range */}
      <div className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl p-5 mb-6">
        <p className="text-sm font-medium text-emerald-700 mb-2">Fair Price Range</p>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold text-emerald-600">
            {formatFullCurrency(result.fair_price_range.low)}
          </span>
          <span className="text-gray-400">—</span>
          <span className="text-3xl font-bold text-emerald-600">
            {formatFullCurrency(result.fair_price_range.high)}
          </span>
        </div>
        <p className="text-xs text-emerald-600 mt-2">
          Median: {formatFullCurrency(result.fair_price_range.median)}
        </p>
      </div>

      {/* Benchmark Rates */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {cghs && (
          <div className="p-4 rounded-xl border border-gray-200 bg-gray-50">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">
                C
              </span>
              <span className="text-sm font-medium text-gray-700">CGHS Rate</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{formatFullCurrency(cghs.rate)}</p>
            <p className="text-xs text-gray-500 mt-1">Official government rate</p>
          </div>
        )}
        {pmjay && (
          <div className="p-4 rounded-xl border border-gray-200 bg-gray-50">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-6 h-6 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold">
                P
              </span>
              <span className="text-sm font-medium text-gray-700">PMJAY Rate</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{formatFullCurrency(pmjay.rate)}</p>
            <p className="text-xs text-gray-500 mt-1">Ayushman Bharat package</p>
          </div>
        )}
      </div>

      {/* Data Info */}
      <div className="flex items-center justify-between text-sm text-gray-500 pt-4 border-t border-gray-100">
        <span>📊 {result.data_points} price observations</span>
        <span>Updated: {new Date(result.last_updated).toLocaleDateString()}</span>
      </div>
    </div>
  );
}

// =============================================================================
// SEARCH RESULT ROW
// =============================================================================

function SearchResultRow({
  result,
  onSelect,
}: {
  result: ProcedureSearchResult;
  onSelect: (name: string) => void;
}) {
  return (
    <button
      onClick={() => onSelect(result.name)}
      className="w-full flex items-center gap-4 p-4 rounded-xl hover:bg-gray-50 transition-all duration-200 text-left group"
    >
      {/* Category Badge */}
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center text-emerald-600 font-bold text-sm">
        {result.category.charAt(0).toUpperCase()}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate group-hover:text-emerald-600 transition-colors">
          {result.name}
        </p>
        <p className="text-sm text-gray-400">{result.category}</p>
      </div>

      {/* Rates */}
      <div className="text-right">
        {result.cghs_rate && (
          <p className="font-semibold text-gray-900">{formatCurrency(result.cghs_rate)}</p>
        )}
        {result.pmjay_rate && !result.cghs_rate && (
          <p className="font-semibold text-gray-900">{formatCurrency(result.pmjay_rate)}</p>
        )}
        <p className="text-xs text-gray-400">
          {result.cghs_rate ? 'CGHS' : result.pmjay_rate ? 'PMJAY' : 'No rate'}
        </p>
      </div>

      {/* Arrow */}
      <svg
        className="w-5 h-5 text-gray-300 group-hover:text-emerald-500 group-hover:translate-x-1 transition-all"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </button>
  );
}

// =============================================================================
// MAIN PRICING PAGE
// =============================================================================

function PricingPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [city, setCity] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<ProcedureSearchResult[]>([]);
  const [priceResult, setPriceResult] = useState<PriceLookupResponse | null>(null);
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load stats on mount
  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await getDatabaseStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  // Debounced search
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setIsSearching(true);
        const results = await searchProcedures(searchQuery);
        setSearchResults(results.results);
      } catch (err) {
        console.error('Search failed:', err);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setError(null);
    setIsSearching(true);
    setPriceResult(null);

    try {
      const result = await lookupPrice(searchQuery, city || undefined);
      setPriceResult(result);
      setSearchResults([]);
    } catch (err) {
      setError('No pricing data found for this procedure. Try a different search term.');
      console.error('Lookup failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectProcedure = async (procedureName: string) => {
    setSearchQuery(procedureName);
    setSearchResults([]);
    setError(null);
    setIsSearching(true);
    setPriceResult(null);

    try {
      const result = await lookupPrice(procedureName, city || undefined);
      setPriceResult(result);
    } catch (err) {
      setError('Failed to fetch pricing details.');
      console.error('Lookup failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const popularSearches = [
    'Knee Replacement',
    'MRI Brain',
    'Appendectomy',
    'Cesarean',
    'Angioplasty',
    'Cataract Surgery',
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">💰</span>
          <span className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-sm font-medium">
            Pricing Intelligence
          </span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Medical Price Lookup</h1>
        <p className="text-gray-500 mt-1">
          Compare procedure costs with CGHS and PMJAY government rates
        </p>
      </div>

      {/* Stats Grid */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 stagger-children">
          <StatCard
            icon={
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            }
            value={String(stats.cghs_procedures)}
            label="CGHS Procedures"
            variant="emerald"
          />
          <StatCard
            icon={
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            }
            value={String(stats.pmjay_packages)}
            label="PMJAY Packages"
            variant="amber"
          />
          <StatCard
            icon={
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            }
            value={String(stats.total_hospitals)}
            label="Hospitals"
            variant="violet"
          />
          <StatCard
            icon={
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
            }
            value={String(stats.crowdsourced_points)}
            label="Price Points"
            variant="sky"
          />
        </div>
      )}

      {/* Search Section */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Search Procedure</h2>

        <div className="flex flex-col md:flex-row gap-4 mb-4">
          <div className="flex-1 relative">
            <Input
              type="text"
              placeholder="Enter procedure name (e.g., Knee Replacement, MRI Brain)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="pr-10"
            />
            {isSearching && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </div>
          <div className="md:w-48">
            <Input
              type="text"
              placeholder="City (optional)"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
          </div>
          <Button onClick={handleSearch} className="btn-primary">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Search
          </Button>
        </div>

        {/* Popular Searches */}
        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-gray-500">Popular:</span>
          {popularSearches.map((term) => (
            <button
              key={term}
              onClick={() => handleSelectProcedure(term)}
              className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-sm hover:bg-emerald-100 hover:text-emerald-700 transition-colors"
            >
              {term}
            </button>
          ))}
        </div>

        {/* Search Suggestions Dropdown */}
        {searchResults.length > 0 && !priceResult && (
          <div className="mt-4 border border-gray-200 rounded-xl divide-y divide-gray-100 max-h-80 overflow-y-auto">
            {searchResults.map((result) => (
              <SearchResultRow
                key={`${result.name}-${result.category}`}
                result={result}
                onSelect={handleSelectProcedure}
              />
            ))}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-rose-50 border border-rose-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-rose-700">No results found</p>
              <p className="text-sm text-rose-600">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Price Result */}
      {priceResult && <PriceResultCard result={priceResult} />}

      {/* Info Section */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
              <span className="text-xl">🏥</span>
            </div>
            <h3 className="font-semibold text-gray-900">What is CGHS?</h3>
          </div>
          <p className="text-gray-600 text-sm leading-relaxed">
            <strong>Central Government Health Scheme</strong> provides healthcare to central government employees and pensioners. 
            CGHS rates are official government-approved prices that empaneled hospitals must follow.
          </p>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center">
              <span className="text-xl">🆎</span>
            </div>
            <h3 className="font-semibold text-gray-900">What is PMJAY?</h3>
          </div>
          <p className="text-gray-600 text-sm leading-relaxed">
            <strong>Pradhan Mantri Jan Arogya Yojana</strong> (Ayushman Bharat) provides ₹5 lakh health coverage per family. 
            Package rates include all costs: surgery, room, medicines, and follow-up.
          </p>
        </div>
      </div>
    </div>
  );
}

export default PricingPage;

