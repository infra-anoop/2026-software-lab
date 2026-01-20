from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from researcher import run_research
from critic import run_audit
from models import ResearchOutput, AuditFeedback

# 1. Define the 'State' - what the agents share
class AgentState(TypedDict):
    raw_input: str
    research: ResearchOutput
    feedback: AuditFeedback
    iterations: int

# 2. Define the Nodes (The Workers)
async def researcher_node(state: AgentState):
    # If we have feedback, we'd pass it here to 'improve'
    res = await run_research(state['raw_input'])
    return {"research": res, "iterations": state.get('iterations', 0) + 1}

async def critic_node(state: AgentState):
    feedback = await run_audit(state['research'])
    return {"feedback": feedback}

# 3. Define the Router (The Decision Maker)
def should_continue(state: AgentState):
    if state['feedback'].verdict == "PASS" or state['iterations'] > 3:
        return END
    return "researcher"

# 4. Build the Graph
workflow = StateGraph(AgentState)
workflow.add_node("researcher", researcher_node)
workflow.add_node("critic", critic_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "critic")
workflow.add_conditional_edges("critic", should_continue)

app = workflow.compile()