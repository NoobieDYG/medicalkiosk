import './Mascot.css';
import { resolveMascotState, mascotAriaLabel } from './mascotStates.js';

// 12 radial bars form the "voice ring" — as a circle in idle/listening/
// processing, morphing into a waveform when talking. Generated rather
// than hand-written so the count is easy to tune from one place.
const WAVEFORM_BAR_COUNT = 12;
const waveformBars = Array.from({ length: WAVEFORM_BAR_COUNT }, (_, i) => i);

export default function Mascot({ state = 'idle' }) {
  const activeState = resolveMascotState(state);

  return (
    <div
      className={`mascot mascot--${activeState}`}
      role="img"
      aria-label={mascotAriaLabel(activeState)}
    >
      <svg viewBox="0 0 200 200" className="mascot__svg" aria-hidden="true">
        {/* Voice ring — solid ring in idle/listening/processing */}
        <circle className="mascot__ring" cx="100" cy="100" r="84" fill="none" strokeWidth="4" />

        {/* Voice ring — waveform bars, only visible while talking */}
        <g className="mascot__waveform">
          {waveformBars.map((i) => (
            <g key={i} transform={`rotate(${i * (360 / WAVEFORM_BAR_COUNT)} 100 100)`}>
              <rect
                className="mascot__bar"
                x="97"
                y="4"
                width="6"
                height="14"
                rx="3"
                style={{ animationDelay: `${(i % 4) * 100}ms` }}
              />
            </g>
          ))}
        </g>

        {/* Face */}
        <g className="mascot__face">
          <circle className="mascot__body" cx="100" cy="100" r="60" />
          <circle className="mascot__eye mascot__eye--left" cx="82" cy="94" r="6" />
          <circle className="mascot__eye mascot__eye--right" cx="118" cy="94" r="6" />
          <ellipse className="mascot__mouth" cx="100" cy="120" rx="14" ry="4" />
        </g>
      </svg>
    </div>
  );
}