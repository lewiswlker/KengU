"""
Agents
"""

from __future__ import annotations

import inspect
from enum import Enum

import dspy

from core.config import settings

from .planner_agent import PlannerAgent
from .scraper_agent import update_knowledge_base

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
    Analyze user request and route to the most appropriate agent list.

    Available agents and their responsibilities:

    1. PLANNER - Use for:
       - Study schedules, calendars, and time management
       - Assignment deadlines and due dates
       - Learning progress tracking and academic progress
       - Task planning and study planning
       - Course planning and academic planning
       Keywords: schedule, plan, progress, deadline, due, calendar, time management

    2. RAG (Retrieval-Augmented Generation) - Use for:
       - Course content and topics (what to learn)
       - Concept explanations and knowledge queries
       - Existing course materials and documents
       - Searching through stored information
       - Questions about specific courses or subjects
       Keywords: what, explain, topics, content, information, find, course materials, concept

    3. SCRAPER - Use ONLY when explicitly requested:
       - Update/refresh/sync data from external sources
       - Scrape/crawl/fetch new data
       - Must contain explicit action verbs: update, refresh, scrape, sync, fetch, crawl
       Keywords: update, refresh, scrape, sync, fetch, crawl (explicit action required)

    4. GENERAL - Use for:
       - Greetings and casual conversation
       - Off-topic queries unrelated to academics
       - General assistance not fitting other categories
       Keywords: hello, hi, joke, weather, chat

    Routing rules:
    - NEVER route to SCRAPER unless explicit update/scrape action is mentioned
    - Questions about "latest" or "recent" data should use RAG (query existing data), NOT SCRAPER
    - Progress/deadline/due date queries → PLANNER
    - Content/explanation/topic queries → RAG
    - If query has multiple intents, return multiple agents (e.g., ["rag", "planner"])
    - "What assignments" = content query → RAG (unless explicitly asking to update)
    - "When assignments due" = deadline query → PLANNER
    - "Analyze X and plan Y" → Both RAG and PLANNER
    """

    system_router_prompt: str = dspy.InputField()
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


def get_class_docstring(cls: type) -> str:
    """
    Get the docstring from a class.

    Args:
        cls: The class to extract docstring from

    Returns:
        The formatted docstring, or empty string if no docstring exists
    """
    return inspect.getdoc(cls) or ""


def get_router_system_prompt() -> str:
    """Get the system prompt for the agent router from AgentRouterSignature docstring."""
    return get_class_docstring(AgentRouterSignature)


# Initialize the global router instance
agent_router = dspy.asyncify(dspy.Predict(AgentRouterSignature))

__all__ = [
    "AgentRouter",
    "AgentRouterSignature",
    "AgentType",
    "agent_router",
    "dspy",
    "update_knowledge_base",
    "PlannerAgent",
    "get_class_docstring",
    "get_router_system_prompt",
]