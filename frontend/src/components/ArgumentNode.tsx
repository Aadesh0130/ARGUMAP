import React, { memo } from 'react';
import { Handle, Position, NodeProps, Node } from '@xyflow/react';
import { ArgumentNodeData, ComponentType } from '../types';

export type ArgumentNodeType = Node<ArgumentNodeData, 'argumentNode'>;

const componentTheme: Record<
  ComponentType,
  {
    border: string;
    bg: string;
    badgeBg: string;
    badgeText: string;
    glow: string;
    handleColor: string;
  }
> = {
  CLAIM: {
    border: 'border-indigo-500',
    bg: 'bg-indigo-950/80',
    badgeBg: 'bg-indigo-900/80 border-indigo-700',
    badgeText: 'text-indigo-300',
    glow: 'shadow-[0_0_15px_rgba(99,102,241,0.25)]',
    handleColor: '#6366f1',
  },
  PREMISE: {
    border: 'border-sky-500',
    bg: 'bg-sky-950/80',
    badgeBg: 'bg-sky-900/80 border-sky-700',
    badgeText: 'text-sky-300',
    glow: 'shadow-[0_0_15px_rgba(14,165,233,0.25)]',
    handleColor: '#0ea5e9',
  },
  EVIDENCE: {
    border: 'border-emerald-500',
    bg: 'bg-emerald-950/80',
    badgeBg: 'bg-emerald-900/80 border-emerald-700',
    badgeText: 'text-emerald-300',
    glow: 'shadow-[0_0_15px_rgba(16,185,129,0.25)]',
    handleColor: '#10b981',
  },
  COUNTERARGUMENT: {
    border: 'border-amber-500',
    bg: 'bg-amber-950/80',
    badgeBg: 'bg-amber-900/80 border-amber-700',
    badgeText: 'text-amber-300',
    glow: 'shadow-[0_0_15px_rgba(245,158,11,0.25)]',
    handleColor: '#f59e0b',
  },
  REBUTTAL: {
    border: 'border-rose-500',
    bg: 'bg-rose-950/80',
    badgeBg: 'bg-rose-900/80 border-rose-700',
    badgeText: 'text-rose-300',
    glow: 'shadow-[0_0_15px_rgba(244,63,94,0.25)]',
    handleColor: '#f43f5e',
  },
  OTHER: {
    border: 'border-slate-600',
    bg: 'bg-slate-900/90',
    badgeBg: 'bg-slate-800 border-slate-700',
    badgeText: 'text-slate-400',
    glow: 'shadow-none',
    handleColor: '#64748b',
  },
};

export const ArgumentNode: React.FC<NodeProps<ArgumentNodeType>> = memo(({ data, selected }) => {
  const theme = componentTheme[data.component_type] || componentTheme.OTHER;

  return (
    <div
      className={`w-64 rounded-xl border-2 p-3.5 backdrop-blur-sm transition-all duration-200 select-none ${
        theme.border
      } ${theme.bg} ${selected ? `${theme.glow} ring-2 ring-white/60 scale-105` : 'shadow-md'}`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 rounded-full transition-colors"
        style={{ background: theme.handleColor }}
      />

      <div className="flex items-center justify-between gap-1.5 mb-2">
        <span
          className={`text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded border ${theme.badgeBg} ${theme.badgeText}`}
        >
          {data.component_type}
        </span>
        <span className="text-[11px] font-medium text-slate-300 bg-slate-900/90 px-1.5 py-0.5 rounded border border-slate-800">
          {data.speaker_name}
        </span>
      </div>

      <p className="text-xs text-slate-100 font-normal leading-relaxed line-clamp-3 mb-2.5">
        "{data.label}"
      </p>

      <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1.5 border-t border-slate-800/80">
        <span className="font-mono text-slate-500">Turn {data.turn_order}</span>
        <span className="font-mono text-slate-400">
          {(data.confidence * 100).toFixed(0)}% conf
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 rounded-full transition-colors"
        style={{ background: theme.handleColor }}
      />
    </div>
  );
});

ArgumentNode.displayName = 'ArgumentNode';
