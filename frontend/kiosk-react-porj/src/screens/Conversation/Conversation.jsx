import Mascot from '../../components/Mascot/Mascot.jsx';
import Transcript from '../../components/Transcript/Transcript.jsx';
import StageLayout from '../../components/StageLayout/StageLayout.jsx';
import DoctorPanel from '../../components/DoctorPanel/DoctorPanel.jsx';
import './Conversation.css';

export default function Conversation({
  mascotState,
  transcriptLines,
  doctorList,
  onSelectDoctor,
  micActive,
  onToggleMic,
  awaitingConfirmation,
  onConfirm,
}) {
  // panelActive is DERIVED from doctorList presence, per spec — never a
  // separately managed flag, so there's no way for UI and data to drift apart.
  const panelActive = Boolean(doctorList && doctorList.length > 0);

  return (
    <div className="conversation">
      <StageLayout
        panelActive={panelActive}
        mascotSlot={<Mascot state={mascotState} />}
        transcriptSlot={<Transcript lines={transcriptLines} />}
        panelSlot={<DoctorPanel items={doctorList} onSelect={onSelectDoctor} />}
      />

      <div className="conversation__controls">
        <button
          type="button"
          className={`conversation__mic-button${micActive ? ' conversation__mic-button--active' : ''}`}
          onClick={onToggleMic}
        >
          {micActive ? 'Listening… tap to stop' : 'Tap to speak'}
        </button>

        {awaitingConfirmation && (
          <button type="button" className="conversation__confirm-button" onClick={onConfirm}>
            Confirm and get token
          </button>
        )}
      </div>
    </div>
  );
}