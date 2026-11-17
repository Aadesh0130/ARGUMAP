/**
 * useVoice — Dual-purpose voice hook for ARGUMAP
 *
 * Features:
 *  1. Speech-to-Text (STT) via the browser's Web Speech API
 *     → Streams recognized text back so it can be pasted into the
 *       transcript textarea on the Analyze page.
 *
 *  2. Text-to-Speech (TTS) via the backend /api/speak endpoint
 *     → Fetches an MP3 blob and plays it through an <audio> element.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { speakText } from '../lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────

export type TTSStatus = 'idle' | 'loading' | 'playing' | 'error';
export type STTStatus = 'idle' | 'listening' | 'error';

export interface UseVoiceReturn {
  // TTS
  ttsStatus: TTSStatus;
  ttsError: string | null;
  speak: (text: string, lang?: string) => Promise<void>;
  stopSpeaking: () => void;

  // STT
  sttStatus: STTStatus;
  sttError: string | null;
  sttSupported: boolean;
  startListening: (onResult: (transcript: string) => void) => void;
  stopListening: () => void;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useVoice(): UseVoiceReturn {
  // TTS state
  const [ttsStatus, setTtsStatus] = useState<TTSStatus>('idle');
  const [ttsError, setTtsError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  // STT state
  const [sttStatus, setSttStatus] = useState<STTStatus>('idle');
  const [sttError, setSttError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  // Check browser support for Web Speech API
  const sttSupported =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  // ── Cleanup on unmount ──────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  // ── TTS: speak ─────────────────────────────────────────────────────────
  const speak = useCallback(async (text: string, lang = 'en') => {
    // Stop any current playback
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }

    setTtsStatus('loading');
    setTtsError(null);

    try {
      const url = await speakText(text, lang);
      blobUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onplay = () => setTtsStatus('playing');
      audio.onended = () => setTtsStatus('idle');
      audio.onerror = () => {
        setTtsStatus('error');
        setTtsError('Audio playback failed.');
      };

      await audio.play();
    } catch (err: any) {
      setTtsStatus('error');
      setTtsError(err.message || 'TTS request failed.');
    }
  }, []);

  const stopSpeaking = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setTtsStatus('idle');
  }, []);

  // ── STT: listen ────────────────────────────────────────────────────────
  const startListening = useCallback((onResult: (transcript: string) => void) => {
    if (!sttSupported) {
      setSttError('Speech recognition is not supported in this browser. Try Chrome or Edge.');
      setSttStatus('error');
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      if (finalTranscript) onResult(finalTranscript);
    };

    recognition.onerror = (event: any) => {
      setSttError(`Microphone error: ${event.error}`);
      setSttStatus('error');
    };

    recognition.onend = () => {
      setSttStatus('idle');
    };

    recognitionRef.current = recognition;
    recognition.start();
    setSttStatus('listening');
    setSttError(null);
  }, [sttSupported]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setSttStatus('idle');
  }, []);

  return {
    ttsStatus,
    ttsError,
    speak,
    stopSpeaking,
    sttStatus,
    sttError,
    sttSupported,
    startListening,
    stopListening,
  };
}
