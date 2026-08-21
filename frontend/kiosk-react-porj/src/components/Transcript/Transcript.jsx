import { useEffect, useRef } from 'react';
import './Transcript.css';

// Renders assistant_text lines only — patient speech is never shown,
// per the spec. Auto-scrolls to the latest line as new ones arrive.
export default function Transcript({ lines }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [lines]);

  if (lines.length === 0) {
    return null; // nothing spoken yet — avoid an empty box taking up space
  }

  return (
    <div className="transcript">
      {lines.map((line, i) => (
        <p
          key={i}
          className={`transcript__line ${i === lines.length - 1 ? 'transcript__line--latest' : ''}`}
        >
          {line}
        </p>
      ))}
      <div ref={endRef} />
    </div>
  );
}