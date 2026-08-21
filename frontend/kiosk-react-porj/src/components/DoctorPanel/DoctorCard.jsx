import './DoctorPanel.css';

export default function DoctorCard({ doctor, index, onSelect }) {
  const { name, specialty, available, next_slot } = doctor;

  return (
    <button
      className="doctor-card"
      onClick={() => onSelect(doctor.id)}
      aria-label={`Select doctor ${index}: ${name}, ${specialty}`}
    >
      <div className="doctor-card__index">{index}</div>

      <div className="doctor-card__info">
        <h3 className="doctor-card__name">{name}</h3>
        <p className="doctor-card__specialty">{specialty}</p>
      </div>

      <div className={`doctor-card__badge ${available ? 'doctor-card__badge--available' : 'doctor-card__badge--unavailable'}`}>
        {available ? `Available · ${next_slot}` : 'Unavailable'}
      </div>
    </button>
  );
}