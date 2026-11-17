import React from 'react';
import { Link } from 'react-router-dom';
import { Network, Github, BookOpen, ShieldCheck } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-900 bg-slate-950 text-slate-400 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          {/* Col 1: Identity */}
          <div className="space-y-3 md:col-span-1">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white">
                <Network className="w-4 h-4" />
              </div>
              <span className="text-base font-bold text-white tracking-tight">ARGUMAP</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Automated Argument Structure Analysis and Debate Reasoning using Natural Language Processing.
            </p>
            <div className="text-[11px] text-slate-500 font-mono">
              Academic Research Foundation • V1 Blueprint
            </div>
          </div>

          {/* Col 2: Navigation */}
          <div>
            <h5 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-3">
              Application
            </h5>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/analyze" className="hover:text-indigo-400 transition-colors">
                  Analyze Transcript
                </Link>
              </li>
              <li>
                <Link to="/results" className="hover:text-indigo-400 transition-colors">
                  Sample Argument Graph
                </Link>
              </li>
              <li>
                <Link to="/how-it-works" className="hover:text-indigo-400 transition-colors">
                  How It Works
                </Link>
              </li>
              <li>
                <Link to="/technology" className="hover:text-indigo-400 transition-colors">
                  Planned Stack & Architecture
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Research Foundations */}
          <div>
            <h5 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-3">
              NLP Architecture
            </h5>
            <ul className="space-y-2 text-xs">
              <li className="flex items-center gap-1.5 text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
                Task 1: Component Classifier
              </li>
              <li className="flex items-center gap-1.5 text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-500"></span>
                Task 2: Relation Extractor
              </li>
              <li className="flex items-center gap-1.5 text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Topological Multigraph Engine
              </li>
              <li className="flex items-center gap-1.5 text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                Structural Insight Audits
              </li>
            </ul>
          </div>

          {/* Col 4: Scientific Boundaries */}
          <div>
            <h5 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-3">
              Ethical AI Policy
            </h5>
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-[11px] text-slate-400 leading-relaxed">
              <div className="flex items-center gap-1 text-slate-300 font-medium mb-1">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                No Winner Prediction
              </div>
              ARGUMAP reconstructs dialectical reasoning structure. It does not predict debate winners, score rhetoric, or adjudicate truth values.
            </div>
          </div>
        </div>

        <div className="border-t border-slate-900 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <p>© {new Date().getFullYear()} ARGUMAP Project. Built for academic debate analysis and argumentation research.</p>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1 hover:text-slate-400 cursor-pointer">
              <BookOpen className="w-3.5 h-3.5" /> Docs
            </span>
            <span className="inline-flex items-center gap-1 hover:text-slate-400 cursor-pointer">
              <Github className="w-3.5 h-3.5" /> Repository
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};
