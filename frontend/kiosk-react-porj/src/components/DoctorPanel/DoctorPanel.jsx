import DoctorCard from './DoctorCard.jsx';
import './DoctorPanel.css';

export default function DoctorPanel({ items, onSelect }) {
  if (!items || items.length === 0) {
    return (
      <div className="doctor-panel doctor-panel--empty">
        <p>No matching doctors found right now.</p>
      </div>
    );
  }

  return (
    <div className="doctor-panel">
      <h2 className="doctor-panel__heading">Recommended doctors</h2>
      <p className="doctor-panel__hint">Tap a card, or say the number.</p>

      <div className="doctor-panel__list">
        {items.map((doctor, i) => (
          <DoctorCard
            key={doctor.id}
            doctor={doctor}
            index={i + 1}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}