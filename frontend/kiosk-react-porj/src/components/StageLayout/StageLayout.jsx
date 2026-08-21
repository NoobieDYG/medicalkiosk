import './StageLayout.css';

// Owns the centered <-> split transition. panelActive is derived by the
// caller (Conversation) from doctorList presence — this component only
// reacts to the boolean, it never decides when to switch modes itself.
export default function StageLayout({ panelActive, mascotSlot, transcriptSlot, panelSlot }) {
  return (
    <div className={`stage-layout ${panelActive ? 'stage-layout--split' : 'stage-layout--centered'}`}>
      <div className="stage-layout__primary">
        {mascotSlot}
        {transcriptSlot}
      </div>

      <div className="stage-layout__panel">
        {panelActive && panelSlot}
      </div>
    </div>
  );
}