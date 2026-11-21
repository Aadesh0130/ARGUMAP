import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  ArrowRight,
  Activity,
  Terminal,
  AlertCircle,
  RotateCcw,
  Loader2,
  FileEdit,
} from 'lucide-react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { ProcessingStep, StepStatus } from '../components/ProcessingStep';
import { analyzeTranscript, ApiError } from '../lib/api';
import { adaptApiResponse } from '../lib/apiAdapter';
import { SAMPLE_TRANSCRIPT } from '../lib/mockData';
import { AnalysisResult, RawAnalysisResponse } from '../types';

interface PipelineStepConfig {
  number: number;
  title: string;
  description: string;
  logMessage: string;
}

const PIPELINE_STEPS: PipelineStepConfig[] = [
  {
    number: 1,
    title: 'Sanitizing discourse text',
    description: 'Normalizing raw transcript buffer, standardizing line breaks, and validating character encoding.',
    logMessage: '>> [INGEST] Sanitized transcript buffer and normalized character stream.',
  },
  {
    number: 2,
    title: 'Extracting speaker turns',
    description: 'Identifying debater entities, isolating chronological turns, and attributing speaker metadata.',
    logMessage: '>> [SPEAKER_PARSER] Ingested speech turns and resolved speaker identities.',
  },
  {
    number: 3,
    title: 'Segmenting propositions',
    description: 'Applying boundary detection to extract proposition-level units with verbatim character offsets.',
    logMessage: '>> [NLP_SEGMENT] Extracted proposition-level units with exact character sub-spans.',
  },
  {
    number: 4,
    title: 'Classifying argument components',
    description: 'Evaluating propositions across the frozen 6-class taxonomy (CLAIM, PREMISE, EVIDENCE, etc.).',
    logMessage: '>> [CLASSIFIER] Applied frozen 6-class component classification rules.',
  },
  {
    number: 5,
    title: 'Inferring argument relations',
    description: 'Evaluating candidate argument pairs to infer SUPPORTS, ATTACKS, and RESPONDS_TO links.',
    logMessage: '>> [RELATION_ENGINE] Evaluated candidate pairs without self-referencing loops.',
  },
  {
    number: 6,
    title: 'Constructing argument graph',
    description: 'Building NetworkX directed multigraph and calculating deterministic 2D canvas coordinates.',
    logMessage: '>> [GRAPH_BUILDER] Assembled NetworkX argument multigraph and deterministic node positions.',
  },
  {
    number: 7,
    title: 'Auditing structural reasoning',
    description: 'Detecting unsupported claims, unanswered counterarguments, and cross-speaker clashes.',
    logMessage: '>> [ANALYSIS_ENGINE] Structural analysis engine audited argument reasoning soundness.',
  },
];

const STEP_DURATION_MS = 350; // ~2.45s total progression for 7 steps

