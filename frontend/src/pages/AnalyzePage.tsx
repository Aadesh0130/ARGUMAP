import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  FileText,
  Upload,
  Sparkles,
  Info,
  RotateCcw,
  CheckCircle,
  FileCode,
  AlertCircle,
  Mic,
  MicOff,
} from 'lucide-react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { useVoice } from '../hooks/useVoice';
import { SAMPLE_TRANSCRIPT } from '../lib/mockData';

export const AnalyzePage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Pre-fill from mic dictation on Results page
  const prefill = (location.state as any)?.prefill || '';

  const [transcript, setTranscript] = useState(prefill || SAMPLE_TRANSCRIPT);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileNotice, setFileNotice] = useState<string | null>(
    prefill ? '🎤 Transcript filled from microphone dictation.' : null
  );

  // Clear location state so a refresh doesn't re-prefill
  useEffect(() => {
    if (prefill) window.history.replaceState({}, '');
  }, [prefill]);

  const wordCount = transcript.trim() ? transcript.trim().split(/\s+/).length : 0;
  const charCount = transcript.length;

  // ── Voice (mic) ────────────────────────────────────────────────────────
  const { sttStatus, sttError, sttSupported, startListening, stopListening } = useVoice();

  const handleMicToggle = () => {
    if (sttStatus === 'listening') {
      stopListening();
    } else {
      startListening((text) => {
        setTranscript((prev: string) => (prev ? prev + '\n' + text : text));
        setFileNotice('🎤 Voice input appended to transcript.');
      });
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);

    // If text file, read into textarea directly
    if (file.name.endsWith('.txt')) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        setTranscript(content);
        setFileNotice(`Loaded text content from "${file.name}"`);
      };
      reader.readAsText(file);
    } else {
      // PDF or DOCX notice
      setFileNotice(
        `Selected "${file.name}" (${(file.size / 1024).toFixed(1)} KB). Server-side PDF/DOCX extraction pipeline will be connected in Phase 4. Using current transcript buffer.`
      );
    }
  };

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (!transcript.trim()) return;
    navigate('/processing', { state: { transcript, title: 'Debate Analysis' } });
  };

  const handleLoadSample = () => {
    setTranscript(SAMPLE_TRANSCRIPT);
    setSelectedFile(null);
    setFileNotice('Loaded default AI in Education debate transcript.');
  };

  const handleClear = () => {
    setTranscript('');
    setSelectedFile(null);
    setFileNotice(null);
  };

  return (
    <div className="py-8 sm:py-12 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-950/60 text-indigo-400 border border-indigo-800/50 mb-3">
          <FileText className="w-3.5 h-3.5" />
          Discourse Ingestion Interface
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-3">
          Analyze Debate Transcript
        </h1>
        <p className="text-sm sm:text-base text-slate-400 max-w-2xl leading-relaxed">
          Input an academic debate transcript with speaker turns to reconstruct the proposition-level argument graph and audit reasoning soundness.
        </p>
      </div>

      {/* System Integration Notice */}
      <div className="bg-slate-900/90 border border-indigo-500/30 rounded-xl p-4 text-xs text-slate-300 flex items-start gap-3">
        <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-semibold text-white">Live Pipeline Analysis:</span>{' '}
          Submitting this transcript launches the live ARGUMAP reasoning pipeline: NLP proposition segmentation, frozen-label component classification, relation inference, and structural reasoning graph synthesis.
        </div>
      </div>

      <form onSubmit={handleAnalyze} className="space-y-6">
        {/* Main Textarea Card */}
        <Card className="p-6 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
            <div>
              <label htmlFor="transcript" className="text-sm font-semibold text-white block">
                Transcript Content
              </label>
              <span className="text-xs text-slate-400">
                Prefix lines with speaker names (e.g. <code className="text-indigo-300 bg-slate-800 px-1 py-0.5 rounded">Speaker A:</code>, <code className="text-indigo-300 bg-slate-800 px-1 py-0.5 rounded">Affirmative:</code>)
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleLoadSample}
                icon={<RotateCcw className="w-3.5 h-3.5" />}
              >
                Sample Debate
              </Button>
              {/* 🎤 Microphone button */}
              <button
                type="button"
                onClick={handleMicToggle}
                disabled={!sttSupported}
                title={
                  !sttSupported
                    ? 'Speech recognition requires Chrome or Edge'
                    : sttStatus === 'listening'
                    ? 'Stop microphone'
                    : 'Dictate transcript via microphone'
                }
                className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all
                  ${sttStatus === 'listening'
                    ? 'bg-emerald-950/60 border-emerald-600 text-emerald-300 animate-pulse'
                    : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-indigo-600 hover:text-indigo-300'}
                  disabled:opacity-40 disabled:cursor-not-allowed`}
              >
                {sttStatus === 'listening'
                  ? <><MicOff className="w-3.5 h-3.5" /> Stop</>
                  : <><Mic className="w-3.5 h-3.5" /> Dictate</>}
              </button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleClear}
                disabled={!transcript}
              >
                Clear
              </Button>
            </div>
          </div>

          <textarea
            id="transcript"
            rows={12}
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Speaker A: AI should be used in education because it enables personalized learning.&#10;Speaker B: However, excessive dependence on AI can reduce independent thinking.&#10;Speaker A: This risk can be reduced through teacher supervision."
            className="w-full bg-slate-950/80 border border-slate-800 rounded-lg p-4 font-mono text-xs sm:text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors leading-relaxed resize-y"
            required
          />

          {/* Counts & Status Bar */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-slate-400 pt-2">
            <div className="flex items-center gap-4 font-mono">
              <span>{wordCount} words</span>
              <span className="text-slate-600">•</span>
              <span>{charCount} characters</span>
              <span className="text-slate-600">•</span>
              <span>{transcript.split('\n').filter((l: string) => l.trim().length > 0).length} turns detected</span>
            </div>

            <div className="text-[11px] text-slate-500">
              Format: Plain Text (UTF-8)
            </div>
          </div>
        </Card>

        {/* File Upload Auxiliary Section */}
        <Card className="p-6 space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Upload className="w-4 h-4 text-indigo-400" />
            Upload Document File
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Drag and drop or select a formatted transcript file. Supported document extensions:
            <span className="text-slate-300 font-mono ml-1 font-semibold">.txt, .pdf, .docx</span>
          </p>

          <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl p-6 text-center cursor-pointer transition-colors relative bg-slate-950/40">
            <input
              type="file"
              accept=".txt,.pdf,.docx"
              onChange={handleFileUpload}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            />
            <div className="flex flex-col items-center justify-center space-y-2">
              <div className="w-10 h-10 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400">
                <FileCode className="w-5 h-5 text-indigo-400" />
              </div>
              <div className="text-xs font-medium text-slate-300">
                {selectedFile ? (
                  <span className="text-emerald-400 font-semibold font-mono">
                    Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </span>
                ) : (
                  <>
                    <span className="text-indigo-400 font-semibold underline underline-offset-2">Click to choose</span> or drag document here
                  </>
                )}
              </div>
              <span className="text-[11px] text-slate-500 font-mono">Max file size: 10MB</span>
            </div>
          </div>

          {fileNotice && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-indigo-950/40 border border-indigo-800/40 text-xs text-indigo-300">
              <CheckCircle className="w-4 h-4 shrink-0 text-indigo-400" />
              <span>{fileNotice}</span>
            </div>
          )}

          {sttError && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-950/40 border border-rose-800/40 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{sttError}</span>
            </div>
          )}
        </Card>

        {/* Action Button */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <AlertCircle className="w-4 h-4 text-slate-400" />
            <span>Transcripts are processed strictly for argumentation reasoning structure.</span>
          </div>

          <Button
            type="submit"
            size="lg"
            variant="primary"
            disabled={!transcript.trim()}
            icon={<Sparkles className="w-4 h-4" />}
            className="w-full sm:w-auto"
          >
            Launch Reasoning Analysis
          </Button>
        </div>
      </form>
    </div>
  );
};
