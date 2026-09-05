import React, { useState } from 'react';
import './App.css';
import { AuthForm } from "./components/ui/AuthForm";
import Dashboard from './pages/Dashboard';
import { normalizeHost } from './utils/host';

function loadStoredHost(): string | null {
  const raw = localStorage.getItem('lynceus_host');
  if (!raw) return null;
  try {
    return normalizeHost(raw);
  } catch {
    localStorage.removeItem('lynceus_host');
    localStorage.removeItem('lynceus_key');
    return null;
  }
}

export const App: React.FC = () => {
  const [storedHost] = useState<string | null>(loadStoredHost());
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(
    Boolean(storedHost && localStorage.getItem('lynceus_key'))
  );
  const [hostAddress, setHostAddress] = useState<string>(storedHost || '');

  const handleConnect = (host: string, key: string) => {
    localStorage.setItem('lynceus_host', host);
    localStorage.setItem('lynceus_key', key);
    setHostAddress(host);
    setIsAuthenticated(true);
  };

  const handleDisconnect = () => {
    localStorage.removeItem('lynceus_host');
    localStorage.removeItem('lynceus_key');
    setIsAuthenticated(false);
  };

  return (
    <div>
      <header className="site-header">
        <div className="brand-row">
          <div className="title-stack">
            <h1 className="site-title">LYNCEUS</h1>
            <p className="subtitle">
              {isAuthenticated ? `Connected to ${hostAddress}` : 'Server Monitoring Dashboard'}
            </p>
          </div>
        </div>
      </header>

      {!isAuthenticated ? (
        <AuthForm onConnect={handleConnect} />
      ) : (
        <>
          <div className="sub-nav">
            <div className="sub-nav-inner">
              <div className="sub-nav-status">
                <span>Status:</span>
                <code>CONNECTED</code>
              </div>
              <button className="secondary-button" onClick={handleDisconnect}>
                Disconnect
              </button>
            </div>
          </div>
          
          <main className="content-page">
            <Dashboard />
          </main>
        </>
      )}

      <footer>
        Lynceus System Control &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
};

export default App;