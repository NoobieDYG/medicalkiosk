import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiFetch } from './doctorApi.js';
import OpdSlip from './OpdSlip.jsx';
import './slipPage.css';

const POLL_MS = 5000;

export default function SlipPage() {
  const { slipId } = useParams();
  const [slip, setSlip] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [retryNote, setRetryNote] = useState('');

  useEffect(() => {
    let cancelled = false;
    let finished = false;
    let timer = null;

    const stop = () => {
      finished = true;
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };

    const load = async () => {
      if (finished) return;
      try {
        const data = await apiFetch(`/slip/${encodeURIComponent(slipId)}`, { auth: false });
        if (cancelled) return;
        setSlip(data);
        setRetryNote('');
        if (data.status === 'completed') stop();
      } catch (err) {
        if (cancelled) return;
        if (err.status === 404) {
          setNotFound(true);
          stop();
        } else {
          setRetryNote('Could not refresh. Trying again…');
        }
      }
    };

    const onVisibilityChange = () => {
      if (!document.hidden) load();
    };

    load();
    timer = setInterval(() => {
      if (!document.hidden) load();
    }, POLL_MS);
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      cancelled = true;
      stop();
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [slipId]);

  if (notFound) {
    return (
      <div className="slip-page">
        <p className="slip-page__message">This slip link isn't valid. Please check the link or ask at the desk.</p>
      </div>
    );
  }

  if (!slip) {
    return (
      <div className="slip-page">
        <p className="slip-page__message">{retryNote || 'Loading your slip…'}</p>
      </div>
    );
  }

  return (
    <div className="slip-page">
      <div className="slip-page__inner">
        <OpdSlip slip={slip} />

        <p className="slip-page__status">
          {slip.status === 'completed'
            ? 'Your visit is complete.'
            : 'This slip updates automatically as your doctor adds notes.'}
        </p>
        {retryNote && <p className="slip-page__error">{retryNote}</p>}

        <button type="button" className="slip-page__print" onClick={() => window.print()}>
          Save as PDF / Print
        </button>
      </div>
    </div>
  );
}