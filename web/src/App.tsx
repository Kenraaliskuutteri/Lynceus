import React, { useState } from 'react';
import './App.css';
import { AuthForm } from './components/ui/AuthForm';
import Dashboard from './pages/Dashboard';
import AlertsPage from './pages/AlertsPage';
import { AuthProvider, useAuth } from './context/AuthContext';

type View = 'dashboard' | 'alerts';

const AppShell: React.FC = () => {
  const { isAuthenticated, isLoading, host, username, role, logout } = useAuth();
  const [view, setView] = useState<View>('dashboard');

  if (isLoading) {
    return (
      <div>
        <header className="site-header">
          <div className="brand-row">
            <div className="title-stack">
              <h1 className="site-title">LYNCEUS</h1>
              <p className="subtitle">Server Monitoring Dashboard</p>
            </div>
          </div>
        </header>
      </div>
    );
  }

  return (
    <div>
      <header className="site-header">
        <div className="brand-row">
          <div className="title-stack">
            <h1 className="site-title">LYNCEUS</h1>
            <p className="subtitle">
              {isAuthenticated ? `Connected to ${host} as ${username} (${role})` : 'Server Monitoring Dashboard'}
            </p>
          </div>
        </div>
      </header>

      {!isAuthenticated ? (
        <AuthForm />
      ) : (
        <>
          <div className="sub-nav">
            <div className="sub-nav-inner">
              <div className="sub-nav-status" style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <button
                  className="secondary-button"
                  style={{ fontWeight: view === 'dashboard' ? 700 : 400 }}
                  onClick={() => setView('dashboard')}
                >
                  Dashboard
                </button>
                <button
                  className="secondary-button"
                  style={{ fontWeight: view === 'alerts' ? 700 : 400 }}
                  onClick={() => setView('alerts')}
                >
                  Alerts
                </button>
              </div>
              <button className="secondary-button" onClick={logout}>
                Sign Out
              </button>
            </div>
          </div>

          <main className="content-page">
            {view === 'dashboard' ? <Dashboard /> : <AlertsPage />}
          </main>
        </>
      )}

      <footer>
        Lynceus System Control &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
};

export const App: React.FC = () => (
  <AuthProvider>
    <AppShell />
  </AuthProvider>
);

export default App;