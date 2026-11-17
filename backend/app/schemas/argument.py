"""Pydantic Schemas for Argument Units and Relations."""

from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

ComponentType = Literal[
    "CLAIM",
    "PREMISE",
    "EVIDENCE",
    "COUNTERARGUMENT",
    "REBUTTAL",
    "OTHER",
]

RelationType = Literal[
    "SUPPORTS",
    "ATTACKS",
    "RESPONDS_TO",
    "NO_RELATION",
]


class ArgumentGraphNodeData(BaseModel):
    label: str
    component_type: ComponentType
    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = None
    confidence: float
    turn_order: int


class ArgumentGraphNode(BaseModel):
    id: str
    type: str = "argumentNode"
    position: Dict[str, float] = {"x": 0.0, "y": 0.0}
    data: ArgumentGraphNodeData


class ArgumentSchema(BaseModel):
    id: str
    turn_id: str
    speaker_id: str
    text: str
    component_type: ComponentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    turn_order: int
    start_char: Optional[int] = 0
    end_char: Optional[int] = 0
    graph_node: Optional[ArgumentGraphNode] = None

    model_config = ConfigDict(from_attributes=True)


class RelationGraphEdgeData(BaseModel):
    relation_type: RelationType
    confidence: float


class RelationGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str = "argumentEdge"
    label: RelationType
    animated: Optional[bool] = False
    data: RelationGraphEdgeData


class RelationSchema(BaseModel):
    id: str
    source_argument_id: str
    target_argument_id: str
    relation_type: RelationType
    confidence: float = Field(..., ge=0.0, le=1.0)
    graph_edge: Optional[RelationGraphEdge] = None

    model_config = ConfigDict(from_attributes=True)
