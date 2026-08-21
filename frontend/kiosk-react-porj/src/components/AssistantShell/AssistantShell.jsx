import { useState, useCallback } from 'react';
import { SCREEN, nextScreen } from '../../state/sessionMachine.js';
import useVoiceSession from '../../hooks/useVoiceSession.js';
import Welcome from '../../screens/Welcome/Welcome.jsx';
import Conversation from '../../screens/Conversation/Conversation.jsx';
import TokenDisplay from '../../screens/TokenDisplay/TokenDisplay.jsx';

const HOSPITAL_ID = 1;
const KIOSK_ID = 1;

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
    return <TokenDisplay token={token} onReset={handleReset} />;
  }

  return null;
}