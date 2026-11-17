import React from 'react';
import { CheckCircle2, CircleDashed, Clock } from 'lucide-react';

export type StepStatus = 'pending' | 'in_progress' | 'completed';

interface ProcessingStepProps {
  stepNumber: number;
  title: string;
  description: string;
  status: StepStatus;
  isLast?: boolean;
}

export const ProcessingStep: React.FC<ProcessingStepProps> = ({
  stepNumber,
  title,
  description,
  status,
  isLast = false,
}) => {
  return (
    <div className="flex items-start gap-4 relative">
      {!isLast && (
        <div
          className={`absolute left-5 top-10 w-0.5 h-[calc(100%-8px)] transition-colors duration-300 ${
            status === 'completed' ? 'bg-indigo-500' : 'bg-slate-800'
          }`}
        />
      )}

      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 border transition-all duration-300 z-10 ${
          status === 'completed'
            ? 'bg-indigo-950 border-indigo-500 text-indigo-400'
            : status === 'in_progress'
            ? 'bg-indigo-600/20 border-indigo-400 text-indigo-300 ring-4 ring-indigo-500/20'
            : 'bg-slate-900 border-slate-800 text-slate-500'
        }`}
      >
        {status === 'completed' ? (
          <CheckCircle2 className="w-5 h-5" />
        ) : status === 'in_progress' ? (
          <CircleDashed className="w-5 h-5 animate-spin text-indigo-400" />
        ) : (
          <Clock className="w-4 h-4" />
        )}
      </div>

      <div className="pt-1.5 pb-8">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-mono text-slate-500 font-semibold">
            STEP {stepNumber.toString().padStart(2, '0')}
          </span>
          <span
            className={`text-xs px-2 py-0.2 rounded font-medium ${
              status === 'completed'
                ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                : status === 'in_progress'
                ? 'bg-indigo-950/80 text-indigo-300 border border-indigo-700/50 animate-pulse'
                : 'bg-slate-800/60 text-slate-500'
            }`}
          >
            {status === 'completed'
              ? 'Complete'
              : status === 'in_progress'
              ? 'Processing...'
              : 'Queued'}
          </span>
        </div>
        <h4 className="text-base font-semibold text-white mb-0.5">{title}</h4>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
    </div>
  );
};
