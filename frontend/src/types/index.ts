/**
 * ARGUMAP — Core TypeScript Domain Models
 * Aligned with docs/DATA_SCHEMA.md and docs/API_CONTRACT.md
 */

export type ComponentType =
  | 'CLAIM'
  | 'PREMISE'
  | 'EVIDENCE'
  | 'COUNTERARGUMENT'
  | 'REBUTTAL'
  | 'OTHER';

export type RelationType =
  | 'SUPPORTS'
  | 'ATTACKS'
  | 'RESPONDS_TO'
  | 'NO_RELATION';

export type DebateStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface Speaker {
  id: string;
  debate_id?: string;
  name: string;
  created_at?: string;
}

export interface Turn {
  id: string;
  debate_id?: string;
  speaker_id: string;
  speaker_name?: string;
  turn_order: number;
  text: string;
  created_at?: string;
}

export interface ArgumentNodeData extends Record<string, unknown> {
  label: string;
  component_type: ComponentType;
  speaker_id: string;
  speaker_name: string;
  confidence: number;
  turn_order: number;
  unit_index?: number;
}

export interface ArgumentGraphNode {
  id: string;
  type: 'argumentNode';
  position: { x: number; y: number };
  data: ArgumentNodeData;
}

export interface Argument {
  id: string;
  debate_id?: string;
  turn_id: string;
  speaker_id: string;
  text: string;
  component_type: ComponentType;
  confidence: number;
  turn_order: number;
  start_char?: number;
  end_char?: number;
  graph_node?: ArgumentGraphNode;
}

export interface RelationEdgeData extends Record<string, unknown> {
  relation_type: RelationType;
  confidence: number;
}

export interface RelationGraphEdge {
  id: string;
  source: string;
  target: string;
  type: 'argumentEdge';
  label: RelationType;
  animated?: boolean;
  data: RelationEdgeData;
}

export interface Relation {
  id: string;
  debate_id?: string;
  source_argument_id: string;
  target_argument_id: string;
  relation_type: RelationType;
  confidence: number;
  graph_edge?: RelationGraphEdge;
}

export type InsightType =
  | 'UNSUPPORTED_CLAIM'
  | 'UNANSWERED_COUNTERARGUMENT'
  | 'DIRECT_CLASH'
  | 'ORPHAN_EVIDENCE';

export type InsightSeverity = 'INFO' | 'WARNING' | 'ALERT';

export interface StructuralInsight {
  id: string;
  type: InsightType;
  severity: InsightSeverity;
  message: string;
  related_argument_ids: string[];
}

export interface Debate {
  id: string;
  title: string;
  raw_transcript: string;
  status: DebateStatus;
  created_at: string;
  updated_at?: string;
  speakers?: Speaker[];
  turns?: Turn[];
}

export interface AnalysisSummary {
  speaker_count: number;
  turn_count: number;
  argument_count: number;
  relation_count: number;
  insights_count: number;
  component_counts: Record<ComponentType, number>;
}

export interface AnalysisResult {
  analysis_id: string;
  debate_id: string;
  status: DebateStatus;
  model_version: string;
  created_at: string;
  completed_at?: string;
  summary: AnalysisSummary;
  speakers: Speaker[];
  arguments: Argument[];
  relations: Relation[];
  insights: StructuralInsight[];
}

export interface RawAnalysisResponse {
  analysis_id: string;
  debate_id: string;
  status: DebateStatus;
  message?: string;
  model_version: string;
  created_at: string;
  completed_at?: string;
  summary: {
    speaker_count: number;
    turn_count: number;
    argument_count: number;
    relation_count: number;
    insights_count: number;
    component_counts?: Record<string, number>;
  };
  speakers: Speaker[];
  arguments: Argument[];
  relations: Relation[];
  insights: StructuralInsight[];
  [key: string]: unknown;
}
