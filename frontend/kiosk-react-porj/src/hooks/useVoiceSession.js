import { useState, useRef, useCallback } from 'react';
import TriageSocket from '../lib/websocket';
import { MicRecorder, TtsPlayer } from '../lib/audio';

const WS_URL_BASE = 'ws://localhost:8000/ws/kiosk'; // hospital and kiosk IDs are appended at connection time
const READY_TO_FINALIZE_STAGE = 'ready_to_finalize';

export default function useVoiceSession({ hospitalId, kioskId, onTokenIssued }) {
  const [mascotState, setMascotState] = useState('idle'); // idle | listening | processing | talking
  const [transcriptLines, setTranscriptLines] = useState([]);
  const [doctorList, setDoctorList] = useState(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [micActive, setMicActive] = useState(false);

  const socketRef = useRef(null);
  const micRef = useRef(null);
  const ttsRef = useRef(null);

  const stopMic = useCallback(() => {
    micRef.current?.stop();
    micRef.current = null;
    setMicActive(false);
  }, []);

  const connect = useCallback(() => {
    const socket = new TriageSocket({
      onOpen: () => setMascotState('idle'),
      onTextMessage: (message) => {
        switch (message.type) {
          case 'assistant_text':
            setMascotState('talking');
            setTranscriptLines((lines) => [...lines, message.text]);
            // Stage is authoritative and rides on every assistant_text message,
            // so derive confirmation state from it instead of trusting a single
            // event type. This self-corrects if the patient branches away from
            // finalize (e.g. "change doctor") after being asked to confirm.
            setAwaitingConfirmation(message.stage === READY_TO_FINALIZE_STAGE);
            break;
          case 'structured_data':
            if (message.kind === 'doctor_list') {
              setDoctorList(message.items);
            }
            break;
          case 'awaiting_confirmation':
            setAwaitingConfirmation(true);
            break;
          case 'token_issued':
            // Session is finalized and the backend is closing the connection.
            // Stop the mic so it doesn't try to send onto a dead socket, and
            // clear any leftover doctor list / confirmation UI.
            stopMic();
            setDoctorList(null);
            setAwaitingConfirmation(false);
            setMascotState('idle');
            onTokenIssued?.(message.token);
            break;
          case 'error':
            setTranscriptLines((lines) => [...lines, `⚠ ${message.detail}`]);
            setMascotState('idle');
            break;
          default:
            break;
        }
      },
      onBinaryMessage: (arrayBuffer) => {
        setMascotState('talking');
        ttsRef.current?.enqueue(arrayBuffer);
      },
      onClose: () => {
        socketRef.current = null;
      },
      onError: () => {
        setTranscriptLines((lines) => [...lines, '⚠ Connection lost. Please restart.']);
      },
    });

    const url = `${WS_URL_BASE}/${hospitalId}/${kioskId}`;
    socket.connect(url);
    socketRef.current = socket;
    ttsRef.current = new TtsPlayer();
  }, [hospitalId, kioskId, onTokenIssued, stopMic]);

  const disconnect = useCallback(() => {
    stopMic();
    setAwaitingConfirmation(false);
    socketRef.current?.disconnect();
    socketRef.current = null;
  }, [stopMic]);

  const startListening = useCallback(async () => {
    if (!socketRef.current || micRef.current) return;

    const mic = new MicRecorder({
      onSpeechStart: () => setMascotState('listening'),
      onSpeechEnd: (blob) => {
        setMascotState('processing');
        blob.arrayBuffer().then((buf) => socketRef.current?.sendBinary(buf));
      },
    });

    await mic.start();
    micRef.current = mic;
    setMicActive(true);
  }, []);

  const stopListening = useCallback(() => {
    stopMic();
    setMascotState('idle');
  }, [stopMic]);

  const sendMessage = useCallback((text) => {
    socketRef.current?.send({ type: 'message', text });
    setTranscriptLines((lines) => [...lines, text]);
    setMascotState('processing');
  }, []);

  const sendSelection = useCallback((doctorId) => {
    socketRef.current?.send({ type: 'selection', kind: 'doctor', id: doctorId });
    setDoctorList(null);
  }, []);

  const confirmEnd = useCallback(() => {
    socketRef.current?.send({ type: 'end' });
  }, []);

  return {
    mascotState,
    transcriptLines,
    doctorList,
    awaitingConfirmation,
    micActive,
    connect,
    disconnect,
    startListening,
    stopListening,
    sendMessage,
    sendSelection,
    confirmEnd,
  };
}