import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  hoverable = false,
}) => {
  return (
    <div
      className={`bg-slate-900/70 border border-slate-800/80 rounded-xl p-5 shadow-sm ${
        hoverable ? 'hover:border-slate-700 hover:bg-slate-900 transition-all duration-150' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
};
