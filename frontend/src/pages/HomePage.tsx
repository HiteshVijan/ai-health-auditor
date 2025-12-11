import { Link } from 'react-router-dom';
import { APP_NAME } from '../utils/constants';

/**
 * Landing page for unauthenticated users.
 */
function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-accent-50">
      <header className="px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-3xl">🏥</span>
            <span className="text-xl font-bold text-gray-900">{APP_NAME}</span>
          </div>
          <div className="flex items-center space-x-4">
            <Link to="/login" className="text-gray-600 hover:text-gray-900 font-medium">
              Login
            </Link>
            <Link to="/register" className="btn-primary">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main className="px-6 py-20">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Stop Overpaying for <span className="text-gradient">Medical Bills</span>
          </h1>
          <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
            Our AI-powered platform audits your medical bills, identifies errors and overcharges,
            and helps you negotiate fair prices automatically.
          </p>
          <div className="flex justify-center space-x-4">
            <Link to="/register" className="btn-primary text-lg px-8 py-3">
              Start Free Audit
            </Link>
            <Link to="/login" className="btn-outline text-lg px-8 py-3">
              Learn More
            </Link>
          </div>
        </div>

        <div className="max-w-6xl mx-auto mt-24 grid md:grid-cols-3 gap-8">
          {[
            { icon: '📤', title: 'Upload', desc: 'Upload your medical bill (PDF or image)' },
            { icon: '🔍', title: 'Audit', desc: 'AI analyzes for errors and overcharges' },
            { icon: '💰', title: 'Save', desc: 'Get a negotiation letter to reduce your bill' },
          ].map((step, i) => (
            <div key={i} className="card text-center">
              <div className="text-4xl mb-4">{step.icon}</div>
              <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
              <p className="text-gray-600">{step.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

export default HomePage;

