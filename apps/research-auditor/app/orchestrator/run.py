from typing import TypedDict, Any
import logfire
from langgraph.graph import StateGraph, END
from app.agents.researcher import run_research
from app.agents.critic import run_audit
from app.agents.models import ResearchOutput, AuditFeedback
from app.db.client import get_supabase_client
from app.db.null_repo import NullRepo
from app.db.repo import RunRepo
from app.db.supabase_repo import SupabaseRepo

_repo: RunRepo | None = None


def get_repo() -> RunRepo:
    """Get repo instance: SupabaseRepo if shared client is configured, else NullRepo."""
    global _repo
    if _repo is None:
        client = get_supabase_client()
        _repo = SupabaseRepo(client) if client else NullRepo()
    return _repo

# 1. Define the 'State' - what the agents share
class AgentState(TypedDict, total=False):
    raw_input: str
    research: ResearchOutput
    feedback: AuditFeedback
    iterations: int
    max_iterations: int
    run_id: str
    step: int

# 2. Define the Nodes (The Workers)
async def researcher_node(state: AgentState):
    """Researcher node with turn tracking."""
    run_id = state.get('run_id')
    step = state.get('step', 1)
    input_data = {"raw_input": state['raw_input']}
    
    try:
        res = await run_research(state['raw_input'])
        output_data = res.model_dump() if hasattr(res, 'model_dump') else res
        
        # Track turn if run_id exists
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="researcher", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "researcher", input_data, output_data, True, None)
        
        result = {
            "research": res,
            "iterations": state.get('iterations', 0) + 1
        }
        if run_id:
            result["step"] = step + 1
        return result
    except Exception as e:
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="researcher", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "researcher", input_data, None, False, str(e))
        raise

async def critic_node(state: AgentState):
    """Critic node with turn tracking."""
    run_id = state.get('run_id')
    step = state.get('step', 1)
    input_data = state['research'].model_dump() if hasattr(state['research'], 'model_dump') else state['research']
    
    try:
        feedback = await run_audit(state['research'])
        output_data = feedback.model_dump() if hasattr(feedback, 'model_dump') else feedback
        
        # Track turn if run_id exists
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="critic", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "critic", input_data, output_data, True, None)
        
        result = {"feedback": feedback}
        if run_id:
            result["step"] = step + 1
        return result
    except Exception as e:
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="critic", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "critic", input_data, None, False, str(e))
        raise

# 3. Define the Router (The Decision Maker)
def should_continue(state: AgentState):
    max_it = state.get('max_iterations', 3)
    if state['feedback'].verdict == "PASS" or state['iterations'] >= max_it:
        return END
    return "researcher"

# 4. Build the Graph
workflow = StateGraph(AgentState)
workflow.add_node("researcher", researcher_node)
workflow.add_node("critic", critic_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "critic")
workflow.add_conditional_edges("critic", should_continue)

_compiled_app = workflow.compile()

# 5. Wrapper function with run lifecycle management
async def run_workflow(initial_input: dict[str, Any]) -> dict[str, Any]:
    """Execute workflow with run/turn persistence."""
    repo = get_repo()
    
    # Extract topic from input (use raw_input as topic)
    topic = initial_input.get('raw_input', 'unknown')
    with logfire.span("repo.create_run", topic=topic):
        run_id = repo.create_run(topic)
    
    # Add run_id and step to initial state
    state_with_run = {
        **initial_input,
        "run_id": run_id,
        "step": 1
    }
    
    try:
        with logfire.span("langgraph.ainvoke", run_id=run_id):
            final_state = await _compiled_app.ainvoke(state_with_run)
        
        # Prepare final output dict
        final_output = {
            "research": final_state['research'].model_dump() if hasattr(final_state['research'], 'model_dump') else final_state['research'],
            "feedback": final_state['feedback'].model_dump() if hasattr(final_state['feedback'], 'model_dump') else final_state['feedback'],
            "iterations": final_state['iterations']
        }
        
        with logfire.span("repo.finalize_run", run_id=run_id, status="completed"):
            repo.finalize_run(run_id, "completed", final_output=final_output)
        return final_state
    except Exception as e:
        with logfire.span("repo.finalize_run", run_id=run_id, status="failed"):
            repo.finalize_run(run_id, "failed", error=str(e))
        raise

# Compiled LangGraph workflow (direct ainvoke); use run_workflow for persistence.
workflow_app = _compiled_app