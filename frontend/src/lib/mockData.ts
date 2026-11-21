import { AnalysisResult } from '../types';

export const SAMPLE_TRANSCRIPT = `Speaker A: AI should be used in education because it enables personalized learning at scale.
Speaker A: A 2024 Stanford study found a 23% improvement in retention when adaptive tutoring was used.
Speaker B: However, excessive dependence on AI can reduce students' independent critical thinking.
Speaker A: This risk can be reduced through structured teacher supervision and inquiry-based assignments.
Speaker B: But teacher workloads are already too high to manage continuous algorithmic oversight.
Speaker A: Automated analytics can actually reduce administrative burden, freeing more time for mentoring.`;

export const MOCK_ANALYSIS_RESULT: AnalysisResult = {
  analysis_id: "run_mock_01h7x8z9",
  debate_id: "deb_mock_9f3a1e2b",
  status: "COMPLETED",
  model_version: "v1-baseline (Mock Demonstration)",
  created_at: "2026-09-24T14:30:00Z",
  completed_at: "2026-09-24T14:30:02Z",
  summary: {
    speaker_count: 2,
    turn_count: 6,
    argument_count: 6,
    relation_count: 5,
    insights_count: 3,
    component_counts: {
      CLAIM: 1,
      PREMISE: 2,
      EVIDENCE: 1,
      COUNTERARGUMENT: 1,
      REBUTTAL: 1,
      OTHER: 0
    }
  },
  speakers: [
    { id: "spk_a", name: "Speaker A" },
    { id: "spk_b", name: "Speaker B" }
  ],
  arguments: [
    {
      id: "arg_1",
      turn_id: "turn_1",
      speaker_id: "spk_a",
      text: "AI should be used in education",
      component_type: "CLAIM",
      confidence: 0.96,
      turn_order: 1,
      graph_node: {
        id: "arg_1",
        type: "argumentNode",
        position: { x: 320, y: 40 },
        data: {
          label: "AI should be used in education",
          component_type: "CLAIM",
          speaker_id: "spk_a",
          speaker_name: "Speaker A",
          confidence: 0.96,
          turn_order: 1
        }
      }
    },
    {
      id: "arg_2",
      turn_id: "turn_1",
      speaker_id: "spk_a",
      text: "it enables personalized learning at scale",
      component_type: "PREMISE",
      confidence: 0.92,
      turn_order: 1,
      graph_node: {
        id: "arg_2",
        type: "argumentNode",
        position: { x: 120, y: 180 },
        data: {
          label: "it enables personalized learning at scale",
          component_type: "PREMISE",
          speaker_id: "spk_a",
          speaker_name: "Speaker A",
          confidence: 0.92,
          turn_order: 1
        }
      }
    },
    {
      id: "arg_3",
      turn_id: "turn_2",
      speaker_id: "spk_a",
      text: "A 2024 Stanford study found a 23% improvement in retention",
      component_type: "EVIDENCE",
      confidence: 0.95,
      turn_order: 2,
      graph_node: {
        id: "arg_3",
        type: "argumentNode",
        position: { x: 40, y: 320 },
        data: {
          label: "A 2024 Stanford study found a 23% improvement in retention",
          component_type: "EVIDENCE",
          speaker_id: "spk_a",
          speaker_name: "Speaker A",
          confidence: 0.95,
          turn_order: 2
        }
      }
    },
    {
      id: "arg_4",
      turn_id: "turn_3",
      speaker_id: "spk_b",
      text: "excessive dependence on AI can reduce students' independent critical thinking",
      component_type: "COUNTERARGUMENT",
      confidence: 0.89,
      turn_order: 3,
      graph_node: {
        id: "arg_4",
        type: "argumentNode",
        position: { x: 520, y: 180 },
        data: {
          label: "excessive dependence on AI can reduce students' independent critical thinking",
          component_type: "COUNTERARGUMENT",
          speaker_id: "spk_b",
          speaker_name: "Speaker B",
          confidence: 0.89,
          turn_order: 3
        }
      }
    },
    {
      id: "arg_5",
      turn_id: "turn_4",
      speaker_id: "spk_a",
      text: "This risk can be reduced through structured teacher supervision",
      component_type: "REBUTTAL",
      confidence: 0.91,
      turn_order: 4,
      graph_node: {
        id: "arg_5",
        type: "argumentNode",
        position: { x: 520, y: 320 },
        data: {
          label: "This risk can be reduced through structured teacher supervision",
          component_type: "REBUTTAL",
          speaker_id: "spk_a",
          speaker_name: "Speaker A",
          confidence: 0.91,
          turn_order: 4
        }
      }
    },
    {
      id: "arg_6",
      turn_id: "turn_5",
      speaker_id: "spk_b",
      text: "teacher workloads are already too high to manage continuous oversight",
      component_type: "COUNTERARGUMENT",
      confidence: 0.87,
      turn_order: 5,
      graph_node: {
        id: "arg_6",
        type: "argumentNode",
        position: { x: 740, y: 320 },
        data: {
          label: "teacher workloads are already too high to manage continuous oversight",
          component_type: "COUNTERARGUMENT",
          speaker_id: "spk_b",
          speaker_name: "Speaker B",
          confidence: 0.87,
          turn_order: 5
        }
      }
    }
  ],
  relations: [
    {
      id: "rel_1",
      source_argument_id: "arg_2",
      target_argument_id: "arg_1",
      relation_type: "SUPPORTS",
      confidence: 0.94,
      graph_edge: {
        id: "rel_1",
        source: "arg_2",
        target: "arg_1",
        type: "argumentEdge",
        label: "SUPPORTS",
        data: { relation_type: "SUPPORTS", confidence: 0.94 }
      }
    },
    {
      id: "rel_2",
      source_argument_id: "arg_3",
      target_argument_id: "arg_2",
      relation_type: "SUPPORTS",
      confidence: 0.96,
      graph_edge: {
        id: "rel_2",
        source: "arg_3",
        target: "arg_2",
        type: "argumentEdge",
        label: "SUPPORTS",
        data: { relation_type: "SUPPORTS", confidence: 0.96 }
      }
    },
    {
      id: "rel_3",
      source_argument_id: "arg_4",
      target_argument_id: "arg_1",
      relation_type: "ATTACKS",
      confidence: 0.91,
      graph_edge: {
        id: "rel_3",
        source: "arg_4",
        target: "arg_1",
        type: "argumentEdge",
        label: "ATTACKS",
        animated: true,
        data: { relation_type: "ATTACKS", confidence: 0.91 }
      }
    },
    {
      id: "rel_4",
      source_argument_id: "arg_5",
      target_argument_id: "arg_4",
      relation_type: "RESPONDS_TO",
      confidence: 0.89,
      graph_edge: {
        id: "rel_4",
        source: "arg_5",
        target: "arg_4",
        type: "argumentEdge",
        label: "RESPONDS_TO",
        data: { relation_type: "RESPONDS_TO", confidence: 0.89 }
      }
    },
    {
      id: "rel_5",
      source_argument_id: "arg_6",
      target_argument_id: "arg_5",
      relation_type: "ATTACKS",
      confidence: 0.88,
      graph_edge: {
        id: "rel_5",
        source: "arg_6",
        target: "arg_5",
        type: "argumentEdge",
        label: "ATTACKS",
        animated: true,
        data: { relation_type: "ATTACKS", confidence: 0.88 }
      }
    }
  ],
  insights: [
    {
      id: "ins_1",
      type: "DIRECT_CLASH",
      severity: "INFO",
      message: "Direct dialectical clash detected: Speaker B countered Speaker A's central claim, which was subsequently defended by Rebuttal (arg_5).",
      related_argument_ids: ["arg_1", "arg_4", "arg_5"]
    },
    {
      id: "ins_2",
      type: "UNANSWERED_COUNTERARGUMENT",
      severity: "WARNING",
      message: "Speaker B's final counterargument ('teacher workloads are already too high...') has no detected response in the recorded debate turns.",
      related_argument_ids: ["arg_6"]
    },
    {
      id: "ins_3",
      type: "UNSUPPORTED_CLAIM",
      severity: "INFO",
      message: "Central claim ('AI should be used in education') is well-supported by 1 premise and backed by empirical evidence (Stanford study).",
      related_argument_ids: ["arg_1", "arg_2", "arg_3"]
    }
  ]
};
