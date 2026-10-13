import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiFetch } from './doctorApi.js';
import { formatDateTime } from './format.js';
import OpdSlip from './OpdSlip.jsx';

const SECTIONS = [
  { key: 'diagnosis', label: 'Diagnosis', placeholder: 'Your diagnosis for this patient' },
  { key: 'follow_ups', label: 'Follow-ups', placeholder: 'e.g. X-ray chest, CBC, review in 5 days' },
  { key: 'prescription', label: 'Prescription', placeholder: 'Medicine, dose, frequency, duration' },
];

function draftsFrom(slip) {
  return {
    diagnosis: slip.diagnosis ?? '',
    follow_ups: slip.follow_ups ?? '',
    prescription: slip.prescription ?? '',
  };
}

export default function VisitPage() {
  const { visitId } = useParams();
  const [detail, setDetail] = useState(null);
  const [drafts, setDrafts] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [savingKey, setSavingKey] = useState(null);
  const [fieldError, setFieldError] = useState({ key: null, message: '' });
  const [completing, setCompleting] = useState(false);
  const [completeError, setCompleteError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setDetail(null);
    setDrafts(null);
    setLoadError('');

    apiFetch(`/doctor/visits/${visitId}`)
      .then((data) => {
        if (cancelled) return;
        setDetail(data);
        setDrafts(draftsFrom(data.slip));
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, [visitId]);

  if (loadError) {
    return (
      <div className="dr-page">
        <Link to="/dr" className="dr-back">← Back to tokens</Link>
        <p className="dr-error">{loadError}</p>
      </div>
    );
  }

  if (!detail || !drafts) {
    return <p className="dr-muted">Loading…</p>;
  }

  const { slip, patient } = detail;
  const completed = slip.status === 'completed';

  // A section is "dirty" when what's in the box differs from what the slip holds.
  const isDirty = (key) => {
    const saved = slip[key];
    if (saved === null) return true; // never saved: Save is allowed (even blank = "None")
    return drafts[key].trim() !== saved;
  };

  const handleSave = async (key) => {
    setSavingKey(key);
    setFieldError({ key: null, message: '' });
    try {
      const updatedSlip = await apiFetch(`/doctor/visits/${visitId}/slip`, {
        method: 'PATCH',
        body: { [key]: drafts[key] },
      });
      setDetail((prev) => ({ ...prev, slip: updatedSlip }));
      setDrafts((prev) => ({ ...prev, [key]: updatedSlip[key] ?? '' }));
    } catch (err) {
      setFieldError({ key, message: err.message });
    } finally {
      setSavingKey(null);
    }
  };

  const handleComplete = async () => {
    const hasUnsavedText = SECTIONS.some((s) =>
      slip[s.key] === null ? drafts[s.key].trim() !== '' : drafts[s.key].trim() !== slip[s.key]
    );
    const notFilled = SECTIONS.filter(
      (s) => slip[s.key] === null && drafts[s.key].trim() === ''
    ).map((s) => s.label);

    const lines = ['Mark this visit as complete? The slip becomes read-only.'];
    if (hasUnsavedText) lines.push('You have unsaved text that will be lost.');
    if (notFilled.length > 0) lines.push(`Not filled in yet: ${notFilled.join(', ')}.`);

    if (!window.confirm(lines.join('\n\n'))) return;

    setCompleting(true);
    setCompleteError('');
    try {
      const data = await apiFetch(`/doctor/visits/${visitId}/complete`, { method: 'POST' });
      setDetail(data);
      setDrafts(draftsFrom(data.slip));
    } catch (err) {
      setCompleteError(err.message);
    } finally {
      setCompleting(false);
    }
  };

  return (
    <div className="dr-visit">
      <Link to={completed ? '/dr/history' : '/dr'} className="dr-back">
        ← Back to {completed ? 'history' : 'tokens'}
      </Link>

      <div className="dr-visit-head">
        <h1 className="dr-page-title">
          Token #{slip.token_number} · {patient.name}
        </h1>
        {completed && <span className="dr-badge dr-badge--done">Completed</span>}
      </div>

      <div className="dr-visit-grid">
        <div className="dr-visit-left">
          <section className="dr-card">
            <h2 className="dr-card-title">Patient</h2>
            <dl className="dr-detail-list">
              <div><dt>Age</dt><dd>{patient.age ?? '—'}</dd></div>
              <div><dt>Gender</dt><dd>{patient.gender || '—'}</dd></div>
              <div><dt>Phone</dt><dd>{patient.phone || '—'}</dd></div>
              <div><dt>Department</dt><dd>{detail.department || '—'}</dd></div>
              {detail.icd_code && (
                <div><dt>ICD code</dt><dd>{detail.icd_code}</dd></div>
              )}
            </dl>

            {detail.symptom_summary && (
              <>
                <h3 className="dr-subtitle">Symptoms reported</h3>
                <p className="dr-prewrap">{detail.symptom_summary}</p>
              </>
            )}

            {detail.ai_impression && (
              <div className="dr-ai-box">
                <p className="dr-ai-label">AI summary — not a diagnosis</p>
                <p className="dr-prewrap">{detail.ai_impression}</p>
              </div>
            )}
          </section>

          {SECTIONS.map((section) => {
            const key = section.key;
            const dirty = isDirty(key);
            const saving = savingKey === key;

            let status = 'On the slip';
            if (slip[key] === null) status = 'Not on the slip yet';
            else if (dirty) status = 'Unsaved changes';

            let buttonLabel = 'Saved';
            if (saving) buttonLabel = 'Saving…';
            else if (slip[key] === null) buttonLabel = 'Save';
            else if (dirty) buttonLabel = 'Update';

            return (
              <section className="dr-card" key={key}>
                <label className="dr-card-title" htmlFor={`field-${key}`}>
                  {section.label}
                </label>
                <textarea
                  id={`field-${key}`}
                  className="dr-textarea"
                  rows={5}
                  maxLength={5000}
                  placeholder={section.placeholder}
                  value={drafts[key]}
                  disabled={completed || saving}
                  onChange={(e) => setDrafts((prev) => ({ ...prev, [key]: e.target.value }))}
                />
                <div className="dr-field-foot">
                  <span className="dr-muted">{completed ? 'On the slip' : status}</span>
                  {!completed && (
                    <button
                      type="button"
                      className="dr-btn dr-btn--primary"
                      disabled={saving || !dirty}
                      onClick={() => handleSave(key)}
                    >
                      {buttonLabel}
                    </button>
                  )}
                </div>
                {fieldError.key === key && <p className="dr-error">{fieldError.message}</p>}
              </section>
            );
          })}

          {!completed && (
            <div className="dr-complete">
              <button
                type="button"
                className="dr-btn dr-btn--secondary"
                disabled={completing || savingKey !== null}
                onClick={handleComplete}
              >
                {completing ? 'Completing…' : 'Complete visit'}
              </button>
              {completeError && <p className="dr-error">{completeError}</p>}
            </div>
          )}

          {completed && (
            <p className="dr-muted">
              This visit is complete, so the slip is read-only.
            </p>
          )}
        </div>

        <aside className="dr-visit-right">
          <OpdSlip slip={slip} />
        </aside>
      </div>
    </div>
  );
}