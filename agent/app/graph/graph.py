from langgraph.graph import StateGraph, START, END

from graph.state import TravelState
from graph.nodes import (
    place_search_node,
    schedule_builder_node,
    validate_schedule_node,
    save_schedule_node,
    should_retry_or_save,
)

_builder = StateGraph(TravelState)

_builder.add_node("place_search",       place_search_node)
_builder.add_node("schedule_builder",   schedule_builder_node)
_builder.add_node("validate_schedule",  validate_schedule_node)
_builder.add_node("save_schedule",      save_schedule_node)

_builder.add_edge(START,              "place_search")
_builder.add_edge("place_search",     "schedule_builder")
_builder.add_edge("schedule_builder", "validate_schedule")

# 검증 통과 → 저장, 실패 → 재생성 (최대 2회)
_builder.add_conditional_edges(
    "validate_schedule",
    should_retry_or_save,
    {"retry": "schedule_builder", "save": "save_schedule"},
)

_builder.add_edge("save_schedule", END)

travel_graph = _builder.compile()
