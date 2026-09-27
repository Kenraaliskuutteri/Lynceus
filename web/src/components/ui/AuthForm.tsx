import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';

export const AuthForm: React.FC = () => {
  const { login, host: storedHost } = useAuth();
  const [hostAddress, setHostAddress] = useState<string>(storedHost);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!hostAddress.trim()) {
      setErrorMessage('Endpoint URL required.');
      return;
    }
    if (!username.trim() || !password) {
      setErrorMessage('Username and password required.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(hostAddress, username.trim(), password);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Login failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="homepage-panels">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-kicker">Authentication Required</span>
          <h2>Sign In</h2>
        </div>
        <p>Specify daemon endpoint and account credentials to establish session.</p>

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
            <label>Username</label>
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              autoComplete="current-password"
              placeholder="••••••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="download-button" style={{ marginTop: '12px' }} disabled={isSubmitting}>
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};