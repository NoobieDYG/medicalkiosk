// Central definition of valid mascot states + accessibility labels.
// Anything rendering <Mascot> should only ever pass one of these.

export const MASCOT_STATES = ['idle', 'listening', 'processing', 'talking'];

const ARIA_LABELS = {
  idle: 'Assistant is ready',
  listening: 'Assistant is listening',
  processing: 'Assistant is thinking',
  talking: 'Assistant is speaking',
};

export function resolveMascotState(state) {
  return MASCOT_STATES.includes(state) ? state : 'idle';
}

export function mascotAriaLabel(state) {
  return ARIA_LABELS[resolveMascotState(state)];
}