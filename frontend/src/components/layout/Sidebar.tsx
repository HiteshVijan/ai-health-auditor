import { NavLink, useLocation } from 'react-router-dom';
import { useLanguage } from '../../contexts/LanguageContext';

/**
 * Premium sidebar navigation with glassmorphism design.
 */
function Sidebar() {
  const { t } = useLanguage();
  const location = useLocation();

  const navItems = [
    { 
      path: '/dashboard', 
      labelKey: 'nav.dashboard', 
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
        </svg>
      ),
      gradient: 'from-emerald-500 to-teal-500',
    },
    { 
      path: '/upload', 
      labelKey: 'nav.upload', 
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      ),
      gradient: 'from-blue-500 to-indigo-500',
    },
    { 
      path: '/negotiate', 
      labelKey: 'nav.negotiate', 
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      ),
      gradient: 'from-violet-500 to-purple-500',
    },
    { 
      path: '/history', 
      labelKey: 'nav.history', 
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      ),
      gradient: 'from-amber-500 to-orange-500',
    },
    { 
      path: '/settings', 
      labelKey: 'nav.settings', 
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
      gradient: 'from-slate-500 to-gray-600',
    },
  ];

  return (
    <aside className="fixed left-0 top-16 bottom-0 w-64 hidden lg:block">
      {/* Background */}
      <div className="absolute inset-0 bg-white/80 backdrop-blur-xl border-r border-gray-200/50" />
      
      {/* Content */}
      <div className="relative h-full flex flex-col">
        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1.5">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
                            location.pathname.startsWith(item.path + '/');
            
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group
                  ${isActive
                    ? `bg-gradient-to-r ${item.gradient} text-white shadow-lg`
                    : 'text-gray-600 hover:bg-gray-100'
                  }`}
                style={isActive ? { boxShadow: '0 4px 14px -4px rgba(16, 185, 129, 0.4)' } : {}}
              >
                <span className={`${isActive ? 'text-white' : 'text-gray-500 group-hover:text-gray-700'}`}>
                  {item.icon}
                </span>
                <span className={`font-medium ${isActive ? '' : 'group-hover:text-gray-900'}`}>
                  {t(item.labelKey)}
                </span>
                
                {/* Active indicator */}
                {isActive && (
                  <div className="ml-auto w-2 h-2 rounded-full bg-white/50" />
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom section */}
        <div className="p-4 border-t border-gray-100">
          <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">💡</span>
              <span className="text-sm font-semibold text-emerald-700">Pro Tip</span>
            </div>
            <p className="text-xs text-emerald-600 leading-relaxed">
              Upload clear, high-resolution images of your bills for the best AI analysis results.
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
