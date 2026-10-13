import { QRCodeSVG } from 'qrcode.react';
import './TokenDisplay.css';

export default function TokenDisplay({ token, slipUrl, onReset }) {
  return (
    <div className="token-display">
      <div className="token-display__content">
        <p className="token-display__label">Your token number</p>
        <p className="token-display__number">{token}</p>
        <p className="token-display__hint">Please have a seat — we'll call your number shortly.</p>

        {slipUrl && (
          <div className="token-display__slip">
            <QRCodeSVG value={slipUrl} size={160} />
            <p className="token-display__slip-hint">
              Scan to open your OPD slip on your phone. Your doctor's notes will appear on it.
            </p>
          </div>
        )}

        <button className="token-display__reset-button" onClick={onReset}>
          Done
        </button>
      </div>
    </div>
  );
}