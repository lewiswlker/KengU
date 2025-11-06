import asyncio
from collections.abc import AsyncGenerator

from agents import AgentType
from agents.llm import LLM
from dao.user import UserDAO
from rag_scraper.scraper import RAGScraper


class ChatAgent:
    def __init__(self):
        self.llm = LLM()
        self.user_dao = UserDAO()
        self.agent_tools = {
            "planner": None,
            "scraper": None,
            "rag": None,
        }

    def _initialize_scraper(self, email: str, password: str):
        """Initialize RAGScraper with user credentials"""
        self.agent_tools["scraper"] = RAGScraper(
            email=email, password=password, headless=True, verbose=False, parallel_workers=1
        )

    async def chat(
        self, user_request: str, user_id: int | None = None, user_email: str | None = None, messages: list | None = None
    ) -> AsyncGenerator[str]:
        """
        Route request to appropriate agent and generate response

        Args:
            user_request: User's request text
            user_id: Optional user ID to fetch credentials from database
            user_email: Optional user email to fetch credentials from database
            messages: Optional conversation history

        Yields:
            Response text chunks
        """
        if messages is None:
            messages = []

        # Route to determine which agents to use
        agent_types = await self.llm.route(user_request)
        if not agent_types:
            yield "无法确定合适的代理类型。"
            return

        # Collect agent tasks
        agent_tasks = []
        for agent_type in agent_types:
            if agent_type == AgentType.SCRAPER:
                agent_tasks.append(self._handle_scraper_agent(user_request, user_id=user_id, user_email=user_email))
            elif agent_type == AgentType.PLANNER:
                agent_tasks.append(self._handle_planner_agent(user_request))
            elif agent_type == AgentType.RAG:
                agent_tasks.append(self._handle_rag_agent(user_request))
            # AgentType.GENERAL doesn't need a specific handler

        # Execute all agent tasks concurrently
        if agent_tasks:
            try:
                # Gather all results from different agents
                agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)

                # Process results and add to message context
                for i, result in enumerate(agent_results):
                    if isinstance(result, Exception):
                        # Handle exceptions from agent tasks
                        yield f"Agent {agent_types[i]} 执行失败: {str(result)}\n"
                    elif result is not None:
                        # Add successful agent results to context
                        if isinstance(result, dict):
                            # Structured result
                            messages.append(
                                {
                                    "role": "system",
                                    "content": f"Agent {agent_types[i]} 结果: {result.get('summary', str(result))}",
                                }
                            )
                        else:
                            # Plain text result
                            messages.append(
                                {"role": "system", "content": f"Agent {agent_types[i]} 结果: {str(result)}"}
                            )
            except Exception as e:
                yield f"执行代理任务时出错: {str(e)}"
                return

        # Generate response using LLM with all context
        if not messages:
            messages = [{"role": "user", "content": user_request}]

        async for chunk in self.llm.static_chat_stream(model_alias="default", messages=messages):
            yield chunk

    async def _handle_scraper_agent(
        self, user_request: str, user_id: int | None = None, user_email: str | None = None
    ) -> dict | None:
        """
        Handle requests routed to the scraper agent

        Returns:
            dict: Result with 'success', 'data', and optional 'error' keys
        """
        # Get user info from database
        user_info = None
        if user_id is not None:
            user_info = self.user_dao.find_by_id(user_id)
        elif user_email is not None:
            user_info = self.user_dao.find_by_email(user_email)

        if user_info is None:
            return {"success": False, "error": "无法获取用户信息，请提供有效的 user_id 或 user_email 参数。"}

        # Initialize scraper with user credentials
        if self.agent_tools["scraper"] is None:
            self._initialize_scraper(email=user_info["user_email"], password=user_info["pwd"])

        # Execute scraper
        try:
            # Run synchronous scrape_all in thread pool to avoid blocking
            scrape_result = await asyncio.to_thread(self.agent_tools["scraper"].scrape_all)

            return {"success": True, "data": scrape_result, "summary": f"成功抓取数据: {scrape_result}"}
        except Exception as e:
            return {"success": False, "error": f"抓取数据时出错: {str(e)}"}

    async def _handle_planner_agent(self, user_request: str) -> dict | None:
        """
        Handle requests routed to the planner agent

        Returns:
            dict: Result with 'success', 'data', and optional 'error' keys
        """
        # TODO: Implement planner agent logic
        return {"success": True, "data": "Planner agent not yet implemented", "summary": "规划代理尚未实现"}

    async def _handle_rag_agent(self, user_request: str) -> dict | None:
        """
        Handle requests routed to the RAG agent

        Returns:
            dict: Result with 'success', 'data', and optional 'error' keys
        """
        # TODO: Implement RAG agent logic
        return {"success": True, "data": "RAG agent not yet implemented", "summary": "RAG代理尚未实现"}
