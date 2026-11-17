/**
 * VoiceBar — Floating voice control strip for the Results page.
 *
 * Provides two buttons:
 *  🔊 Speak Summary  — sends the full analysis summary to /api/speak and plays MP3
 *  🎤 Mic Input      — opens the browser's microphone and streams recognised text
 *                       back to the Analyze page (via navigate state)
 */

import React from 'react';
import { Mic, MicOff, Volume2, VolumeX, Loader2, Radio } from 'lucide-react';
import { TTSStatus, STTStatus } from '../hooks/useVoice';

interface VoiceBarProps {
  ttsStatus: TTSStatus;
  sttStatus: STTStatus;
  ttsError: string | null;
  sttError: string | null;
  sttSupported: boolean;
  onSpeak: () => void;
  onStopSpeaking: () => void;
  onStartListening: () => void;
  onStopListening: () => void;
  summaryText: string;
}

const ttsLabel: Record<TTSStatus, string> = {
  idle: 'Speak Summary',
  loading: 'Generating audio…',
  playing: 'Stop Audio',
  error: 'Retry Audio',
};

const sttLabel: Record<STTStatus, string> = {
  idle: 'Mic Input',
  listening: 'Stop Listening',
  error: 'Retry Mic',
};

export const VoiceBar: React.FC<VoiceBarProps> = ({
  ttsStatus,
  sttStatus,
  ttsError,
  sttError,
  sttSupported,
  onSpeak,
  onStopSpeaking,
  onStartListening,
  onStopListening,
  summaryText,
}) => {
  const handleTTS = () => {
    if (ttsStatus === 'playing') onStopSpeaking();
    else onSpeak();
  };

  const handleSTT = () => {
    if (sttStatus === 'listening') onStopListening();
    else onStartListening();
  };

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-4 rounded-xl bg-slate-900/80 border border-indigo-800/40 backdrop-blur">
      {/* Header label */}
      <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-400 shrink-0">
        <Radio className="w-3.5 h-3.5" />
        Voice System
      </div>

      <div className="flex flex-wrap items-center gap-2 flex-1">
        {/* ── TTS Button ───────────────────────────────── */}
        <button
          onClick={handleTTS}
          disabled={ttsStatus === 'loading' || !summaryText}
          title={summaryText ? 'Listen to the analysis summary' : 'No summary available'}
          className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border
            ${ttsStatus === 'playing'
              ? 'bg-rose-950/60 border-rose-700/60 text-rose-300 hover:bg-rose-900/60'
              : ttsStatus === 'error'
              ? 'bg-amber-950/60 border-amber-700/60 text-amber-300 hover:bg-amber-900/60'
              : 'bg-indigo-950/60 border-indigo-700/60 text-indigo-200 hover:bg-indigo-900/60'}
            disabled:opacity-40 disabled:cursor-not-allowed`}
        >
          {ttsStatus === 'loading' ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : ttsStatus === 'playing' ? (
            <VolumeX className="w-3.5 h-3.5" />
          ) : (
            <Volume2 className="w-3.5 h-3.5" />
          )}
          {ttsLabel[ttsStatus]}
        </button>

        {/* ── STT Button ───────────────────────────────── */}
        <button
          onClick={handleSTT}
          disabled={!sttSupported}
          title={
            sttSupported
              ? 'Dictate a transcript using your microphone'
              : 'Speech recognition not supported — use Chrome or Edge'
          }
          className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border
            ${sttStatus === 'listening'
              ? 'bg-emerald-950/60 border-emerald-600/60 text-emerald-300 hover:bg-emerald-900/60 animate-pulse'
              : sttStatus === 'error'
              ? 'bg-amber-950/60 border-amber-700/60 text-amber-300 hover:bg-amber-900/60'
              : 'bg-slate-800/60 border-slate-700/60 text-slate-300 hover:bg-slate-700/60'}
            disabled:opacity-40 disabled:cursor-not-allowed`}
        >
          {sttStatus === 'listening' ? (
            <MicOff className="w-3.5 h-3.5" />
          ) : (
            <Mic className="w-3.5 h-3.5" />
          )}
          {sttLabel[sttStatus]}
        </button>

        {/* ── Error messages ────────────────────────────── */}
        {(ttsError || sttError) && (
          <span className="text-[11px] text-amber-400 font-mono">
            ⚠ {ttsError || sttError}
          </span>
        )}

        {sttStatus === 'listening' && (
          <span className="text-[11px] text-emerald-400 font-mono animate-pulse">
            🎤 Listening… speak your transcript
          </span>
        )}

        {!sttSupported && (
          <span className="text-[11px] text-slate-500">
            (Mic requires Chrome / Edge)
          </span>
        )}
      </div>
    </div>
  );
};
