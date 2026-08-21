// Thin wrapper around the native WebSocket API. Centralizes connection
// lifecycle, JSON (text) vs binary framing, and reconnect-free lifecycle
// so hooks/components don't touch `new WebSocket` directly.

export default class TriageSocket {
  constructor({ onOpen, onTextMessage, onBinaryMessage, onClose, onError } = {}) {
    this.socket = null;
    this.onOpen = onOpen;
    this.onTextMessage = onTextMessage;
    this.onBinaryMessage = onBinaryMessage;
    this.onClose = onClose;
    this.onError = onError;
  }

  connect(url) {
    if (this.socket) return;

    const socket = new WebSocket(url);
    socket.binaryType = 'arraybuffer';
    this.socket = socket;

    socket.onopen = () => {
      this.onOpen?.();
    };

    socket.onmessage = (event) => {
      if (typeof event.data === 'string') {
        let message;
        try {
          message = JSON.parse(event.data);
        } catch {
          return; // ignore malformed frames rather than crash the session
        }
        this.onTextMessage?.(message);
      } else {
        this.onBinaryMessage?.(event.data); // ArrayBuffer
      }
    };

    socket.onclose = () => {
      this.socket = null;
      this.onClose?.();
    };

    socket.onerror = (err) => {
      this.onError?.(err);
    };
  }

  disconnect() {
    this.socket?.close();
    this.socket = null;
  }

  isConnected() {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  send(obj) {
    if (!this.isConnected()) return;
    this.socket.send(JSON.stringify(obj));
  }

  sendBinary(arrayBufferOrBlob) {
    if (!this.isConnected()) return;
    this.socket.send(arrayBufferOrBlob);
  }
}