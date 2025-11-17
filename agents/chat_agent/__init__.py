import asyncio
from collections.abc import AsyncGenerator

from agents import AgentType, PlannerAgent, settings, update_knowledge_base
from agents.llm import LLM
from agents.planner_agent import LLMConfig
from agents.rag_agent import answer_with_rag
from dao.user import UserDAO
from models import ProgressQuery, ProgressResult
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
        self,
        user_request: str,
        user_id: int | None = None,
        user_email: str | None = None,
        messages: list | None = None,
        selected_course_ids: list[int] | None = None,
    ) -> AsyncGenerator[str]:
        """
        Route request to appropriate agent and generate response

        Args:
            user_request: User's request text
            user_id: Optional user ID to fetch credentials from database
            user_email: Optional user email to fetch credentials from database
            messages: Optional conversation history
            selected_course_ids: Optional list of pre-selected course IDs to skip LLM filtering

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
        rag_retrieval_results = None  # Store RAG retrieval results
        
        for agent_type in agent_types:
            agent_type = AgentType.RAG
            if agent_type == AgentType.SCRAPER:
                agent_tasks.append(
                    asyncio.create_task(self._handle_scraper_agent(user_id=user_id, user_email=user_email))
                )
            elif agent_type == AgentType.PLANNER:
                agent_tasks.append(asyncio.create_task(self._handle_planner_agent(user_request, user_id=user_id)))
            elif agent_type == AgentType.RAG:
                agent_tasks.append(asyncio.create_task(self._handle_rag_agent(user_request, user_id=user_id, selected_course_ids=selected_course_ids)))
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
                        # Extract RAG retrieval results if this is RAG agent
                        print("Aaaaaaaaaaaa",agent_types[i],result)
                        agent_types[i] = AgentType.RAG
                        if agent_types[i] == AgentType.RAG and isinstance(result, dict):
                            rag_data = result.get('data', {})
                            print("Bbbbbbbbbaaaaaa",rag_data)
                            if rag_data.get('retrieval_results'):
                                rag_retrieval_results = rag_data['retrieval_results']
                        
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
                                {
                                    "role": "system",
                                    "content": f"Agent {agent_types[i]} 结果: {str(result)}",
                                }
                            )
            except Exception as e:
                yield f"执行代理任务时出错: {str(e)}"
                return
        
        # Send retrieval results first (before LLM response)
        if rag_retrieval_results:
            print("aaaaaaaaaaaaaaaaaaaa",rag_retrieval_results)
            import json
            from dataclasses import asdict
            sources = [asdict(result) for result in rag_retrieval_results]
            yield f"__SOURCES__:{json.dumps(sources, ensure_ascii=False)}__END_SOURCES__"

        # Generate response using LLM with all context
        messages.append({"role": "user", "content": user_request})

        async for chunk in self.llm.static_chat_stream(model_alias=settings.LLM_MODEL_NAME, messages=messages):
            yield chunk

    async def _handle_scraper_agent(self, user_id: int | None = None, user_email: str | None = None) -> dict | None:
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
            return {
                "success": False,
                "error": "无法获取用户信息，请提供有效的 user_id 或 user_email 参数。",
            }

        try:
            # Run synchronous update_knowledge_base in thread pool to avoid blocking
            scrape_result = await asyncio.to_thread(
                update_knowledge_base,
                user_id=user_info["id"],
                user_email=user_info["user_email"],
                user_password=user_info["pwd"],
                headless=True,
                verbose=False,
            )

            return {
                "success": True,
                "data": scrape_result,
                "summary": f"成功更新知识库: {scrape_result}",
            }
        except Exception as e:
            return {"success": False, "error": f"更新知识库时出错: {str(e)}"}

    async def _handle_planner_agent(self, user_request: str, user_id: int | None = None) -> dict | None:
        """
        Handle requests routed to the planner agent

        Returns:
            dict: Result with 'success', 'data', and optional 'error' keys
        """
        llm_config = LLMConfig(
            model=settings.LLM_MODEL_NAME,
            base_url=settings.LLM_API_ENDPOINT,
            api_key=settings.LLM_API_KEY,
        )
        planner_agent = PlannerAgent(llm_config=llm_config)
        progress_query = ProgressQuery(user_id=user_id)
        progress_result: ProgressResult = await asyncio.to_thread(planner_agent.progress, query=progress_query)

        # Convert ProgressResult to readable text summary
        summary_text = "学习进度统计:\n"
        summary_text += f"- 已完成: {progress_result.completed} 个任务\n"
        summary_text += f"- 待完成: {progress_result.pending} 个任务\n"
        summary_text += f"- 总计: {progress_result.total} 个任务\n"

        if progress_result.details:
            for detail in progress_result.details:
                detail_type = detail.get("type")

                if detail_type == "overall_stats":
                    completion_rate = detail.get("completion_rate", 0)
                    summary_text += f"- 完成率: {completion_rate}%\n"

                elif detail_type == "study_activity":
                    total_sessions = detail.get("total_sessions", 0)
                    total_hours = detail.get("total_study_hours", 0)
                    avg_minutes = detail.get("average_session_minutes", 0)
                    active_days = detail.get("active_days", 0)
                    period_days = detail.get("period_days", 0)

                    summary_text += "\n学习活动统计:\n"
                    summary_text += f"- 总学习时长: {total_hours} 小时\n"
                    summary_text += f"- 学习场次: {total_sessions} 次\n"
                    summary_text += f"- 平均每次: {avg_minutes} 分钟\n"
                    summary_text += f"- 活跃天数: {active_days}/{period_days} 天\n"

                elif detail_type == "course_progress":
                    total_courses = detail.get("total_courses", 0)
                    courses = detail.get("courses", [])
                    summary_text += f"\n课程进度 ({total_courses}门课程):\n"
                    for course in courses:
                        course_name = course.get("course_name", "未知课程")
                        progress = course.get("progress", 0)
                        summary_text += f"- {course_name}: {progress}%\n"

                elif detail_type == "upcoming_assignments":
                    count = detail.get("count", 0)
                    assignments = detail.get("assignments", [])
                    if count > 0:
                        summary_text += f"\n近期待办作业 ({count}个):\n"
                        for assignment in assignments:
                            title = assignment.get("title", "未知作业")
                            due_date = assignment.get("due_date", "无截止日期")
                            summary_text += f"- {title} (截止: {due_date})\n"

                elif detail_type == "suggestions":
                    recommendations = detail.get("recommendations", [])
                    if recommendations:
                        summary_text += "\n学习建议:\n"
                        for suggestion in recommendations:
                            summary_text += f"- {suggestion}\n"

        return {
            "success": True,
            "data": progress_result,
            "summary": summary_text.strip(),
        }

    async def _handle_rag_agent(
        self, 
        user_request: str, 
        user_id: int | None = None, 
        selected_course_ids: list[int] | None = None
        ) -> dict | None:
        """
        Handle requests routed to the RAG agent

        Returns:
            dict: Result with 'success', 'data', and optional 'error' keys
        """
        if user_id is None:
            return {
                "success": False,
                "error": "RAG代理需要有效的 user_id 参数。",
            }

        try:
            rag_result = await asyncio.to_thread(
                answer_with_rag,
                query=user_request,
                user_id=user_id,
                selected_course_ids=selected_course_ids
            )

            # Structure retrieval results for context
            retrieval_summary = ""
            if rag_result.get("retrieval_results"):
                retrieval_summary = "检索到的相关内容:\n"
                for i, result in enumerate(rag_result["retrieval_results"], 1):
                    retrieval_summary += f"{i}. 相关度: {result.relevance_score:.2f}\n"
                    retrieval_summary += f"   来源: {result.source_url}\n"
                    retrieval_summary += f"   内容: {result.text}\n\n"

            return {
                "success": True,
                "data": rag_result,
                "summary": retrieval_summary.strip(),
            }
        except Exception as e:
            return {"success": False, "error": f"RAG检索时出错: {str(e)}"}