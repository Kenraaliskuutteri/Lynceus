    // src/components/AuthForm.tsx
import React, { useState } from 'react';

interface AuthFormProps {
  onConnect: (host: string, key: string) => void;
}

export const AuthForm: React.FC<AuthFormProps> = ({ onConnect }) => {
  const [hostAddress, setHostAddress] = useState<string>(
    localStorage.getItem('lynceus_host') || ''
  );
  const [secretKey, setSecretKey] = useState<string>(
    localStorage.getItem('lynceus_key') || ''
  );
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!hostAddress.trim()) {
      setErrorMessage('Endpoint URL required.');
      return;
    }

    if (!secretKey.trim()) {
      setErrorMessage('Master API Key required.');
      return;
    }

    onConnect(hostAddress, secretKey);
  };

  return (
    <div className="homepage-panels">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-kicker">Authentication Required</span>
          <h2>Connect Instance</h2>
        </div>
        <p>Specify daemon endpoint and secret key to establish session.</p>

        {errorMessage && <div className="error-alert">{errorMessage}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Host Endpoint</label>
            <input
              type="text"
              placeholder="http://127.0.0.1:8000"
              value={hostAddress}
              onChange={(e) => setHostAddress(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Master API Key</label>
            <input
              type="password"
              placeholder="••••••••••••••••"
              value={secretKey}
              onChange={(e) => setSecretKey(e.target.value)}
            />
          </div>

          <button type="submit" className="download-button" style={{ marginTop: '12px' }}>
            Connect Panel
          </button>
        </form>
      </div>
    </div>
  );
};