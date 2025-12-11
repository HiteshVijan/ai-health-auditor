import { Link } from 'react-router-dom';
import { logout } from '../../services/auth';
import { useLanguage } from '../../contexts/LanguageContext';
import LanguageSelector from '../common/LanguageSelector';
import { APP_NAME } from '../../utils/constants';

/**
 * Premium application header with navigation and language selector.
 */
function Header() {
  const { t } = useLanguage();

  const handleLogout = () => {
    logout();
  };

  return (
    <header className="fixed top-0 left-0 right-0 h-16 z-50">
      {/* Glassmorphism background */}
      <div 
        className="absolute inset-0 backdrop-blur-xl"
        style={{
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.95) 0%, rgba(5, 150, 105, 0.95) 100%)',
        }}
      />
      
      {/* Content */}
      <div className="relative flex items-center justify-between h-full px-4 lg:px-8">
        {/* Logo */}
        <Link 
          to="/dashboard" 
          className="flex items-center gap-3 group"
        >
          <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center
                          group-hover:bg-white/30 transition-all duration-300 group-hover:scale-105">
            <span className="text-2xl">🏥</span>
          </div>
          <div className="hidden sm:block">
            <span className="text-lg font-bold text-white tracking-tight">{APP_NAME}</span>
            <span className="block text-xs text-white/70 -mt-0.5">AI-Powered Auditing</span>
          </div>
        </Link>

        {/* Right side actions */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Language Selector */}
          <div className="text-white">
            <LanguageSelector />
          </div>

          {/* Settings */}
          <Link
            to="/settings"
            className="p-2.5 rounded-xl text-white/80 hover:text-white hover:bg-white/10 
                       transition-all duration-200"
            title={t('nav.settings')}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </Link>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 rounded-xl 
                       bg-white/10 hover:bg-white/20 backdrop-blur
                       text-white text-sm font-medium
                       border border-white/20
                       transition-all duration-300"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span className="hidden sm:inline">{t('nav.logout')}</span>
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
