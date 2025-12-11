/**
 * Language Context with AI Translation Support
 * 
 * Supports: English (en), Hindi (hi), Marathi (mr)
 * Uses Groq AI for dynamic translations
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import apiClient from '../services/api';

export type Language = 'en' | 'hi' | 'mr';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, fallback?: string) => string;
  isLoading: boolean;
}

// Static translations for common UI elements (instant, no API call needed)
const staticTranslations: Record<Language, Record<string, string>> = {
  en: {
    // Navigation
    'nav.dashboard': 'Dashboard',
    'nav.upload': 'Upload Bill',
    'nav.history': 'History',
    'nav.settings': 'Settings',
    'nav.negotiate': 'Negotiate',
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
  },
  hi: {
    // Navigation
    'nav.dashboard': 'डैशबोर्ड',
    'nav.upload': 'बिल अपलोड करें',
    'nav.history': 'इतिहास',
    'nav.settings': 'सेटिंग्स',
    'nav.negotiate': 'बातचीत',
    'nav.logout': 'लॉग आउट',
    
    // Dashboard
    'dashboard.welcome': 'वापसी पर स्वागत है!',
    'dashboard.overview': 'आपके मेडिकल बिल ऑडिट का सारांश।',
    'dashboard.totalDocs': 'कुल दस्तावेज़',
    'dashboard.issuesFound': 'समस्याएं मिलीं',
    'dashboard.potentialSavings': 'संभावित बचत',
    'dashboard.lettersGenerated': 'पत्र बनाए गए',
    'dashboard.uploadNew': 'नया बिल अपलोड करें',
    'dashboard.uploadDesc': 'AI ऑडिट के लिए मेडिकल बिल अपलोड करें।',
    'dashboard.generateLetter': 'बातचीत पत्र बनाएं',
    'dashboard.generateDesc': 'AI-संचालित विवाद पत्र बनाएं।',
    'dashboard.recentAudits': 'हाल के ऑडिट',
    'dashboard.viewAll': 'सभी इतिहास देखें',
    'dashboard.noActivity': 'कोई हालिया गतिविधि नहीं। शुरू करने के लिए बिल अपलोड करें!',
    
    // Audit
    'audit.results': 'ऑडिट परिणाम',
    'audit.score': 'ऑडिट स्कोर',
    'audit.issues': 'समस्याएं मिलीं',
    'audit.savings': 'संभावित बचत',
    'audit.noIssues': 'कोई समस्या नहीं मिली! आपका बिल सही लगता है।',
    'audit.disclaimer': 'AI-जनित विश्लेषण। स्वतंत्र रूप से सत्यापित करें।',
    
    // Negotiation
    'negotiate.title': 'बिल पर बातचीत',
    'negotiate.subtitle': 'अपने मेडिकल बिल पर बातचीत करने के लिए विवाद पत्र बनाएं और भेजें।',
    'negotiate.selectDoc': 'दस्तावेज़ चुनें',
    'negotiate.selectChannel': 'चैनल चुनें',
    'negotiate.selectTone': 'टोन चुनें',
    'negotiate.generate': 'पत्र बनाएं',
    'negotiate.send': 'पत्र भेजें',
    'negotiate.preview': 'पत्र पूर्वावलोकन',
    
    // Common
    'common.loading': 'लोड हो रहा है...',
    'common.error': 'एक त्रुटि हुई',
    'common.save': 'सहेजें',
    'common.cancel': 'रद्द करें',
    'common.submit': 'सबमिट करें',
    'common.back': 'वापस',
    'common.next': 'अगला',
    'common.viewDetails': 'विवरण देखें',
    
    // Regions
    'region.india': 'भारत',
    'region.us': 'संयुक्त राज्य अमेरिका',
  },
  mr: {
    // Navigation
    'nav.dashboard': 'डॅशबोर्ड',
    'nav.upload': 'बिल अपलोड करा',
    'nav.history': 'इतिहास',
    'nav.settings': 'सेटिंग्ज',
    'nav.negotiate': 'वाटाघाटी',
    'nav.logout': 'लॉग आउट',
    
    // Dashboard
    'dashboard.welcome': 'पुन्हा स्वागत आहे!',
    'dashboard.overview': 'तुमच्या वैद्यकीय बिल ऑडिटचा सारांश।',
    'dashboard.totalDocs': 'एकूण कागदपत्रे',
    'dashboard.issuesFound': 'समस्या सापडल्या',
    'dashboard.potentialSavings': 'संभाव्य बचत',
    'dashboard.lettersGenerated': 'पत्रे तयार केली',
    'dashboard.uploadNew': 'नवीन बिल अपलोड करा',
    'dashboard.uploadDesc': 'AI ऑडिटसाठी वैद्यकीय बिल अपलोड करा।',
    'dashboard.generateLetter': 'वाटाघाटी पत्र तयार करा',
    'dashboard.generateDesc': 'AI-चालित विवाद पत्रे तयार करा।',
    'dashboard.recentAudits': 'अलीकडील ऑडिट',
    'dashboard.viewAll': 'सर्व इतिहास पहा',
    'dashboard.noActivity': 'कोणतीही अलीकडील क्रियाकलाप नाही। सुरू करण्यासाठी बिल अपलोड करा!',
    
    // Audit
    'audit.results': 'ऑडिट निकाल',
    'audit.score': 'ऑडिट स्कोअर',
    'audit.issues': 'समस्या सापडल्या',
    'audit.savings': 'संभाव्य बचत',
    'audit.noIssues': 'कोणतीही समस्या सापडली नाही! तुमचे बिल अचूक दिसते.',
    'audit.disclaimer': 'AI-व्युत्पन्न विश्लेषण. स्वतंत्रपणे सत्यापित करा.',
    
    // Negotiation
    'negotiate.title': 'बिलावर वाटाघाटी',
    'negotiate.subtitle': 'तुमच्या वैद्यकीय बिलावर वाटाघाटी करण्यासाठी विवाद पत्र तयार करा आणि पाठवा.',
    'negotiate.selectDoc': 'कागदपत्र निवडा',
    'negotiate.selectChannel': 'चॅनेल निवडा',
    'negotiate.selectTone': 'टोन निवडा',
    'negotiate.generate': 'पत्र तयार करा',
    'negotiate.send': 'पत्र पाठवा',
    'negotiate.preview': 'पत्र पूर्वावलोकन',
    
    // Common
    'common.loading': 'लोड होत आहे...',
    'common.error': 'त्रुटी आली',
    'common.save': 'जतन करा',
    'common.cancel': 'रद्द करा',
    'common.submit': 'सबमिट करा',
    'common.back': 'मागे',
    'common.next': 'पुढे',
    'common.viewDetails': 'तपशील पहा',
    
    // Regions
    'region.india': 'भारत',
    'region.us': 'अमेरिका',
  },
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

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem('app_language');
    return (saved as Language) || 'en';
  });
  const [isLoading, setIsLoading] = useState(false);
  const [dynamicTranslations, setDynamicTranslations] = useState<Record<string, string>>({});

  useEffect(() => {
    localStorage.setItem('app_language', language);
  }, [language]);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    setDynamicTranslations({}); // Clear dynamic translations when language changes
  };

  // Translation function
  const t = (key: string, fallback?: string): string => {
    // First check static translations
    const staticValue = staticTranslations[language]?.[key];
    if (staticValue) return staticValue;

    // Then check dynamic (AI-translated) values
    const dynamicValue = dynamicTranslations[key];
    if (dynamicValue) return dynamicValue;

    // Fallback to English or provided fallback
    return staticTranslations.en?.[key] || fallback || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, isLoading }}>
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
export { languageNames, languageFlags };

