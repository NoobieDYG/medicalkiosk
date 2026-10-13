import { formatSlipDate } from './format.js';
import './slip.css';

function Field({ label, value }) {
  return (
    <div className="opd-slip-field">
      <dt>{label}</dt>
      <dd>{value || '—'}</dd>
    </div>
  );
}

function Section({ title, value }) {
  let content;
  if (value === null || value === undefined) {
    content = <p className="opd-slip-awaiting">Awaiting doctor</p>;
  } else if (value === '') {
    content = <p className="opd-slip-body">None</p>;
  } else {
    content = <p className="opd-slip-body">{value}</p>;
  }

  return (
    <section className="opd-slip-section">
      <h3>{title}</h3>
      {content}
    </section>
  );
}

export default function OpdSlip({ slip }) {
  const { clinic, patient, doctor } = slip;

  const ageGender = [patient.age != null ? `${patient.age} yrs` : null, patient.gender]
    .filter(Boolean)
    .join(' / ');

  return (
    <article className="opd-slip">
      <header className="opd-slip-header">
        <h2 className="opd-slip-clinic">{clinic.name}</h2>
        {clinic.address && <p className="opd-slip-contact">{clinic.address}</p>}
        {clinic.phone && <p className="opd-slip-contact">{clinic.phone}</p>}
      </header>

      <p className="opd-slip-title">OPD Slip</p>

      <dl className="opd-slip-grid">
        <Field label="Token" value={slip.token_number != null ? `#${slip.token_number}` : ''} />
        <Field label="Date" value={formatSlipDate(slip.issued_at)} />
        <Field label="Patient" value={patient.name} />
        <Field label="Age / Gender" value={ageGender} />
        <Field label="Doctor" value={doctor.name} />
        <Field label="Department" value={doctor.department} />
      </dl>

      <Section title="Diagnosis" value={slip.diagnosis} />
      <Section title="Follow-ups" value={slip.follow_ups} />
      <Section title="Prescription" value={slip.prescription} />

      {slip.status === 'completed' && (
        <footer className="opd-slip-footer">Visit completed</footer>
      )}
    </article>
  );
}