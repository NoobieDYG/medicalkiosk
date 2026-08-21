// Simple named states for the top-level screen. Kept as plain constants
// rather than a full state-machine library — three states, one direction
// of travel (welcome -> conversation -> token -> back to welcome),
// doesn't need more than that yet.

export const SCREEN = {
  WELCOME: 'welcome',
  CONVERSATION: 'conversation',
  TOKEN: 'token',
};

// Centralizes the transition rules so AssistantShell doesn't scatter
// "which screen comes next" logic across event handlers.
export function nextScreen(current, event) {
  switch (current) {
    case SCREEN.WELCOME:
      if (event === 'start') return SCREEN.CONVERSATION;
      return current;
    case SCREEN.CONVERSATION:
      if (event === 'token_issued') return SCREEN.TOKEN;
      return current;
    case SCREEN.TOKEN:
      if (event === 'reset') return SCREEN.WELCOME;
      return current;
    default:
      return current;
  }
}