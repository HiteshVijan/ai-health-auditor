/**
 * Language Context with AI Translation
 * 
 * Uses Groq AI for dynamic translations - NO hardcoded translations!
 * Only English source strings, AI translates to Hindi/Marathi on-demand.
 * Translations are cached in localStorage for performance.
 */

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import apiClient from '../services/api';

export type Language = 'en' | 'hi' | 'mr';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, fallback?: string) => string;
  translateText: (text: string) => Promise<string>;
  isTranslating: boolean;
}

// English source strings - SINGLE SOURCE OF TRUTH
const englishStrings: Record<string, string> = {
  // Navigation
  'nav.dashboard': 'Dashboard',
  'nav.upload': 'Upload Bill',
  'nav.history': 'History',
  'nav.settings': 'Settings',
  'nav.negotiate': 'Negotiate',
  'nav.pricing': 'Price Lookup',
  'nav.hospitalDashboard': 'Hospital Dashboard',
  'nav.logout': 'Logout',
  
  // Dashboard
  'dashboard.welcome': 'Welcome back!',
  'dashboard.overview': "Here's your medical bill audit overview.",
  'dashboard.totalDocs': 'Total Documents',
  'dashboard.issuesFound': 'Issues Found',
  'dashboard.potentialSavings': 'Potential Savings',
  'dashboard.lettersGenerated': 'Letters Generated',
  'dashboard.uploadNew': 'Upload New Bill',
  'dashboard.uploadDesc': 'Upload a medical bill for AI-powered audit.',
  'dashboard.generateLetter': 'Generate Negotiation Letter',
  'dashboard.generateDesc': 'Create AI-powered dispute letters.',
  'dashboard.recentAudits': 'Recent Audits',
  'dashboard.viewAll': 'View All History',
  'dashboard.noActivity': 'No recent activity. Upload a bill to get started!',
  
  // Audit
  'audit.results': 'Audit Results',
  'audit.score': 'Audit Score',
  'audit.issues': 'Issues Found',
  'audit.savings': 'Potential Savings',
  'audit.noIssues': 'No issues found! Your bill appears accurate.',
  'audit.disclaimer': 'AI-generated analysis. Verify independently.',
  
  // Negotiation
  'negotiate.title': 'Negotiate Bill',
  'negotiate.subtitle': 'Generate and send a dispute letter to negotiate your medical bill.',
  'negotiate.selectDoc': 'Select Document',
  'negotiate.selectChannel': 'Select Channel',
  'negotiate.selectTone': 'Select Tone',
  'negotiate.generate': 'Generate Letter',
  'negotiate.send': 'Send Letter',
  'negotiate.preview': 'Letter Preview',
  
  // Common
  'common.loading': 'Loading...',
  'common.error': 'An error occurred',
  'common.save': 'Save',
  'common.cancel': 'Cancel',
  'common.submit': 'Submit',
  'common.back': 'Back',
  'common.next': 'Next',
  'common.viewDetails': 'View Details',
  
  // Regions
  'region.india': 'India',
  'region.us': 'United States',
  
  // Hospital Dashboard
  'hospital.title': 'Hospital Dashboard',
  'hospital.claim': 'Claim Hospital',
  'hospital.stats': 'Statistics',
  'hospital.pricing': 'Pricing Comparison',
  'hospital.competitors': 'Competitor Analysis',
  'hospital.trends': 'Trends',
};

const languageNames: Record<Language, string> = {
  en: 'English',
  hi: 'हिंदी',
  mr: 'मराठी',
};

const languageFlags: Record<Language, string> = {
  en: '🇬🇧',
  hi: '🇮🇳',
  mr: '🇮🇳',
};

// Cache key for localStorage
const CACHE_KEY = 'ai_translations';
const CACHE_VERSION = 'v1';

interface TranslationCache {
  version: string;
  translations: Record<Language, Record<string, string>>;
}

function getCache(): TranslationCache {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      const parsed = JSON.parse(cached);
      if (parsed.version === CACHE_VERSION) {
        return parsed;
      }
    }
  } catch {
    // Ignore cache errors
  }
  return { version: CACHE_VERSION, translations: { en: {}, hi: {}, mr: {} } };
}

function setCache(cache: TranslationCache) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch {
    // Ignore cache errors
  }
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem('app_language');
    return (saved as Language) || 'en';
  });
  const [isTranslating, setIsTranslating] = useState(false);
  const [translationCache, setTranslationCache] = useState<Record<string, string>>(() => {
    const cache = getCache();
    return cache.translations[language as Language] || {};
  });

  // Load cached translations when language changes
  useEffect(() => {
    localStorage.setItem('app_language', language);
    const cache = getCache();
    setTranslationCache(cache.translations[language] || {});
    
    // If not English, trigger background translation of missing keys
    if (language !== 'en') {
      translateMissingKeys();
    }
  }, [language]);

  // Translate missing keys in background
  const translateMissingKeys = useCallback(async () => {
    if (language === 'en') return;
    
    const cache = getCache();
    const cached = cache.translations[language] || {};
    
    // Find keys that need translation
    const missingKeys = Object.keys(englishStrings).filter(key => !cached[key]);
    
    if (missingKeys.length === 0) return;
    
    setIsTranslating(true);
    
    try {
      // Batch translate (up to 20 at a time to avoid large requests)
      const batchSize = 20;
      for (let i = 0; i < missingKeys.length; i += batchSize) {
        const batch = missingKeys.slice(i, i + batchSize);
        const textsToTranslate = batch.map(key => englishStrings[key]);
        
        const response = await apiClient.post('/translate/batch', {
          texts: textsToTranslate,
          target_language: language,
        });
        
        if (response.data?.translations) {
          const newTranslations: Record<string, string> = {};
          batch.forEach((key, index) => {
            if (response.data.translations[index]) {
              newTranslations[key] = response.data.translations[index];
            }
          });
          
          // Update cache
          const updatedCache = getCache();
          updatedCache.translations[language] = {
            ...updatedCache.translations[language],
            ...newTranslations,
          };
          setCache(updatedCache);
          
          // Update state
          setTranslationCache(prev => ({ ...prev, ...newTranslations }));
        }
      }
    } catch (error) {
      console.error('Translation failed:', error);
      // Fallback to English if translation fails
    } finally {
      setIsTranslating(false);
    }
  }, [language]);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
  };

  // Translation function - returns cached translation or English fallback
  const t = useCallback((key: string, fallback?: string): string => {
    // English - return source string
    if (language === 'en') {
      return englishStrings[key] || fallback || key;
    }
    
    // Check cache first
    if (translationCache[key]) {
      return translationCache[key];
    }
    
    // Fallback to English while translation loads
    return englishStrings[key] || fallback || key;
  }, [language, translationCache]);

  // Translate arbitrary text (for dynamic content like AI responses)
  const translateText = useCallback(async (text: string): Promise<string> => {
    if (language === 'en' || !text) return text;
    
    try {
      const response = await apiClient.post('/translate', {
        text,
        target_language: language,
      });
      return response.data?.translated_text || text;
    } catch {
      return text; // Return original on error
    }
  }, [language]);

  return (
    <LanguageContext.Provider value={{ 
      language, 
      setLanguage, 
      t, 
      translateText,
      isTranslating 
    }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return context;
}

// Export utilities
export { languageNames, languageFlags, englishStrings };
