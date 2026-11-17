import React from 'react';
import { Card } from '../components/Card';
import { SectionHeading } from '../components/SectionHeading';
import { Cpu, Network, Code, Server, Shield } from 'lucide-react';

export const TechnologyPage: React.FC = () => {
  return (
    <div className="py-8 sm:py-14 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto space-y-12">
      <SectionHeading
        badge="System Architecture"
        title="Technical Stack & Design Blueprint"
        subtitle="A modular monolith architecture designed for reproducibility, high-throughput inference, and sub-second interactive visualization."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6 space-y-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400">
            <Code className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white">Frontend Layer</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Single-page client constructed with React 18, TypeScript (strict mode), Vite, and Tailwind CSS. The visual topology is powered by React Flow with custom component nodes, animated relationship edges, and dynamic viewport controls.
          </p>
          <div className="text-[11px] font-mono text-indigo-400">
            React • TypeScript • Tailwind • React Flow
          </div>
        </Card>

        <Card className="p-6 space-y-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-950 border border-emerald-800 flex items-center justify-center text-emerald-400">
            <Server className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white">Backend & API Orchestration</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Asynchronous Python service powered by FastAPI and Pydantic v2. Orchestrates regex speaker turn parsing, spaCy proposition segmentation, model inference wrappers, and serializes graph states into PostgreSQL via SQLAlchemy v2.
          </p>
          <div className="text-[11px] font-mono text-emerald-400">
            FastAPI • Pydantic v2 • SQLAlchemy v2 • Alembic
          </div>
        </Card>

        <Card className="p-6 space-y-3">
          <div className="w-9 h-9 rounded-lg bg-sky-950 border border-sky-800 flex items-center justify-center text-sky-400">
            <Cpu className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white">Machine Learning & NLP</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Two-stage argument mining pipeline. Task 1 applies a fine-tuned transformer classifier over the 6 frozen component labels with a TF-IDF baseline. Task 2 uses pairwise link prediction with 4-stage candidate pruning to defeat O(n²) explosion.
          </p>
          <div className="text-[11px] font-mono text-sky-400">
            PyTorch • Hugging Face • scikit-learn • spaCy
          </div>
        </Card>

        <Card className="p-6 space-y-3">
          <div className="w-9 h-9 rounded-lg bg-amber-950 border border-amber-800 flex items-center justify-center text-amber-400">
            <Network className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white">Graph Topology & Reasoning Audits</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Directed multigraphs constructed via NetworkX. Performs structural validation, cycle detection, and layout coordinate calculations. Deterministic heuristic rules audit unsupported claims and unanswered counterarguments.
          </p>
          <div className="text-[11px] font-mono text-amber-400">
            NetworkX MultiDiGraph • Structural Heuristics
          </div>
        </Card>
      </div>

      <Card className="p-6 border-slate-800 bg-slate-900/60 space-y-4">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <Shield className="w-4 h-4 text-indigo-400" />
          Architectural Scope Constraints
        </h4>
        <p className="text-xs text-slate-400 leading-relaxed">
          In strict accordance with the project specification, ARGUMAP core classification models rely on reproducible supervised transformers and classical baselines. Generative LLMs are excluded from the core classification pipeline and are reserved exclusively for potential explanatory layers in later phases.
        </p>
      </Card>
    </div>
  );
};
