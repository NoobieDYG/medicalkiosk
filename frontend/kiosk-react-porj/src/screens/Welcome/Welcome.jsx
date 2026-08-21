import './Welcome.css';
export default function Welcome({ onStart }) {
  return (
    <div className="welcome">
      <div className="welcome__content">
        <h1 className="welcome__headline">Hi, I'm here to help.</h1>
        <p className="welcome__subline">Tap below and tell me what's bothering you today.</p>
        <button className="welcome__start-button" onClick={onStart}>
          Tap to start
        </button>
      </div>
    </div>
  );
}