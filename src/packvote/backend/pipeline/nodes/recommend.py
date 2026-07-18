import os
import logging
from langsmith import Client
from langchain_core.prompts import PromptTemplate
from packvote.shared.schemas import RecommendationsOutput
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


def recommend_node(state: TripState) -> TripState:
    llm = get_llm()
    version = state["prompt_version"]

    prompt = None
    # Defensive hub.pull with fallback to local file
    try:
        prompt = hub.pull(f"packvote/recommendation-prompt:{version}")
        logger.info(f"Pulled recommendation prompt version {version} from LangSmith Hub")
    except Exception as e:
        logger.warning(f"Failed to pull recommendation prompt version {version} from LangSmith Hub, falling back to local file. Error: {e}")
        local_path = os.path.join("prompts", f"recommendation_{version}.txt")
        if not os.path.exists(local_path):
            local_path = os.path.join("prompts", "recommendation_v1.txt")
        
        with open(local_path, "r", encoding="utf-8") as f:
            template_str = f.read()
        
        prompt = PromptTemplate.from_template(template_str)

    structured_llm = llm.with_structured_output(RecommendationsOutput)
    chain = prompt | structured_llm

    result: RecommendationsOutput = chain.invoke({
        "top_destinations": state["aggregated"].get("top_destinations", []),
        "budget_sweet_spot": state["aggregated"].get("budget_sweet_spot", 15000),
        "vibe_overlap": state["aggregated"].get("vibe_overlap", []),
        "date_conflicts": state["aggregated"].get("date_conflicts", []),
        "retrieved_destinations": state["retrieved_destinations"],
        "critic_feedback": state.get("critic_feedback", ""),
    }, config={"metadata": {"prompt_version": version}, "tags": [version]})

    state["recommendations"] = [r.model_dump() for r in result.recommendations]
    return state

