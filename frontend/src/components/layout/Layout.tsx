import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import { useLanguage } from '../../contexts/LanguageContext';

/**
 * Main application layout with header and sidebar.
 * Features premium glassmorphism design.
 */
function Layout() {
  const { language } = useLanguage();

  return (
    <div 
      className="min-h-screen"
      lang={language}
      style={{
        background: 'linear-gradient(180deg, #ecfdf5 0%, #f0fdf4 30%, #f8fafc 100%)',
      }}
    >
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6 lg:p-8 ml-0 lg:ml-64 mt-16">
          <div className="max-w-7xl mx-auto animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

export default Layout;

