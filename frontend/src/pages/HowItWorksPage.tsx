import React from 'react';
import { Card } from '../components/Card';
import { SectionHeading } from '../components/SectionHeading';
import { BookOpen, GitBranch } from 'lucide-react';

export const HowItWorksPage: React.FC = () => {
  return (
    <div className="py-8 sm:py-14 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto space-y-12">
      <SectionHeading
        badge="Methodology & Taxonomy"
        title="How ARGUMAP Reconstructs Debate Reasoning"
        subtitle="Computational argumentation decomposes complex dialectical exchanges into verifiable proposition units and directional relational graphs."
      />

      {/* Component Taxonomy */}
      <section className="space-y-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-indigo-400" />
          Frozen Component Taxonomy (6 Labels)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="p-4 border-indigo-900/60 bg-indigo-950/20 space-y-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-indigo-900/80 text-indigo-300 border border-indigo-700 uppercase">
              CLAIM
            </span>
            <p className="text-sm font-semibold text-white">Central Contentious Assertion</p>
            <p className="text-xs text-slate-400">
              The overarching thesis or normative proposition put forward by a speaker as a primary contention.
            </p>
            <div className="text-[11px] font-mono text-indigo-300/80 bg-slate-950 p-2 rounded">
              Example: "AI should be used in education."
            </div>
          </Card>

          <Card className="p-4 border-sky-900/60 bg-sky-950/20 space-y-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-sky-900/80 text-sky-300 border border-sky-700 uppercase">
              PREMISE
            </span>
            <p className="text-sm font-semibold text-white">Causal or Logical Ground</p>
            <p className="text-xs text-slate-400">
              A reason, rationale, or foundational statement offered to justify or substantiate an associated claim.
            </p>
            <div className="text-[11px] font-mono text-sky-300/80 bg-slate-950 p-2 rounded">
              Example: "...because it enables personalized learning."
            </div>
          </Card>

          <Card className="p-4 border-emerald-900/60 bg-emerald-950/20 space-y-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-900/80 text-emerald-300 border border-emerald-700 uppercase">
              EVIDENCE
            </span>
            <p className="text-sm font-semibold text-white">Empirical & Statistical Fact</p>
            <p className="text-xs text-slate-400">
              Quantitative data, study findings, research citations, or concrete real-world demonstrations.
            </p>
            <div className="text-[11px] font-mono text-emerald-300/80 bg-slate-950 p-2 rounded">
              Example: "A 2024 Stanford study found a 23% improvement in retention..."
            </div>
          </Card>

          <Card className="p-4 border-amber-900/60 bg-amber-950/20 space-y-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-900/80 text-amber-300 border border-amber-700 uppercase">
              COUNTERARGUMENT
            </span>
            <p className="text-sm font-semibold text-white">Direct Opposing Contention</p>
            <p className="text-xs text-slate-400">
              An objection, competing rationale, or harm raised directly against a previous speaker's claim or premise.
            </p>
            <div className="text-[11px] font-mono text-amber-300/80 bg-slate-950 p-2 rounded">
              Example: "However, excessive dependence reduces independent thinking."
            </div>
          </Card>

          <Card className="p-4 border-rose-900/60 bg-rose-950/20 space-y-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-rose-900/80 text-rose-300 border border-rose-700 uppercase">
              REBUTTAL
            </span>
            <p className="text-sm font-semibold text-white">Defense & Contradiction Counter</p>
            <p className="text-xs text-slate-400">
              A defensive response designed to neutralize, minimize, or invalidate an opponent's counterargument.
            </p>
            <div className="text-[11px] font-mono text-rose-300/80 bg-slate-950 p-2 rounded">
              Example: "This risk can be reduced through teacher supervision."
            </div>
          </Card>

          <Card className="p-4 border-slate-800 bg-slate-900/40 space-y-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 uppercase">
              OTHER
            </span>
            <p className="text-sm font-semibold text-white">Procedural & Conversational</p>
            <p className="text-xs text-slate-400">
              Greetings, procedural remarks, acknowledgments, or non-argumentative discourse filler.
            </p>
            <div className="text-[11px] font-mono text-slate-400 bg-slate-950 p-2 rounded">
              Example: "Thank you, Madame Speaker, and good afternoon."
            </div>
          </Card>
        </div>
      </section>

      {/* Relation Taxonomy */}
      <section className="space-y-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-indigo-400" />
          Frozen Relation Taxonomy (4 Labels)
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4 space-y-2">
            <div className="text-xs font-bold font-mono text-emerald-400">SUPPORTS</div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Source unit reinforces, justifies, or strengthens the validity of target unit ($u_A \rightarrow u_B$).
            </p>
          </Card>

          <Card className="p-4 space-y-2">
            <div className="text-xs font-bold font-mono text-rose-400">ATTACKS</div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Source unit directly challenges, contradicts, or attempts to falsify target unit ($u_A \rightarrow u_B$).
            </p>
          </Card>

          <Card className="p-4 space-y-2">
            <div className="text-xs font-bold font-mono text-indigo-400">RESPONDS_TO</div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Source unit addresses or reframes target unit without necessarily constituting a binary attack.
            </p>
          </Card>

          <Card className="p-4 space-y-2">
            <div className="text-xs font-bold font-mono text-slate-500">NO_RELATION</div>
            <p className="text-xs text-slate-400 leading-relaxed">
              No direct logical, evidential, or dialectical connection exists between candidate units.
            </p>
          </Card>
        </div>
      </section>
    </div>
  );
};
