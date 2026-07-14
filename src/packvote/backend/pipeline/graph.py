from langgraph.graph import StateGraph, END
from packvote.backend.pipeline.state import TripState
from packvote.backend.pipeline.nodes.aggregate import aggregate_node
from packvote.backend.pipeline.nodes.retrieve import retrieve_node
from packvote.backend.pipeline.nodes.recommend import recommend_node
from packvote.backend.pipeline.nodes.critic import critic_node, should_retry

def build_graph():
    graph = StateGraph(TripState)

    # Add all nodes
    graph.add_node("aggregate", aggregate_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("recommend", recommend_node)
    graph.add_node("critic", critic_node)

    # Wire nodes with direct and conditional edges
    graph.set_entry_point("aggregate")
    graph.add_edge("aggregate", "retrieve")
    graph.add_edge("retrieve", "recommend")
    graph.add_edge("recommend", "critic")
    
    graph.add_conditional_edges(
        "critic",
        should_retry,
        {"retry": "recommend", "output": END}
    )

    return graph.compile()

pipeline = build_graph()
