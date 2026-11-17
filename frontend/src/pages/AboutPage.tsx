import React from 'react';
import { Card } from '../components/Card';
import { SectionHeading } from '../components/SectionHeading';
import { ShieldCheck, Target, Award, Users } from 'lucide-react';

export const AboutPage: React.FC = () => {
  return (
    <div className="py-8 sm:py-14 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto space-y-12">
      <SectionHeading
        badge="About ARGUMAP"
        title="Automated Debate Reasoning & Analysis"
        subtitle="A computational linguistics initiative dedicated to understanding and visualizing the logical architecture of human debate."
      />

      <div className="space-y-6">
        <Card className="p-6 border-indigo-900/60 bg-gradient-to-r from-indigo-950/30 to-slate-900/60 space-y-3">
          <div className="text-xs font-mono font-bold text-indigo-400 uppercase tracking-wider">
            Our Unique Proposition
          </div>
          <blockquote className="text-lg sm:text-xl font-medium text-white italic leading-relaxed">
            "ARGUMAP reconstructs the reasoning structure of a debate by connecting claims, supporting arguments, counterarguments, and rebuttals into an interactive argument map."
          </blockquote>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-5 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400">
              <Target className="w-5 h-5" />
            </div>
            <h4 className="text-base font-semibold text-white">Academic Debate</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Equipping competitive debaters, coaches, and tournament adjudicators with objective visual tools to evaluate whether contention clashes were addressed or dropped.
            </p>
          </Card>

          <Card className="p-5 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-950 border border-emerald-800 flex items-center justify-center text-emerald-400">
              <Award className="w-5 h-5" />
            </div>
            <h4 className="text-base font-semibold text-white">Scientific Argumentation</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Synthesizing contradictory findings across research literature into coherent claim-evidence trees to audit scientific consensus and open hypotheses.
            </p>
          </Card>

          <Card className="p-5 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-sky-950 border border-sky-800 flex items-center justify-center text-sky-400">
              <Users className="w-5 h-5" />
            </div>
            <h4 className="text-base font-semibold text-white">Deliberative Governance</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Assisting civic stakeholders and policy analysts in auditing legislative transcripts to verify that civic objections have been answered with empirical grounds.
            </p>
          </Card>
        </div>

        <Card className="p-6 border-slate-800 bg-slate-900/60 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Scientific Honesty & Non-Partisanship
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            ARGUMAP is engineered to analyze argumentation structure rather than pass moral or partisan judgment. The platform explicitly excludes debate winner prediction, stance polarity scoring, and political bias tagging to preserve scholarly neutrality.
          </p>
        </Card>
      </div>
    </div>
  );
};
