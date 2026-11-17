import React from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  ArrowRight,
  GitBranch,
  Network,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Database,
  BarChart3,
} from 'lucide-react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { SectionHeading } from '../components/SectionHeading';

export const LandingPage: React.FC = () => {
  return (
    <div className="space-y-24 py-8 sm:py-16">
      {/* 1. Hero Section */}
      <section className="relative px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center max-w-3xl mx-auto mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium tracking-wide uppercase bg-indigo-950/70 text-indigo-400 border border-indigo-800/60 mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
            Automated Argument Structure Analysis
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white mb-6 leading-tight">
            Understand the Structure Behind Every Argument.
          </h1>

          <p className="text-lg sm:text-xl text-slate-300 font-normal leading-relaxed mb-4">
            Understand the reasoning behind every debate.
          </p>

          <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto mb-8 leading-relaxed">
            ARGUMAP reconstructs the reasoning structure of a debate by connecting claims, supporting arguments, counterarguments, and rebuttals into an interactive argument map.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/analyze">
              <Button size="lg" variant="primary" icon={<Sparkles className="w-4 h-4" />}>
                Analyze a Debate
              </Button>
            </Link>
            <Link to="/results">
              <Button size="lg" variant="outline" icon={<Network className="w-4 h-4" />}>
                Explore Sample Graph
              </Button>
            </Link>
          </div>
        </div>

        {/* Hero Interactive Argument Graph Preview Graphic */}
        <div className="max-w-4xl mx-auto rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:p-8 shadow-2xl relative overflow-hidden backdrop-blur-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6 text-xs text-slate-400">
            <div className="flex items-center gap-2 font-mono">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
              ARGUMAP REASONING GRAPH PREVIEW — AI IN EDUCATION DEBATE
            </div>
            <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-[11px] font-mono">
              6 Nodes • 5 Relations
            </span>
          </div>

          {/* Visual Diagram Representation */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
            {/* Column 1: Affirmative Premise & Evidence */}
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl border border-sky-500/70 bg-sky-950/40 text-xs">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-sky-400 text-[10px] uppercase">PREMISE</span>
                  <span className="text-slate-400 text-[10px]">Speaker A</span>
                </div>
                <p className="text-slate-200">"Enables personalized learning at scale"</p>
              </div>

              <div className="flex justify-center text-slate-600">
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                  ↑ SUPPORTS
                </span>
              </div>

              <div className="p-3.5 rounded-xl border border-emerald-500/70 bg-emerald-950/40 text-xs">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-emerald-400 text-[10px] uppercase">EVIDENCE</span>
                  <span className="text-slate-400 text-[10px]">Speaker A</span>
                </div>
                <p className="text-slate-200">"2024 Stanford study: 23% retention lift"</p>
              </div>
            </div>

            {/* Column 2: Central Root Claim */}
            <div className="flex flex-col items-center justify-center p-5 rounded-xl border-2 border-indigo-500 bg-indigo-950/60 shadow-lg shadow-indigo-950/50 text-center space-y-2">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-900 border border-indigo-700 text-indigo-300 uppercase tracking-wider">
                CORE CLAIM
              </span>
              <h4 className="text-sm font-semibold text-white">
                "AI should be used in education"
              </h4>
              <span className="text-[11px] text-slate-400">Speaker A • 96% confidence</span>
            </div>

            {/* Column 3: Counterargument & Rebuttal */}
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl border border-amber-500/70 bg-amber-950/40 text-xs">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-amber-400 text-[10px] uppercase">COUNTERARGUMENT</span>
                  <span className="text-slate-400 text-[10px]">Speaker B</span>
                </div>
                <p className="text-slate-200">"Reduces independent critical thinking"</p>
              </div>

              <div className="flex justify-center text-slate-600">
                <span className="text-[10px] font-mono text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/40">
                  ↑ RESPONDS_TO
                </span>
              </div>

              <div className="p-3.5 rounded-xl border border-rose-500/70 bg-rose-950/40 text-xs">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-rose-400 text-[10px] uppercase">REBUTTAL</span>
                  <span className="text-slate-400 text-[10px]">Speaker A</span>
                </div>
                <p className="text-slate-200">"Mitigated via structured teacher supervision"</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Problem Section */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <SectionHeading
          badge="The Computational Problem"
          title="Why Sentiment and Topic Analysis Fall Short"
          subtitle="Deliberation and competitive debates are defined by logical structure, not emotional valence. Existing tools reduce text to word clouds while ignoring dialectical reasoning."
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card hoverable className="space-y-3">
            <div className="w-10 h-10 rounded-lg bg-rose-950/60 border border-rose-800/50 flex items-center justify-center text-rose-400 mb-2">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">Blind to Reasoning Chains</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Standard NLP pipelines group keywords by topic or polarity, but cannot discern whether a sentence serves as an empirical foundation, a core thesis, or an unbacked assertion.
            </p>
          </Card>

          <Card hoverable className="space-y-3">
            <div className="w-10 h-10 rounded-lg bg-amber-950/60 border border-amber-800/50 flex items-center justify-center text-amber-400 mb-2">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">Unanswered Rebuttals Go Unseen</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              In fast-paced debate rounds, participants frequently drop counterarguments or talk past each other. Without relational edge prediction, these logical gaps remain invisible.
            </p>
          </Card>

          <Card hoverable className="space-y-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-950/60 border border-indigo-800/50 flex items-center justify-center text-indigo-400 mb-2">
              <Network className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">No Structural Synthesis</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Adjudicators and researchers must manually reconstruct complex argument trees from transcripts. ARGUMAP automates the topological synthesis into interactive visual maps.
            </p>
          </Card>
        </div>
      </section>

      {/* 3. How It Works Section */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <SectionHeading
          badge="End-to-End Pipeline"
          title="From Raw Transcript to Argument Topology"
          subtitle="ARGUMAP executes a disciplined, scientific 7-step process to parse, segment, classify, and graph debate interactions."
        />

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 relative">
            <div className="text-xs font-mono font-bold text-indigo-400 mb-2">PHASE 01</div>
            <h4 className="text-base font-semibold text-white mb-1.5">Speaker Segmentation</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Deterministic regex and tokenizers parse chronological turns, attributing discourse to speakers.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 relative">
            <div className="text-xs font-mono font-bold text-sky-400 mb-2">PHASE 02</div>
            <h4 className="text-base font-semibold text-white mb-1.5">Proposition Isolation</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              spaCy boundary detection isolates discrete argument units from multi-sentence turns.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 relative">
            <div className="text-xs font-mono font-bold text-emerald-400 mb-2">PHASE 03</div>
            <h4 className="text-base font-semibold text-white mb-1.5">Component & Link ML</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Supervised classifiers assign the 6 frozen component labels and 4 directional relation labels.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 relative">
            <div className="text-xs font-mono font-bold text-amber-400 mb-2">PHASE 04</div>
            <h4 className="text-base font-semibold text-white mb-1.5">Graph & Insights</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              NetworkX compiles the multigraph, validates cycles, and highlights unaddressed arguments.
            </p>
          </div>
        </div>
      </section>

      {/* 4. Key Features */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <SectionHeading
          badge="Capabilities"
          title="Engineered for Academic Rigor"
          subtitle="Designed specifically for competitive debate analysis, academic argumentation research, and legal reasoning studies."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card hoverable className="space-y-2.5">
            <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
              <CheckCircle2 className="w-4 h-4" />
              6 Frozen Component Labels
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Strict classification across Claims, Premises, Evidence, Counterarguments, Rebuttals, and Other conversational turns.
            </p>
          </Card>

          <Card hoverable className="space-y-2.5">
            <div className="flex items-center gap-2 text-sky-400 font-semibold text-sm">
              <GitBranch className="w-4 h-4" />
              Pairwise Relation Extraction
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Directional link prediction with 4-stage candidate pruning, preventing O(n²) explosion across long debates.
            </p>
          </Card>

          <Card hoverable className="space-y-2.5">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
              <Network className="w-4 h-4" />
              Interactive React Flow Canvas
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Freely pan, zoom, drag nodes, inspect confidence metrics, and filter visual clusters by speaker or argument type.
            </p>
          </Card>

          <Card hoverable className="space-y-2.5">
            <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
              <BarChart3 className="w-4 h-4" />
              Automated Reasoning Audits
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Instantly surfaces unsupported claims, dropped counterarguments, and quantifies direct team clashes.
            </p>
          </Card>

          <Card hoverable className="space-y-2.5">
            <div className="flex items-center gap-2 text-rose-400 font-semibold text-sm">
              <ShieldCheck className="w-4 h-4" />
              Strict Ethical Scope
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Explicitly excludes winner prediction, ideological bias scoring, and political stance classification.
            </p>
          </Card>

          <Card hoverable className="space-y-2.5">
            <div className="flex items-center gap-2 text-slate-300 font-semibold text-sm">
              <Database className="w-4 h-4" />
              Reproducible Architecture
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Built on documented debate corpora, fixed seeds, PostgreSQL relational integrity, and standard API schemas.
            </p>
          </Card>
        </div>
      </section>

      {/* 5. Technology Section */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <SectionHeading
          badge="Technical Foundation"
          title="Modern NLP and Web Stack"
          subtitle="Built using industry-standard tools across frontend visualization, asynchronous backend orchestration, and machine learning."
        />

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4 text-center">
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-mono font-bold text-white mb-1">React + TS</div>
            <span className="text-[11px] text-slate-400">Strict Type Safety</span>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-mono font-bold text-indigo-400 mb-1">React Flow</div>
            <span className="text-[11px] text-slate-400">Graph Rendering</span>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-mono font-bold text-emerald-400 mb-1">FastAPI</div>
            <span className="text-[11px] text-slate-400">Async Python API</span>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-mono font-bold text-sky-400 mb-1">spaCy</div>
            <span className="text-[11px] text-slate-400">Segmentation</span>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-mono font-bold text-rose-400 mb-1">PyTorch</div>
            <span className="text-[11px] text-slate-400">Transformers</span>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-mono font-bold text-amber-400 mb-1">NetworkX</div>
            <span className="text-[11px] text-slate-400">Topology & Cycles</span>
          </div>
        </div>
      </section>

      {/* 6. Final Call to Action */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto">
        <div className="rounded-2xl border border-indigo-900/80 bg-gradient-to-b from-indigo-950/40 to-slate-950 p-8 sm:p-12 text-center space-y-6">
          <h3 className="text-2xl sm:text-3xl font-bold text-white">
            Ready to Map the Reasoning of Your First Debate?
          </h3>
          <p className="text-sm sm:text-base text-slate-400 max-w-xl mx-auto leading-relaxed">
            Upload or paste a debate transcript to test the interactive visualization workflow and explore argument components.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/analyze">
              <Button size="lg" variant="primary" icon={<ArrowRight className="w-4 h-4" />}>
                Launch Analysis Tool
              </Button>
            </Link>
            <Link to="/how-it-works">
              <Button size="lg" variant="secondary">
                Read Annotation Specs
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};
