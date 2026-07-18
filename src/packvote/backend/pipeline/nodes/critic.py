import os
import logging
from langsmith import Client
from langchain_core.prompts import PromptTemplate
from packvote.shared.schemas import CriticOutput
from packvote.backend.core.llm import get_llm
from packvote.backend.pipeline.state import TripState

logger = logging.getLogger(__name__)

class HubWrapper:
    def __init__(self):
        try:
            self.client = Client()
        except Exception:
            self.client = None

    def pull(self, owner_repo_commit: str):
        if not self.client:
            raise RuntimeError("LangSmith Client not initialized")
        # Strip tenant prefix if present for compatibility with local workspace configuration
        if owner_repo_commit.startswith("packvote/"):
            owner_repo_commit = owner_repo_commit.replace("packvote/", "", 1)
        return self.client.pull_prompt(owner_repo_commit)

hub = HubWrapper()


def critic_node(state: TripState) -> TripState:
    llm = get_llm()
    
    critic_prompt = None
    try:
        critic_prompt = hub.pull("packvote/critic-rubric:v1")
        logger.info("Pulled critic rubric from LangSmith Hub")
    except Exception as e:
        logger.warning(f"Failed to pull critic rubric from LangSmith Hub, falling back to local file. Error: {e}")
        local_path = os.path.join("prompts", "critic_rubric_v1.txt")
        with open(local_path, "r", encoding="utf-8") as f:
            template_str = f.read()
        critic_prompt = PromptTemplate.from_template(template_str)

    structured_llm = llm.with_structured_output(CriticOutput)
    chain = critic_prompt | structured_llm

    result: CriticOutput = chain.invoke({
        "recommendations": state["recommendations"],
        "aggregated": state["aggregated"],
    }, config={"metadata": {"prompt_version": "v1"}, "tags": ["v1"]})

    state["critic_score"] = result.score
    state["critic_feedback"] = result.feedback
    
    # Increment retry count in the state-saving node if a retry is needed
    if result.score < 0.7:
        state["retry_count"] += 1
        
    return state


def should_retry(state: TripState) -> str:
    if state["critic_score"] < 0.7:
        if state["retry_count"] <= 2:
            logger.info(f"Critic score {state['critic_score']} < 0.7. Retrying (attempt {state['retry_count']}/2). Feedback: {state['critic_feedback']}")
            return "retry"
        else:
            logger.warning(
                f"Trip {state['trip_id']}: accepting recommendations with score "
                f"{state['critic_score']:.2f} after 2 retries (cap reached)"
            )
            return "output"
            
    return "output"
