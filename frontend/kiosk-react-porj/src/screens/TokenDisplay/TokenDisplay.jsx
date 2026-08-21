import './TokenDisplay.css';

export default function TokenDisplay({ token, onReset }) {
  return (
    <div className="token-display">
      <div className="token-display__content">
        <p className="token-display__label">Your token number</p>
        <p className="token-display__number">{token}</p>
        <p className="token-display__hint">Please have a seat — we'll call your number shortly.</p>

        <button className="token-display__reset-button" onClick={onReset}>
          Done
        </button>
      </div>
    </div>
  );
}