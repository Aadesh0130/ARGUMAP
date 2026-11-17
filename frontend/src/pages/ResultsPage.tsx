import React, { useState, useMemo, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  Node,
  Edge,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  Network,
  Filter,
  Info,
  AlertTriangle,
  CheckCircle,
  Sparkles,
  RotateCcw,
} from 'lucide-react';

import { ArgumentNode, ArgumentNodeType } from '../components/ArgumentNode';
import { StatisticCard } from '../components/StatisticCard';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { VoiceBar } from '../components/VoiceBar';
import { useVoice } from '../hooks/useVoice';
import { MOCK_ANALYSIS_RESULT } from '../lib/mockData';
import { AnalysisResult } from '../types';

// Register custom node types for React Flow
const nodeTypes = {
  argumentNode: ArgumentNode,
};

export const ResultsPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const locationResult = (location.state as { analysisResult?: AnalysisResult })?.analysisResult;
  const analysisResult: AnalysisResult = useMemo(() => {
    if (locationResult) return locationResult;
    try {
      const cached = sessionStorage.getItem('argumap_current_analysis');
      if (cached) return JSON.parse(cached);
    } catch (e) {
      console.warn('Failed to parse cached analysis:', e);
    }
    return MOCK_ANALYSIS_RESULT;
  }, [locationResult]);

  const [selectedComponentFilter, setSelectedComponentFilter] = useState<string>('ALL');
  const [selectedSpeakerFilter, setSelectedSpeakerFilter] = useState<string>('ALL');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(
    analysisResult.arguments[0]?.id || null
  );

  // ── Voice system ──────────────────────────────────────────────────────
  const {
    ttsStatus, ttsError, speak, stopSpeaking,
    sttStatus, sttError, sttSupported, startListening, stopListening,
  } = useVoice();

  // Build a plain-text summary to pass to TTS
  const summaryText = useMemo(() => {
    const speakers = analysisResult.speakers.map((s) => s.name).join(', ');
    const args = analysisResult.arguments.length;
    const insights = analysisResult.insights
      .map((i) => i.message)
      .slice(0, 4)
      .join('. ');
    return (
      `This debate involves ${analysisResult.speakers.length} speaker(s): ${speakers}. ` +
      `${args} argument unit(s) were identified. ` +
      (insights ? `Key insights: ${insights}.` : '')
    );
  }, [analysisResult]);

  // STT: stream mic text back to Analyze page so user can re-analyse
  const handleStartListening = () => {
    startListening((transcript) => {
      navigate('/analyze', { state: { prefill: transcript } });
    });
  };

  // Convert arguments into React Flow nodes
  const initialNodes: ArgumentNodeType[] = useMemo(() => {
    return analysisResult.arguments.map((arg) => ({
      id: arg.id,
      type: 'argumentNode' as const,
      position: arg.graph_node?.position || { x: 0, y: 0 },
      data: {
        label: arg.text,
        component_type: arg.component_type,
        speaker_id: arg.speaker_id,
        speaker_name:
          analysisResult.speakers.find((s) => s.id === arg.speaker_id)?.name || 'Speaker',
        confidence: arg.confidence,
        turn_order: arg.turn_order,
      },
    }));
  }, [analysisResult]);

  // Convert relations into React Flow edges with distinct styling
  const initialEdges: Edge[] = useMemo(() => {
    return analysisResult.relations.map((rel) => {
      const isAttack = rel.relation_type === 'ATTACKS';
      const isSupport = rel.relation_type === 'SUPPORTS';

      const strokeColor = isAttack ? '#f43f5e' : isSupport ? '#10b981' : '#818cf8';

      return {
        id: rel.id,
        source: rel.source_argument_id,
        target: rel.target_argument_id,
        label: rel.relation_type,
        animated: isAttack,
        style: {
          stroke: strokeColor,
          strokeWidth: 2,
          strokeDasharray: isAttack ? '5,5' : undefined,
        },
        labelStyle: {
          fill: strokeColor,
          fontWeight: 700,
          fontSize: 10,
          fontFamily: 'monospace',
        },
        labelBgStyle: {
          fill: '#0f172a',
          fillOpacity: 0.9,
          stroke: strokeColor,
          strokeWidth: 1,
          rx: 4,
          ry: 4,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: strokeColor,
          width: 16,
          height: 16,
        },
      };
    });
  }, [analysisResult]);

  const [nodes, setNodes] = useState<ArgumentNodeType[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);

  const onNodesChange = useCallback(
    (changes: NodeChange<ArgumentNodeType>[]) =>
      setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  // Filter nodes based on user selection
  const filteredNodes = useMemo(() => {
    return nodes.map((node) => {
      const matchComponent =
        selectedComponentFilter === 'ALL' ||
        node.data.component_type === selectedComponentFilter;
      const matchSpeaker =
        selectedSpeakerFilter === 'ALL' || node.data.speaker_id === selectedSpeakerFilter;

      return {
        ...node,
        hidden: !(matchComponent && matchSpeaker),
      };
    });
  }, [nodes, selectedComponentFilter, selectedSpeakerFilter]);

  const selectedArgument = useMemo(() => {
    return analysisResult.arguments.find((a) => a.id === selectedNodeId);
  }, [selectedNodeId, analysisResult]);

  const isUsingMock = Boolean(
    analysisResult.analysis_id?.includes('mock') ||
    analysisResult.model_version?.toLowerCase().includes('mock')
  );

  return (
    <div className="py-6 sm:py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-6">
      {/* Disclaimer Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5 text-slate-300">
          <Info className="w-4 h-4 text-indigo-400 shrink-0" />
          <span>
            {isUsingMock ? (
              <>
                <strong className="text-white">Demonstration Dashboard:</strong> Argument graph and reasoning insights are currently rendered using baseline mock fixtures to showcase interactive capabilities.
              </>
            ) : (
              <>
                <strong className="text-white">Live Analysis:</strong> Argument graph and reasoning insights are rendered from real backend analysis results.
              </>
            )}
          </span>
        </div>
        <span className="font-mono text-[11px] text-slate-500 bg-slate-950 px-2 py-1 rounded border border-slate-800 shrink-0">
          Model: {analysisResult.model_version}
        </span>
      </div>

      {/* 🔊 Voice Bar */}
      <VoiceBar
        ttsStatus={ttsStatus}
        sttStatus={sttStatus}
        ttsError={ttsError}
        sttError={sttError}
        sttSupported={sttSupported}
        onSpeak={() => speak(summaryText)}
        onStopSpeaking={stopSpeaking}
        onStartListening={handleStartListening}
        onStopListening={stopListening}
        summaryText={summaryText}
      />

      {/* Top Bar: Title & Primary Metrics */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-indigo-400 mb-1">
            <span>DEBATE: {analysisResult.debate_id}</span>
            <span>•</span>
            <span>
              {analysisResult.summary.turn_count} TURNS • {analysisResult.summary.argument_count} ARGUMENTS
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Reasoning Structure Dashboard
          </h1>
        </div>

        {/* Action Controls & Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Analyze Another Debate Action */}
          <Button
            size="sm"
            variant="primary"
            onClick={() => navigate('/analyze')}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Analyze Another Debate
          </Button>

          {/* Component Filter */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400 ml-1.5" />
            <select
              value={selectedComponentFilter}
              onChange={(e) => setSelectedComponentFilter(e.target.value)}
              className="bg-transparent text-slate-200 text-xs font-medium focus:outline-none pr-2 cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900">All Components</option>
              <option value="CLAIM" className="bg-slate-900">Claims</option>
              <option value="PREMISE" className="bg-slate-900">Premises</option>
              <option value="EVIDENCE" className="bg-slate-900">Evidence</option>
              <option value="COUNTERARGUMENT" className="bg-slate-900">Counterarguments</option>
              <option value="REBUTTAL" className="bg-slate-900">Rebuttals</option>
            </select>
          </div>

          {/* Speaker Filter — dynamic from actual result */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            <select
              value={selectedSpeakerFilter}
              onChange={(e) => setSelectedSpeakerFilter(e.target.value)}
              className="bg-transparent text-slate-200 text-xs font-medium focus:outline-none px-2 cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900">All Speakers</option>
              {analysisResult.speakers.map((speaker) => (
                <option key={speaker.id} value={speaker.id} className="bg-slate-900">
                  {speaker.name}
                </option>
              ))}
            </select>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setSelectedComponentFilter('ALL');
              setSelectedSpeakerFilter('ALL');
            }}
            icon={<RotateCcw className="w-3 h-3" />}
          >
            Reset
          </Button>
        </div>
      </div>

      {/* 5 Component Overview Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        <StatisticCard
          label="Claims"
          value={analysisResult.summary.component_counts.CLAIM}
          badge="Thesis"
          badgeColor="indigo"
          description="Central contentious assertions"
        />
        <StatisticCard
          label="Premises"
          value={analysisResult.summary.component_counts.PREMISE}
          badge="Grounds"
          badgeColor="sky"
          description="Supporting causal rationales"
        />
        <StatisticCard
          label="Evidence"
          value={analysisResult.summary.component_counts.EVIDENCE}
          badge="Empirical"
          badgeColor="emerald"
          description="Statistical or study citations"
        />
        <StatisticCard
          label="Counterarguments"
          value={analysisResult.summary.component_counts.COUNTERARGUMENT}
          badge="Attacks"
          badgeColor="amber"
          description="Objections to opponent points"
        />
        <StatisticCard
          label="Rebuttals"
          value={analysisResult.summary.component_counts.REBUTTAL}
          badge="Defense"
          badgeColor="rose"
          description="Direct responses to attacks"
        />
      </div>

      {/* Interactive Argument Graph Canvas & Side Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* React Flow Viewport */}
        <div className="lg:col-span-8 bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl relative">
          <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-2.5 bg-slate-900/60 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <Network className="w-4 h-4 text-indigo-400" />
              <span className="font-semibold text-white">Interactive Argument Graph</span>
              <span className="text-slate-600">|</span>
              <span className="text-[11px] text-slate-400">Drag nodes • Scroll to Zoom • Click to Inspect</span>
            </div>

            {/* Edge Legend */}
            <div className="hidden sm:flex items-center gap-3 text-[11px]">
              <span className="flex items-center gap-1 text-emerald-400 font-mono">
                <span className="w-2 h-0.5 bg-emerald-500 inline-block"></span> SUPPORTS
              </span>
              <span className="flex items-center gap-1 text-rose-400 font-mono">
                <span className="w-2 h-0.5 bg-rose-500 inline-block"></span> ATTACKS
              </span>
              <span className="flex items-center gap-1 text-indigo-400 font-mono">
                <span className="w-2 h-0.5 bg-indigo-500 inline-block"></span> RESPONDS_TO
              </span>
            </div>
          </div>

          <div className="w-full h-[540px] relative">
            {analysisResult.arguments.length === 0 && (
              <div className="absolute inset-0 z-10 flex flex-col items-center justify-center p-6 text-center bg-slate-950/90 space-y-3">
                <Info className="w-8 h-8 text-indigo-400" />
                <p className="text-sm font-semibold text-white">No Argument Units Detected</p>
                <p className="text-xs text-slate-400 max-w-md">
                  No distinct propositional claims or premises were extracted from this transcript.
                  Try submitting discourse containing explicit speaker assertions and premises.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigate('/analyze')}
                  icon={<RotateCcw className="w-3.5 h-3.5" />}
                >
                  Return to Analyze
                </Button>
              </div>
            )}
            <ReactFlow
              nodes={filteredNodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              className="bg-slate-950"
            >
              <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#1e293b" />
              <Controls position="bottom-left" showInteractive={false} />
            </ReactFlow>
          </div>
        </div>

        {/* Right Side: Node Inspector & Structural Reasoning Insights */}
        <div className="lg:col-span-4 space-y-6">
          {/* Node Inspector */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Selected Argument Inspector
              </span>
              {selectedArgument && (
                <span className="text-[11px] font-mono text-indigo-400">
                  {selectedArgument.id}
                </span>
              )}
            </div>

            {selectedArgument ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60 uppercase">
                    {selectedArgument.component_type}
                  </span>
                  <span className="text-xs text-slate-300 bg-slate-800/80 px-2 py-0.5 rounded">
                    {analysisResult.speakers.find((s) => s.id === selectedArgument.speaker_id)?.name}
                  </span>
                </div>

                <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800 text-xs sm:text-sm text-slate-100 font-mono leading-relaxed">
                  "{selectedArgument.text}"
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase block">Model Confidence</span>
                    <span className="font-mono font-bold text-white">
                      {(selectedArgument.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase block">Speech Turn</span>
                    <span className="font-mono font-bold text-white">
                      Turn {selectedArgument.turn_order}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-slate-500 text-center py-6">
                Click any node on the graph canvas to inspect its dialectical attributes.
              </div>
            )}
          </Card>

          {/* Structural Insights Section */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Structural Reasoning Insights
              </div>
              <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                {analysisResult.insights.length} Detected
              </span>
            </div>

            <div className="space-y-3">
              {analysisResult.insights.map((insight) => (
                <div
                  key={insight.id}
                  className={`p-3 rounded-lg border text-xs leading-relaxed space-y-1 ${insight.severity === 'WARNING'
                      ? 'bg-amber-950/20 border-amber-800/40 text-amber-200'
                      : 'bg-indigo-950/20 border-indigo-800/40 text-indigo-200'
                    }`}
                >
                  <div className="flex items-center gap-1.5 font-bold text-[10px] tracking-wider uppercase">
                    {insight.severity === 'WARNING' ? (
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    ) : (
                      <CheckCircle className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                    )}
                    <span>{insight.type.replace('_', ' ')}</span>
                  </div>
                  <p className="text-slate-300 font-normal">{insight.message}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
