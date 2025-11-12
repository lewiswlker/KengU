"""
Agents
"""

from __future__ import annotations

from enum import Enum

import dspy

from core.config import settings

from .scraper_agent import update_knowledge_base
from .planner_agent import PlannerAgent

# Configure DSPy with LLM settings
dspy.configure(
    lm=dspy.LM(
        # if using GLM models, prefix the model name with "openai/"
        "openai/" + settings.LLM_MODEL_NAME,
        api_base=settings.LLM_API_ENDPOINT,
        api_key=settings.LLM_API_KEY,
        temperature=0,
        timeout=120,
    ),
    async_mode=True,
    async_max_workers=4,
)


# Define available agent types
class AgentType(str, Enum):
    """Available agent types in the system"""

    PLANNER = "planner"
    SCRAPER = "scraper"
    RAG = "rag"
    GENERAL = "general"


class AgentRouterSignature(dspy.Signature):
    """
    Analyze user request and route to the most appropriate agent.

    Available agents:
    - planner: For task planning, course scheduling, and academic planning
    - scraper: For web scraping, data extraction from Moodle or exam databases
    - rag: For retrieval-augmented generation tasks involving document retrieval
    - general: For general queries and tasks that don't fit other categories
    """

    user_request: str = dspy.InputField(desc="The user's request or query that needs to be processed")
    agent_type: list[AgentType] = dspy.OutputField(
        desc="List of agent types best suited to handle this request (can be multiple agents)"
    )


# Define Agent Router Module
class AgentRouter(dspy.Module):
    """
    Router module that selects the appropriate agent based on user request.
    Uses DSPy's ChainOfThought for reasoning about agent selection.
    """

    def __init__(self):
        super().__init__()
        self.route_agent = dspy.asyncify(dspy.Predict(AgentRouterSignature))

    def forward(self, user_request: str):
        """
        Route the user request to the appropriate agent.

        Args:
            user_request: The user's query or task description

        Returns:
            dspy.Prediction containing agent_type and reasoning
        """
        result = self.route_agent(user_request=user_request)
        return result


# Initialize the global router instance
agent_router = dspy.asyncify(dspy.Predict(AgentRouterSignature))

__all__ = [
    "AgentRouter",
    "AgentRouterSignature",
    "AgentType",
    "agent_router",
    "dspy",
    "update_knowledge_base",
    'PlannerAgent'
]
