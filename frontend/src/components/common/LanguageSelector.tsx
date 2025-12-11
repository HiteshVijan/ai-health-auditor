/**
 * Language Selector Component
 * 
 * Elegant dropdown for switching between English, Hindi, and Marathi
 */

import { useState, useRef, useEffect } from 'react';
import { useLanguage, Language, languageNames, languageFlags } from '../../contexts/LanguageContext';

export default function LanguageSelector() {
  const { language, setLanguage } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const languages: Language[] = ['en', 'hi', 'mr'];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-xl 
                   bg-white/10 hover:bg-white/20 backdrop-blur-sm
                   border border-white/20 transition-all duration-300
                   text-sm font-medium"
        aria-label="Select language"
      >
        <span className="text-lg">{languageFlags[language]}</span>
        <span className="hidden sm:inline">{languageNames[language]}</span>
        <svg 
          className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-40 rounded-xl overflow-hidden
                        bg-white shadow-2xl border border-gray-100
                        animate-in fade-in slide-in-from-top-2 duration-200 z-50">
          {languages.map((lang) => (
            <button
              key={lang}
              onClick={() => {
                setLanguage(lang);
                setIsOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 text-left
                         transition-colors duration-150 text-sm
                         ${language === lang 
                           ? 'bg-gradient-to-r from-emerald-50 to-teal-50 text-emerald-700 font-medium' 
                           : 'text-gray-700 hover:bg-gray-50'
                         }`}
            >
              <span className="text-lg">{languageFlags[lang]}</span>
              <span>{languageNames[lang]}</span>
              {language === lang && (
                <svg className="w-4 h-4 ml-auto text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

