from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from models import GraphState
from utils import router_function, check_inferred_output
from nodes import run_test_case_analysis, correctness_checking, misunderstanding_fixing, retrieval_agent, planning_agent, coding_agent, executor_agent, debugging_agent, human_feedback, next_plan

workflow = StateGraph(GraphState)

# defining the nodes
workflow.add_node("initial_test_case_analysis", run_test_case_analysis)
workflow.add_node("correctness_checking", correctness_checking)
workflow.add_node("misunderstanding_fixing", misunderstanding_fixing)
workflow.add_node("retrieval_agent", retrieval_agent)
workflow.add_node("planning_agent", planning_agent)
workflow.add_node("coding_agent", coding_agent)
workflow.add_node("executor_agent", executor_agent)
workflow.add_node("next_plan", next_plan)
workflow.add_node("debugging_agent", debugging_agent)
workflow.add_node("human_feedback", human_feedback)

# build graph
workflow.add_edge(START,"initial_test_case_analysis")
workflow.add_edge("initial_test_case_analysis", "correctness_checking")
workflow.add_conditional_edges(
    "correctness_checking",
    check_inferred_output,
    {
        "misunderstanding_present":"misunderstanding_fixing",
        "proceed":"retrieval_agent"
    }
    
)
workflow.add_edge("misunderstanding_fixing", "correctness_checking")
workflow.add_edge("retrieval_agent", "planning_agent")
workflow.add_edge("planning_agent", "coding_agent")
workflow.add_edge("coding_agent", "executor_agent")
workflow.add_conditional_edges(
    "executor_agent",
    router_function,
    {
        "end": END,
        "next_plan": "next_plan",
        "debug": "debugging_agent",
        "human_feedback": "human_feedback"
    }
)
workflow.add_edge("next_plan", "coding_agent")
workflow.add_edge("human_feedback", "debugging_agent")
workflow.add_edge("debugging_agent", "coding_agent")

memory = MemorySaver()

app = workflow.compile(checkpointer = memory, interrupt_before=["human_feedback"])
