// Mic capture with simple volume-based VAD, and a sequential playback
// queue for TTS audio chunks arriving as binary WS frames.
//
// VAD approach: analyse mic input volume via AnalyserNode. While volume
// stays below SILENCE_THRESHOLD for SILENCE_DURATION_MS, treat the
// utterance as finished and flush the recorded chunk.

const SILENCE_THRESHOLD = 0.02; // 0-1 scale, tune per mic/environment
const SILENCE_DURATION_MS = 1200;
const CHECK_INTERVAL_MS = 100;

export class MicRecorder {
  constructor({ onSpeechStart, onSpeechEnd } = {}) {
    this.onSpeechStart = onSpeechStart;
    this.onSpeechEnd = onSpeechEnd; // called with a Blob of recorded audio
    this.mediaStream = null;
    this.mediaRecorder = null;
    this.audioContext = null;
    this.analyser = null;
    this.silenceTimer = null;
    this.vadInterval = null;
    this.chunks = [];
    this.speaking = false;
  }

  async start() {
    this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 512;
    source.connect(this.analyser);

    this.mediaRecorder = new MediaRecorder(this.mediaStream, {
      mimeType: 'audio/webm;codecs=opus',
    });
    this.chunks = [];

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) this.chunks.push(event.data);
    };

    this.mediaRecorder.onstop = () => {
      const blob = new Blob(this.chunks, { type: 'audio/webm;codecs=opus' });
      this.chunks = [];
      this.onSpeechEnd?.(blob);
    };

    this.mediaRecorder.start();
    this._runVad();
  }

  _runVad() {
    const buffer = new Uint8Array(this.analyser.frequencyBinCount);

    this.vadInterval = setInterval(() => {
      this.analyser.getByteTimeDomainData(buffer);

      // RMS volume of the waveform, normalized to 0-1
      let sumSquares = 0;
      for (let i = 0; i < buffer.length; i += 1) {
        const normalized = (buffer[i] - 128) / 128;
        sumSquares += normalized * normalized;
      }
      const rms = Math.sqrt(sumSquares / buffer.length);

      if (rms > SILENCE_THRESHOLD) {
        if (!this.speaking) {
          this.speaking = true;
          this.onSpeechStart?.();
        }
        if (this.silenceTimer) {
          clearTimeout(this.silenceTimer);
          this.silenceTimer = null;
        }
      } else if (this.speaking && !this.silenceTimer) {
        this.silenceTimer = setTimeout(() => {
          this.speaking = false;
          this._flush();
        }, SILENCE_DURATION_MS);
      }
    }, CHECK_INTERVAL_MS);
  }

  _flush() {
    // Restart the recorder so the next utterance starts a fresh blob,
    // while the current one gets delivered via onstop above.
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop();
      this.mediaRecorder.start();
    }
  }

  stop() {
    if (this.vadInterval) clearInterval(this.vadInterval);
    if (this.silenceTimer) clearTimeout(this.silenceTimer);
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    this.mediaStream?.getTracks().forEach((track) => track.stop());
    this.audioContext?.close();

    this.mediaStream = null;
    this.mediaRecorder = null;
    this.audioContext = null;
    this.analyser = null;
    this.speaking = false;
  }
}

// Sequential playback queue for TTS audio chunks (ArrayBuffers) arriving
// over the WS. Decodes and plays one at a time so chunks don't overlap.
export class TtsPlayer {
  constructor() {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    this.queue = [];
    this.playing = false;
  }

  enqueue(arrayBuffer) {
    this.queue.push(arrayBuffer);
    if (!this.playing) this._playNext();
  }

  async _playNext() {
    const next = this.queue.shift();
    if (!next) {
      this.playing = false;
      return;
    }
    this.playing = true;

    try {
      const audioBuffer = await this.audioContext.decodeAudioData(next.slice(0));
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);
      source.onended = () => this._playNext();
      source.start();
    } catch {
      this._playNext(); // skip a bad chunk rather than stall the queue
    }
  }

  clear() {
    this.queue = [];
  }
}