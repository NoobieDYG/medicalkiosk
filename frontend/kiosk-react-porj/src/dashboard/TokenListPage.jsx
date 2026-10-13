import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from './doctorApi.js';
import { formatDateTime, formatTime } from './format.js';

const COPY = {
  current: {
    title: 'Current tokens',
    empty: 'No patients waiting right now.',
  },
  past: {
    title: 'History',
    empty: 'No completed visits yet.',
  },
};

export default function TokenListPage({ scope }) {
  const navigate = useNavigate();
  const [tokens, setTokens] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setTokens(null);
    setError('');

    const load = () =>
      apiFetch(`/doctor/tokens?scope=${scope}`)
        .then((data) => {
          if (cancelled) return;
          setTokens(data);
          setError('');
        })
        .catch((err) => {
          if (!cancelled) setError(err.message);
        });

    load();
    if (scope !== 'current') {
      return () => {
        cancelled = true;
      };
    }
    const timer = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [scope]);

  const copy = COPY[scope];

  const describe = (token) => {
    const parts = [];
    if (token.age != null) parts.push(`${token.age} yrs`);
    if (token.gender) parts.push(token.gender);
    if (token.department) parts.push(token.department);
    return parts.join(' · ');
  };

  return (
    <div className="dr-page">
      <h1 className="dr-page-title">{copy.title}</h1>

      {error && <p className="dr-error">{error}</p>}
      {tokens === null && !error && <p className="dr-muted">Loading…</p>}
      {tokens !== null && tokens.length === 0 && <p className="dr-muted">{copy.empty}</p>}

      {tokens !== null && tokens.length > 0 && (
        <ul className="dr-token-list">
          {tokens.map((token) => (
            <li key={token.visit_id}>
              <button
                type="button"
                className="dr-token-card"
                onClick={() => navigate(`/dr/visit/${token.visit_id}`)}
              >
                <span className="dr-token-number">#{token.token_number}</span>
                <span className="dr-token-main">
                  <span className="dr-token-name">{token.patient_name}</span>
                  <span className="dr-token-meta">{describe(token)}</span>
                </span>
                <span className="dr-token-time">
                  {scope === 'past'
                    ? `Completed ${formatDateTime(token.completed_at)}`
                    : `Checked in ${formatTime(token.created_at)}`}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}