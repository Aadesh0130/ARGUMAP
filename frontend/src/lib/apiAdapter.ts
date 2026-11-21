import { AnalysisResult, ComponentType, RawAnalysisResponse } from '../types';

export function adaptApiResponse(apiResponse: RawAnalysisResponse | any): AnalysisResult {
  // Count component types from arguments array
  const componentCounts: Record<ComponentType, number> = {
    CLAIM: 0,
    PREMISE: 0,
    EVIDENCE: 0,
    COUNTERARGUMENT: 0,
    REBUTTAL: 0,
    OTHER: 0,
  };
  (apiResponse.arguments || []).forEach((a: any) => {
    if (a.component_type in componentCounts) {
      componentCounts[a.component_type as ComponentType]++;
    }
  });

  // Track units per turn to dynamically space them vertically without collision
  const turnUnitCounts: Record<number, number> = {};
  const X_SPACING = 320;
  const X_OFFSET = 80;
  const Y_SPACING = 190;
  const Y_OFFSET = 80;

  const adaptedArguments = (apiResponse.arguments || []).map((a: any) => {
    const turnOrder = typeof a.turn_order === 'number' && a.turn_order > 0 ? a.turn_order : 1;
    const indexInTurn = turnUnitCounts[turnOrder] || 0;
    turnUnitCounts[turnOrder] = indexInTurn + 1;

    const deterministicPosition = {
      x: X_OFFSET + (turnOrder - 1) * X_SPACING,
      y: Y_OFFSET + indexInTurn * Y_SPACING,
    };

    return {
      ...a,
      graph_node: a.graph_node || {
        id: a.id,
        type: 'argumentNode' as const,
        position: deterministicPosition,
        data: {
          label: a.text,
          component_type: a.component_type,
          speaker_id: a.speaker_id,
          speaker_name:
            (apiResponse.speakers || []).find((s: any) => s.id === a.speaker_id)?.name ||
            'Speaker',
          confidence: a.confidence || 0.5,
          turn_order: turnOrder,
        },
      },
    };
  });

  return {
    analysis_id: apiResponse.analysis_id,
    debate_id: apiResponse.debate_id,
    status: apiResponse.status,
    model_version: apiResponse.model_version || 'v1-rule-heuristic',
    created_at: apiResponse.created_at,
    completed_at: apiResponse.completed_at,
    summary: {
      speaker_count: apiResponse.summary?.speaker_count || 0,
      turn_count: apiResponse.summary?.turn_count || 0,
      argument_count:
        apiResponse.summary?.argument_count || (apiResponse.arguments || []).length,
      relation_count:
        apiResponse.summary?.relation_count || (apiResponse.relations || []).length,
      insights_count:
        apiResponse.summary?.insights_count || (apiResponse.insights || []).length,
      component_counts: componentCounts,
    },
    speakers: apiResponse.speakers || [],
    arguments: adaptedArguments,
    relations: (apiResponse.relations || []).map((r: any) => ({
      ...r,
      graph_edge: r.graph_edge || {
        id: r.id,
        source: r.source_argument_id,
        target: r.target_argument_id,
        type: 'argumentEdge' as const,
        label: r.relation_type,
        animated: r.relation_type === 'ATTACKS',
        data: { relation_type: r.relation_type, confidence: r.confidence || 0.5 },
      },
    })),
    insights: (apiResponse.insights || []).map((ins: any, i: number) => ({
      id: ins.id || `ins_${i + 1}`,
      type: ins.type,
      severity: ins.severity,
      message: ins.message,
      related_argument_ids: ins.related_argument_ids || [],
    })),
  };
}
