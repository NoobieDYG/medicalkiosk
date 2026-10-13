import { useState, useCallback } from 'react';
import { SCREEN, nextScreen } from '../../state/sessionMachine.js';
import useVoiceSession from '../../hooks/useVoiceSession.js';
import Welcome from '../../screens/Welcome/Welcome.jsx';
import Conversation from '../../screens/Conversation/Conversation.jsx';
import TokenDisplay from '../../screens/TokenDisplay/TokenDisplay.jsx';

const HOSPITAL_ID = 1;
const KIOSK_ID = 1;

// The address a patient's phone can reach the frontend at (used inside the QR code).
const PUBLIC_BASE_URL = (import.meta.env.VITE_PUBLIC_BASE_URL || window.location.origin).replace(/\/$/, '');

export default function AssistantShell() {
  const [screen, setScreen] = useState(SCREEN.WELCOME);
  const [token, setToken] = useState(null);

  const handleTokenIssued = useCallback((issuedToken) => {
    setToken(issuedToken);
    setScreen((current) => nextScreen(current, 'token_issued'));
  }, []);

  const voiceSession = useVoiceSession({
    hospitalId: HOSPITAL_ID,
    kioskId: KIOSK_ID,
    onTokenIssued: handleTokenIssued,
  });

  const handleStart = useCallback(() => {
    voiceSession.connect();
    setScreen((current) => nextScreen(current, 'start'));
  }, [voiceSession]);

  const handleReset = useCallback(() => {
    voiceSession.disconnect();
    setToken(null);
    setScreen((current) => nextScreen(current, 'reset'));
  }, [voiceSession]);

  const handleToggleMic = useCallback(async () => {
    if (voiceSession.micActive) {
      voiceSession.stopListening();
      return;
    }
    try {
      await voiceSession.startListening();
    } catch (err) {
      // Most likely mic permission denied or no mic present.
      console.error('Could not start microphone:', err);
    }
  }, [voiceSession]);

  if (screen === SCREEN.WELCOME) {
    return <Welcome onStart={handleStart} />;
  }

  if (screen === SCREEN.CONVERSATION) {
    return (
      <Conversation
        mascotState={voiceSession.mascotState}
        transcriptLines={voiceSession.transcriptLines}
        doctorList={voiceSession.doctorList}
        onSelectDoctor={voiceSession.sendSelection}
        micActive={voiceSession.micActive}
        onToggleMic={handleToggleMic}
        awaitingConfirmation={voiceSession.awaitingConfirmation}
        onConfirm={voiceSession.confirmEnd}
      />
    );
  }

  if (screen === SCREEN.TOKEN) {
    const slipUrl = token?.slip_id ? `${PUBLIC_BASE_URL}/s/${token.slip_id}` : null;
    return (
      <TokenDisplay
        token={token?.token_number ?? token}
        slipUrl={slipUrl}
        onReset={handleReset}
      />
    );
  }

  return null;
}