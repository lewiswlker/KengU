from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from agents import AgentType, agent_router, get_router_system_prompt
from core.config import settings


class LLM:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=settings.LLM_API_ENDPOINT,
            api_key=settings.LLM_API_KEY,
        )

    async def chat(self, model_alias: str, messages: list) -> str:
        response = await self.client.chat.completions.create(
            model=model_alias,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content

    async def route(self, user_request: str) -> list[AgentType]:
        """
        Route the user request to the appropriate agent type.
        Args:
            user_request (str): The user's request or query.
        Returns:
            str: The type of agent best suited to handle the request.
        """
        result = await agent_router(system_router_prompt=get_router_system_prompt(), user_request=user_request)
        return result.agent_type

    @staticmethod
    async def static_chat_stream(model_alias: str, messages: list) -> AsyncGenerator[str]:
        """
        Chat stream for a specific model.
        Args:
            model_alias (str): The model alias to use for the chat.
            messages (list): The list of messages in the chat format.
        Yields:
            AsyncGenerator[str]: An asynchronous generator yielding chat response chunks.
        """
        client = AsyncOpenAI(
            base_url=settings.LLM_API_ENDPOINT,
            api_key=settings.LLM_API_KEY,
        )
        stream = await client.chat.completions.create(
            model=model_alias,
            messages=messages,
            stream=True,
            temperature=0.7,
        )
        full_response = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content
