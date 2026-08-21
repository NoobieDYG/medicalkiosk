import { useState, useRef, useCallback } from 'react';
import TriageSocket from '../lib/websocket';
import { MicRecorder, TtsPlayer } from '../lib/audio';

const WS_URL_BASE = 'ws://localhost:8000/ws/kiosk'; // adjust per environment

export default function useVoiceSession({ hospitalId, kioskId, onTokenIssued }) {
  const [mascotState, setMascotState] = useState('idle'); // idle | listening | processing | talking
  const [transcriptLines, setTranscriptLines] = useState([]);
  const [doctorList, setDoctorList] = useState(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [micActive, setMicActive] = useState(false);

  const socketRef = useRef(null);
  const micRef = useRef(null);
  const ttsRef = useRef(null);

  const connect = useCallback(() => {
    const socket = new TriageSocket({
      onOpen: () => setMascotState('idle'),
      onTextMessage: (message) => {
        switch (message.type) {
          case 'assistant_text':
            setMascotState('talking');
            setTranscriptLines((lines) => [...lines, message.text]);
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
            setAwaitingConfirmation(false);
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
  }, [hospitalId, kioskId, onTokenIssued]);

  const disconnect = useCallback(() => {
    micRef.current?.stop();
    micRef.current = null;
    setMicActive(false);
    setAwaitingConfirmation(false);
    socketRef.current?.disconnect();
    socketRef.current = null;
  }, []);

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
    micRef.current?.stop();
    micRef.current = null;
    setMicActive(false);
    setMascotState('idle');
  }, []);

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