export const ProcessingPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const { transcript, title } = (location.state as { transcript?: string; title?: string }) || {};
  const effectiveTranscript = transcript || SAMPLE_TRANSCRIPT;
  const effectiveTitle = title || 'Debate Analysis';

  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [logs, setLogs] = useState<string[]>([PIPELINE_STEPS[0].logMessage]);
  const [apiResult, setApiResult] = useState<AnalysisResult | null>(null);
  const [apiState, setApiState] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');
  const [errorDetails, setErrorDetails] = useState<{ message: string; code?: string } | null>(null);
  const [isAnimationFinished, setIsAnimationFinished] = useState<boolean>(false);

  const autoNavTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const terminalBottomRef = useRef<HTMLDivElement | null>(null);
  const activeRequestIdRef = useRef<number>(0);

  // Auto-scroll terminal logs to bottom
  useEffect(() => {
    terminalBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Clean up auto navigation timer on unmount
  useEffect(() => {
    return () => {
      if (autoNavTimerRef.current) clearTimeout(autoNavTimerRef.current);
    };
  }, []);

  // Main execution runner (callable on mount or on retry)
  const executeAnalysis = useCallback(() => {
    // Clear any pending navigation
    if (autoNavTimerRef.current) {
      clearTimeout(autoNavTimerRef.current);
      autoNavTimerRef.current = null;
    }

    const currentReqId = ++activeRequestIdRef.current;

    // Reset visual state
    setCurrentStepIndex(0);
    setLogs([
      `// ARGUMAP Execution Engine v1.0.0`,
      `// Session Title: ${effectiveTitle}`,
      PIPELINE_STEPS[0].logMessage,
    ]);
    setApiResult(null);
    setApiState('running');
    setErrorDetails(null);
    setIsAnimationFinished(false);

    // Launch actual API request
    analyzeTranscript({ title: effectiveTitle, raw_transcript: effectiveTranscript })
      .then((rawResponse: RawAnalysisResponse) => {
        // Discard if a newer retry has been launched
        if (activeRequestIdRef.current !== currentReqId) return;

        const adapted = adaptApiResponse(rawResponse);
        setApiResult(adapted);
        setApiState('completed');

        // Persist to sessionStorage for browser refresh recovery
        try {
          sessionStorage.setItem('argumap_current_analysis', JSON.stringify(adapted));
        } catch (e) {
          console.warn('Unable to persist analysis to sessionStorage:', e);
        }
      })
      .catch((err: any) => {
        if (activeRequestIdRef.current !== currentReqId) return;

        const message = err instanceof ApiError
          ? err.message
          : err?.message || 'An unexpected error occurred during backend analysis.';
        const code = err?.code || (err?.status ? `HTTP_${err.status}` : 'INTERNAL_ERROR');

        setApiState('error');
        setErrorDetails({ message, code });
        setLogs((prev) => [
          ...prev,
          `>> [ERROR] Backend processing failed [${code}]: ${message}`,
        ]);
      });
  }, [effectiveTitle, effectiveTranscript]);

  // Run on initial mount
  useEffect(() => {
    executeAnalysis();
  }, [executeAnalysis]);

  // Handle step ladder animation progression
  useEffect(() => {
    if (apiState === 'error') return;

    // If we haven't reached the final step, advance on timer
    if (currentStepIndex < PIPELINE_STEPS.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStepIndex((prev) => {
          const next = prev + 1;
          if (next < PIPELINE_STEPS.length) {
            setLogs((l) => [...l, PIPELINE_STEPS[next].logMessage]);
          }
          return next;
        });
      }, STEP_DURATION_MS);
      return () => clearTimeout(timer);
    }

    // When on the final step (index 6, step 7):
    // Check if API has completed
    if (currentStepIndex === PIPELINE_STEPS.length - 1) {
      if (apiState === 'completed' && apiResult && !isAnimationFinished) {
        setIsAnimationFinished(true);
        setLogs((l) => [
          ...l,
          `>> [BACKEND] Verified reasoning graph: ${apiResult.summary.speaker_count} speaker(s), ${apiResult.summary.argument_count} argument(s), ${apiResult.summary.relation_count} relation(s), ${apiResult.insights.length} structural insight(s).`,
          `✓ Pipeline execution completed successfully.`,
        ]);

        // Auto-navigate to Results after a brief delay
        autoNavTimerRef.current = setTimeout(() => {
          navigate('/results', { state: { analysisResult: apiResult } });
        }, 600);
      }
    }
  }, [currentStepIndex, apiState, apiResult, isAnimationFinished, navigate]);

  // If API finished while we were at the final step waiting for it
  useEffect(() => {
    if (
      currentStepIndex === PIPELINE_STEPS.length - 1 &&
      apiState === 'completed' &&
      apiResult &&
      !isAnimationFinished
    ) {
      setIsAnimationFinished(true);
      setLogs((l) => [
        ...l,
        `>> [BACKEND] Verified reasoning graph: ${apiResult.summary.speaker_count} speaker(s), ${apiResult.summary.argument_count} argument(s), ${apiResult.summary.relation_count} relation(s), ${apiResult.insights.length} structural insight(s).`,
        `✓ Pipeline execution completed successfully.`,
      ]);

      autoNavTimerRef.current = setTimeout(() => {
        navigate('/results', { state: { analysisResult: apiResult } });
      }, 600);
    }
  }, [apiState, apiResult, currentStepIndex, isAnimationFinished, navigate]);

  // Explicit Skip or View button handler
  const handleProceedToResults = () => {
    if (!apiResult) return;
    if (autoNavTimerRef.current) clearTimeout(autoNavTimerRef.current);
    navigate('/results', { state: { analysisResult: apiResult } });
  };

  const getStepStatus = (index: number): StepStatus => {
    if (apiState === 'error') {
      if (index < currentStepIndex) return 'completed';
      if (index === currentStepIndex) return 'in_progress';
      return 'pending';
    }
    if (index < currentStepIndex) return 'completed';
    if (index === currentStepIndex) {
      return isAnimationFinished ? 'completed' : 'in_progress';
    }
    return 'pending';
  };

  return (
    <div className="py-8 sm:py-12 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-indigo-950/70 text-indigo-400 border border-indigo-800/60">
          <Activity className="w-3.5 h-3.5 animate-pulse text-indigo-400" />
          Pipeline Execution Monitor
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          {errorDetails
            ? 'Analysis Failed'
            : isAnimationFinished
            ? 'Analysis Successfully Compiled'
            : 'Reconstructing Debate Reasoning...'}
        </h1>
        <p className="text-sm text-slate-400 leading-relaxed">
          {errorDetails
            ? 'An error occurred while communicating with the backend analysis service.'
            : isAnimationFinished
            ? 'Argument graph topology and structural insights have been synthesized and are ready for interactive exploration.'
            : 'Executing NLP segmentation, frozen-label component classification, and graph link extraction.'}
        </p>
      </div>

      {/* Error Banner & Recovery Actions */}
      {errorDetails && (
        <Card className="p-5 border-rose-800/60 bg-rose-950/30 text-rose-200 space-y-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-1.5 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-rose-100 text-sm">
                  Backend Analysis Error
                </span>
                {errorDetails.code && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 border border-rose-800 text-rose-300">
                    {errorDetails.code}
                  </span>
                )}
              </div>
              <p className="text-xs text-rose-300 font-mono leading-relaxed">
                {errorDetails.message}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-rose-900/40">
            <Button
              size="sm"
              variant="primary"
              onClick={executeAnalysis}
              icon={<RotateCcw className="w-3.5 h-3.5" />}
            >
              Retry Analysis
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate('/analyze')}
              icon={<FileEdit className="w-3.5 h-3.5" />}
            >
              Edit Transcript
            </Button>
          </div>
        </Card>
      )}

      {/* Main Grid: Pipeline Steps & Console Log */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left: Step Progress Ladder */}
        <Card className="lg:col-span-7 p-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-6">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Pipeline Stage
            </span>
            <span className="text-xs font-mono text-indigo-400 font-medium">
              {Math.min(currentStepIndex + 1, PIPELINE_STEPS.length)} / {PIPELINE_STEPS.length}
            </span>
          </div>

          <div className="space-y-0">
            {PIPELINE_STEPS.map((step, idx) => (
              <ProcessingStep
                key={step.number}
                stepNumber={step.number}
                title={step.title}
                description={step.description}
                status={getStepStatus(idx)}
                isLast={idx === PIPELINE_STEPS.length - 1}
              />
            ))}
          </div>
        </Card>

        {/* Right: Real-time Terminal Log & Action */}
        <div className="lg:col-span-5 space-y-6">
          <Card className="p-5 space-y-3 bg-slate-950/90 border-slate-800">
            <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800 pb-2">
              <div className="flex items-center gap-1.5 font-mono">
                <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                Pipeline Stream
              </div>
              <span
                className={`w-2 h-2 rounded-full ${
                  errorDetails
                    ? 'bg-rose-500'
                    : isAnimationFinished
                    ? 'bg-emerald-500'
                    : 'bg-indigo-400 animate-ping'
                }`}
              />
            </div>

            <div className="font-mono text-[11px] text-slate-300 space-y-2 h-64 overflow-y-auto pr-1">
              {logs.map((log, index) => (
                <div
                  key={index}
                  className={`leading-relaxed ${
                    log.startsWith('>> [ERROR]')
                      ? 'text-rose-400 font-semibold'
                      : log.startsWith('✓')
                      ? 'text-emerald-400 font-semibold'
                      : log.startsWith('//')
                      ? 'text-slate-500'
                      : 'text-indigo-300'
                  }`}
                >
                  {log}
                </div>
              ))}
              {!isAnimationFinished && !errorDetails && (
                <div className="text-slate-500 animate-pulse flex items-center gap-1.5">
                  <Loader2 className="w-3 h-3 animate-spin text-indigo-400" />
                  <span>
                    {apiState === 'completed'
                      ? 'Compiling visual layout coordinates...'
                      : 'Awaiting backend pipeline response...'}
                  </span>
                </div>
              )}
              <div ref={terminalBottomRef} />
            </div>
          </Card>

          {/* Action Box */}
          {!errorDetails && (
            <Card className="p-5 border-indigo-900/60 bg-indigo-950/30 text-center space-y-4">
              <div className="text-xs text-slate-300">
                {isAnimationFinished
                  ? 'All nodes and relations have been positioned on the visual canvas.'
                  : apiState === 'completed'
                  ? 'Backend analysis complete! You may proceed directly to the reasoning dashboard.'
                  : 'Analyzing discourse arguments with live NLP and structural reasoning models...'}
              </div>

              <Button
                size="lg"
                variant="primary"
                className="w-full"
                disabled={apiState !== 'completed' || !apiResult}
                onClick={handleProceedToResults}
                icon={
                  apiState !== 'completed' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ArrowRight className="w-4 h-4" />
                  )
                }
              >
                {isAnimationFinished
                  ? 'View Argument Graph'
                  : apiState === 'completed'
                  ? 'Skip to Results'
                  : 'Processing Pipeline...'}
              </Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
