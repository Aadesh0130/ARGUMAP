import React from 'react';

interface StatisticCardProps {
  label: string;
  value: number | string;
  badge?: string;
  badgeColor?: 'indigo' | 'sky' | 'emerald' | 'amber' | 'rose' | 'slate';
  icon?: React.ReactNode;
  description?: string;
  className?: string;
}

export const StatisticCard: React.FC<StatisticCardProps> = ({
  label,
  value,
  badge,
  badgeColor = 'slate',
  icon,
  description,
  className = '',
}) => {
  const colorMap = {
    indigo: 'text-indigo-400 border-indigo-800/60 bg-indigo-950/40',
    sky: 'text-sky-400 border-sky-800/60 bg-sky-950/40',
    emerald: 'text-emerald-400 border-emerald-800/60 bg-emerald-950/40',
    amber: 'text-amber-400 border-amber-800/60 bg-amber-950/40',
    rose: 'text-rose-400 border-rose-800/60 bg-rose-950/40',
    slate: 'text-slate-400 border-slate-800/60 bg-slate-900/60',
  };

  return (
    <div className={`bg-slate-900/80 border border-slate-800/80 rounded-xl p-4.5 shadow-sm ${className}`}>
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
          {label}
        </span>
        {badge && (
          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${colorMap[badgeColor]}`}>
            {badge}
          </span>
        )}
        {icon && <span className="text-slate-500">{icon}</span>}
      </div>
      <div className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-1">
        {value}
      </div>
      {description && (
        <div className="text-xs text-slate-400 line-clamp-1">
          {description}
        </div>
      )}
    </div>
  );
};
