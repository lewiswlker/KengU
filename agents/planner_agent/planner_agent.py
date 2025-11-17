# python
"""
planner_agent.py - PlannerAgent 核心实现（保留原有数据结构）
===========================================================

功能：本学期课程规划和复习计划生成（基于 RAG + LLM 架构）

核心特点：
1. 完整的 RAG 架构实现（检索 + 增强 + 生成）
2. LLM 配置灵活，支持本地模型（Ollama, vLLM, 自定义 API）
3. 专注于本学期规划（9-12月）
4. 所有参数可后期修改，无需写死
5. 保留原有的数据结构，不做更改

数据结构由 init.py 定义，这里只实现 Agent 的方法
"""

import json
from datetime import datetime, timedelta

import requests

from dao import AssignmentDAO, CourseDAO, StudySessionDAO, UserCourseDAO
from models import ActionInput, ActionResult, ChatInput, ChatResult, ScheduleInput, ScheduleResult


class LLMConfig:
    """LLM 配置类 - 支持多种模型和提供商"""

    def __init__(
        self,
        provider: str = "openai",
        base_url: str = None,
        api_key: str = None,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2500,
        timeout: int = 30,
    ):
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @staticmethod
    def openai_api(api_key: str, model: str = "gpt-4") -> "LLMConfig":
        return LLMConfig(provider="openai", api_key=api_key, model=model, base_url="https://api.openai.com/v1")

    @staticmethod
    def local_ollama(base_url: str = "http://localhost:11434", model: str = "deepseek-r1:1.5b") -> "LLMConfig":
        return LLMConfig(provider="ollama", base_url=base_url, model=model)

    @staticmethod
    def local_vllm(base_url: str = "http://localhost:8000", model: str = "meta-llama/Llama-2-7b-hf") -> "LLMConfig":
        return LLMConfig(provider="vllm", base_url=base_url, model=model)

    @staticmethod
    def local_api(base_url: str, model: str = "local-model") -> "LLMConfig":
        return LLMConfig(provider="local_api", base_url=base_url, model=model)

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "api_key": self.api_key if self.api_key and len(self.api_key) > 10 else "***",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }


class PlannerAgent:
    """学期规划智能体（RAG + LLM + 配置化 + 本学期专注）"""

    def __init__(self, llm_config: LLMConfig = None, openai_api_key: str = None, current_semester: str = "2025-Fall"):
        self.current_semester = current_semester
        self.semester_months = [9, 10, 11, 12]

        # 初始化 DAO
        self.user_course_dao = UserCourseDAO()
        self.course_dao = CourseDAO()
        self.assignment_dao = AssignmentDAO()
        self.study_session_dao = StudySessionDAO()

        # 会话状态（支持多轮）
        self._conversations: dict[int, list[dict]] = {}

        # 配置 LLM：优先使用传入配置 -> 环境配置 -> 本地 Ollama
        try:
            from core.config import settings
        except Exception:
            settings = None

        if llm_config:
            self.llm_config = llm_config
        elif openai_api_key:
            self.llm_config = LLMConfig.openai_api(openai_api_key)
        elif settings and getattr(settings, "LLM_API_ENDPOINT", None):
            self.llm_config = LLMConfig.local_api(
                settings.LLM_API_ENDPOINT, model=getattr(settings, "LLM_MODEL_NAME", "local-model")
            )
        else:
            # 默认本地 Ollama
            self.llm_config = LLMConfig.local_ollama()

    # ================================================================
    # LLM 调用方法（支持多个提供商）
    # ================================================================

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM API（支持多个提供商）"""
        try:
            if self.llm_config.provider == "openai":
                return self._call_openai(system_prompt, user_prompt)
            elif self.llm_config.provider == "ollama":
                return self._call_ollama(system_prompt, user_prompt)
            elif self.llm_config.provider == "vllm":
                return self._call_vllm(system_prompt, user_prompt)
            elif self.llm_config.provider == "local_api":
                return self._call_local_api(system_prompt, user_prompt)
            else:
                return f"错误：不支持的提供商 {self.llm_config.provider}"
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return f"错误：无法生成回答。{str(e)}"

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.llm_config.api_key, base_url=self.llm_config.base_url)

        response = client.chat.completions.create(
            model=self.llm_config.model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=self.llm_config.temperature,
            max_tokens=self.llm_config.max_tokens,
        )
        return response.choices[0].message.content

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.llm_config.base_url}/api/generate"
        payload = {"model": self.llm_config.model, "prompt": f"{system_prompt}\n\n{user_prompt}", "stream": False}
        response = requests.post(url, json=payload, timeout=self.llm_config.timeout)
        if response.status_code == 200:
            data = response.json()
            raw_response = data.get("response", json.dumps(data))
            # For deepseek-r1, extract content after </think> if present
            if "</think>" in raw_response:
                raw_response = raw_response.split("</think>", 1)[1].strip()
            return raw_response
        else:
            raise Exception(f"Ollama API 错误: {response.status_code}")

    def _call_vllm(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.llm_config.base_url}/v1/chat/completions"
        payload = {
            "model": self.llm_config.model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": self.llm_config.temperature,
            "max_tokens": self.llm_config.max_tokens,
        }
        response = requests.post(url, json=payload, timeout=self.llm_config.timeout)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"vLLM API 错误: {response.status_code}")

    def _call_local_api(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.llm_config.base_url}/chat"
        payload = {
            "model": self.llm_config.model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": self.llm_config.temperature,
            "max_tokens": self.llm_config.max_tokens,
        }
        response = requests.post(url, json=payload, timeout=self.llm_config.timeout)
        if response.status_code == 200:
            result = response.json()
            if "content" in result:
                return result["content"]
            elif "message" in result:
                return result["message"]
            else:
                return str(result)
        else:
            raise Exception(f"本地 API 错误: {response.status_code}")

    # ================================================================
    # 配置管理方法
    # ================================================================

    def update_llm_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.llm_config, key):
                setattr(self.llm_config, key, value)

    def get_llm_config(self) -> dict:
        return self.llm_config.to_dict()

    # ================================================================
    # Conversation / Chat 支持（多轮）
    # ================================================================

    def _append_conversation(self, user_id: int, role: str, content: str):
        conv = self._conversations.setdefault(user_id, [])
        conv.append({"role": role, "content": content, "ts": datetime.now().isoformat()})

    def chat(self, chat_input: "ChatInput") -> "ChatResult":
        """对话接口：支持多轮上下文、解析意图并触发相应动作（修改作业状态、记录学习时长、返回待办）
        保持输入/输出数据结构与 models 中定义一致。
        """
        user_id = getattr(chat_input, "user_id", None) or 0
        message = getattr(chat_input, "message", "")

        self._append_conversation(user_id, "user", message)

        # Check if user is responding to a previous question
        conv = self._conversations.get(user_id, [])
        if (
            len(conv) >= 2
            and conv[-2]["role"] == "assistant"
            and "是否要添加为新任务" in conv[-2]["content"]
            and message.lower().strip() in ["是", "yes", "y"]
        ):
            reply = "好的，请提供作业的课程名和截止日期，例如：课程 COMP7103 Data Mining，截止 2025-11-20。"
            self._append_conversation(user_id, "assistant", reply)
            return ChatResult(reply=reply)

        system_prompt = (
            "你是课程规划助手。你可以建议计划、识别用户意图并返回结构化动作。\n"
            '当用户说明"我完成了作业 X"时，返回 JSON: {"action":"mark_complete", "assignment_title": "..."}\n'
            '当用户说明"我复习了作业 X 花了 Y 小时"时，返回 JSON: {"action":"log_study_session", "assignment_title": "...", "duration_minutes": 120}\n'
            '当用户询问"告诉我还需要完成的作业"时，返回 JSON: {"action":"list_pending"}\n'
            '如果用户提到新任务如“后天需要提交一份poster报告”，返回 JSON: {"action":"reply", "message":"这是哪门课程的poster报告？截止日期是什么时候？"}\n'
            '如果用户说“我完成了作业 X”但未找到匹配，返回 JSON: {"action":"reply", "message":"未找到该作业，是否要添加为新任务？"}\n'
            '当用户说“作业X其实还没完成”时，返回 JSON: {"action":"unmark_complete", "assignment_title": "..."}\n'
            '当用户说“删除学习记录X”时，返回 JSON: {"action":"delete_study_session", "assignment_title": "..."}\n'
            '当用户问“X月份的时间安排计划”时，返回 JSON: {"action":"generate_monthly_plan", "month": "X"}\n例如，如果用户说“11月份的时间安排计划”，返回 {"action":"generate_monthly_plan", "month": "11"}\n'
            '当用户说“为作业X添加笔记Y”时，返回 JSON: {"action":"add_note", "assignment_title": "X", "note": "Y"}\n'
            '当用户说“上传附件到作业X，路径Y”时，返回 JSON: {"action":"upload_attachment", "assignment_title": "X", "path": "Y"}\n'
            '仅返回 JSON，不要额外解释，除非无法识别意图则返回 {"action":"reply", "message":"..."}\n'
        )

        user_prompt = f"用户: {message}\n当前时间: {datetime.now().isoformat()}"
        llm_response = self.call_llm(system_prompt, user_prompt)

        # 尝试解析 LLM 返回的 JSON 指令
        try:
            # Handle markdown code blocks
            if llm_response.startswith("```json") and "```" in llm_response:
                llm_response = llm_response.split("```json", 1)[1].split("```", 1)[0].strip()
            parsed = json.loads(llm_response)
        except Exception:
            # 非 JSON 则直接把 llm_response 做为回复
            self._append_conversation(user_id, "assistant", llm_response)
            return ChatResult(reply=llm_response)

        action = parsed.get("action")
        if action == "mark_complete":
            title = parsed.get("assignment_title")
            pending = self.assignment_dao.get_pending_by_user(user_id)
            assign = None
            for a in pending:
                if title and title.strip().lower() in (a.get("title") or "").strip().lower():
                    assign = a
                    break
            if assign:
                success = self.assignment_dao.mark_complete_by_id(assign["id"])
                reply = (
                    f"已将作业 '{assign['title']}' 标记为完成。"
                    if success
                    else f"尝试标记作业 '{assign['title']}' 为完成，但失败。"
                )
                self._append_conversation(user_id, "assistant", reply)
                return ChatResult(reply=reply)
            else:
                # Check if already completed
                all_assignments = self.assignment_dao.get_assignments_by_date_range(
                    user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365)
                )
                completed_assign = None
                for a in all_assignments:
                    if (
                        a.get("status") == "completed"
                        and title
                        and title.strip().lower() in (a.get("title") or "").strip().lower()
                    ):
                        completed_assign = a
                        break
                if completed_assign:
                    reply = f"作业 '{completed_assign['title']}' 已经标记为完成。"
                    self._append_conversation(user_id, "assistant", reply)
                    return ChatResult(reply=reply)
                else:
                    reply = "未找到该作业，是否要添加为新任务？"
                    self._append_conversation(user_id, "assistant", reply)
                    return ChatResult(reply=reply)

        elif action == "unmark_complete":
            title = parsed.get("assignment_title")
            pending = self.assignment_dao.get_pending_by_user(user_id)
            assign = None
            for a in pending:
                if title and title.strip().lower() in (a.get("title") or "").strip().lower():
                    assign = a
                    break
            if not assign:
                reply = "未找到该作业，无法取消完成状态。"
                self._append_conversation(user_id, "assistant", reply)
                return ChatResult(reply=reply)

            success = self.assignment_dao.mark_incomplete_by_id(assign["id"])
            reply = (
                f"已将作业 '{assign['title']}' 标记为未完成。"
                if success
                else f"尝试取消作业 '{assign['title']}' 的完成状态，但失败。"
            )
            self._append_conversation(user_id, "assistant", reply)
            return ChatResult(reply=reply)

        elif action == "log_study_session":
            title = parsed.get("assignment_title")
            duration = parsed.get("duration_minutes") or parsed.get("duration") or 0
            pending = self.assignment_dao.get_pending_by_user(user_id)
            assign = None
            for a in pending:
                if title and title.strip().lower() in (a.get("title") or "").strip().lower():
                    assign = a
                    break
            if not assign:
                reply = f"未找到标题匹配为 '{title}' 的作业以记录学习时长。"
                self._append_conversation(user_id, "assistant", reply)
                return ChatResult(reply=reply)

            sid = self.study_session_dao.add_study_session(
                assign["id"], datetime.now(), int(duration), notes=parsed.get("notes")
            )
            reply = f"已记录学习时长 {duration} 分钟，关联作业: {assign['title']} (session_id: {sid})。"
            self._append_conversation(user_id, "assistant", reply)
            return ChatResult(reply=reply)

        elif action == "delete_study_session":
            title = parsed.get("assignment_title")
            pending = self.assignment_dao.get_pending_by_user(user_id)
            assign = None
            for a in pending:
                if title and title.strip().lower() in (a.get("title") or "").strip().lower():
                    assign = a
                    break
            if not assign:
                reply = f"未找到标题匹配为 '{title}' 的作业以删除学习记录。"
                self._append_conversation(user_id, "assistant", reply)
                return ChatResult(reply=reply)

            sessions = self.study_session_dao.get_sessions_by_assignment_id(assign["id"])
            if not sessions:
                reply = f"未找到与作业 '{assign['title']}' 关联的学习记录。"
                self._append_conversation(user_id, "assistant", reply)
                return ChatResult(reply=reply)

            # 删除最新的学习记录
            latest_session = sessions[-1]
            self.study_session_dao.delete_study_session_by_id(latest_session["id"])
            reply = f"已删除作业 '{assign['title']}' 的最新学习记录 (session_id: {latest_session['id']})。"
            self._append_conversation(user_id, "assistant", reply)
            return ChatResult(reply=reply)

        elif action == "list_pending":
            pending = self.assignment_dao.get_pending_by_user(user_id)
            if not pending:
                reply = "没有未完成的作业。"
            else:
                lines = [
                    f"- [{p.get('course_name')}] {p.get('title')} 截止: {p.get('due_date')}, 描述: {p.get('description', '无')}, 笔记: {p.get('notes', '无')}, 附件: {p.get('assignment_path', '无')}"
                    for p in pending
                ]
                # Get user's study session stats
                study_stats = self.study_session_dao.get_study_session_stats(user_id, days=30)
                stats_text = f"用户最近30天学习统计：总学习时长 {study_stats['total_study_hours']} 小时，平均每次 {study_stats['avg_duration']} 分钟，活跃天数 {study_stats['active_days']} 天。"
                brief_sys = "你是日程规划助手，根据以下待办项（包括描述、笔记、附件）和用户学习历史，生成一个个性化学习计划（3-5条建议），尽可能解析附件了解要求、时间安排等。用中文回复。"
                brief_user = stats_text + "\n\n待办项：\n" + "\n".join(lines)
                suggestion = self.call_llm(brief_sys, brief_user)
                reply = "未完成作业:\n" + "\n".join(lines) + "\n\n建议计划:\n" + suggestion
            self._append_conversation(user_id, "assistant", reply)
            return ChatResult(reply=reply)

        elif action == "generate_monthly_plan":
            month = parsed.get("month")
            try:
                month_int = int(month)
                year = datetime.now().year
                start_date = datetime(year, month_int, 1)
                if month_int == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month_int + 1, 1) - timedelta(days=1)
            except:
                reply = "月份格式错误，请输入如'11'。"
                self._append_conversation(user_id, "assistant", reply)
                return ChatResult(reply=reply)

            assignments = self.assignment_dao.get_assignments_by_date_range(user_id, start_date, end_date)
            study_sessions = self.study_session_dao.get_study_sessions_by_date_range(user_id, start_date, end_date)

            assign_text = "\n".join(
                [
                    f"- {a['title']} ({a['course_name']}) 截止: {a['due_date']}, 状态: {a['status']}, 描述: {a.get('description', '无')}, 笔记: {a.get('notes', '无')}, 附件: {a.get('assignment_path', '无')}"
                    for a in assignments
                ]
            )
            session_text = "\n".join(
                [
                    f"- {s['assignment_title']} ({s['course_name']}) 时长: {s['duration_minutes']}分钟, 时间: {s['start_time']}, 笔记: {s.get('notes', '无')}"
                    for s in study_sessions
                ]
            )

            plan_sys = "你是时间管理助手。根据用户的作业（包括描述、笔记、附件）和学习记录（包括笔记），生成X月份的详细计划，包括一个文本形式的甘特图（用字符表示，如[Task] [-----] 1-5）。尽可能解析附件了解要求、时间安排等。用中文回复。"
            plan_user = f"{month}月份作业:\n{assign_text}\n\n学习记录:\n{session_text}"
            plan = self.call_llm(plan_sys, plan_user)
            reply = f"{month}月份时间安排计划:\n{plan}"
            self._append_conversation(user_id, "assistant", reply)
            return ChatResult(reply=reply)

        elif action == "add_note":
            title = parsed.get("assignment_title")
            note = parsed.get("note")
            all_assignments = self.assignment_dao.get_assignments_by_date_range(
                user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365)
            )
            assign = None
            for a in all_assignments:
                if title and title.strip().lower() in (a.get("title") or "").strip().lower():
                    assign = a
                    break
            if not assign:
                reply = f"未找到标题匹配为 '{title}' 的作业以添加笔记。"
                self._append_conversation(user_id, "assistant", reply)
                return ChatResult(reply=reply)

            success = self.assignment_dao.update_notes_by_id(assign["id"], note)
            reply = (
                f"已为作业 '{assign['title']}' 添加笔记。"
                if success
                else f"尝试为作业 '{assign['title']}' 添加笔记，但失败。"
            )
            self._append_conversation(user_id, "assistant", reply)
            return ChatResult(reply=reply)

        elif action == "upload_attachment":
            title = parsed.get("assignment_title")
            path = parsed.get("path")
            all_assignments = self.assignment_dao.get_assignments_by_date_range(
                user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365)
            )
            assign = None
            for a in all_assignments:
                if title and title.strip().lower() in (a.get("title") or "").strip().lower():
                    assign = a
                    break
            if not assign:
                reply = f"未找到标题匹配为 '{title}' 的作业以上传附件。"
                self._append_conversation(user_id, "assistant", reply)
                return ChatResult(reply=reply)

            success = self.assignment_dao.update_path_by_id(assign["id"], path)
            reply = (
                f"已为作业 '{assign['title']}' 上传附件，路径: {path}。"
                if success
                else f"尝试为作业 '{assign['title']}' 上传附件，但失败。"
            )
            self._append_conversation(user_id, "assistant", reply)
            return ChatResult(reply=reply)

        else:
            reply = parsed.get("message") or str(parsed)
            self._append_conversation(user_id, "assistant", reply)
            return ChatResult(reply=reply)

    # ================================================================
    # action() 保持接口，使用 DAO 新工具函数，保留原有动作名
    # ================================================================

    def action(self, action_input: ActionInput) -> ActionResult:
        try:
            action = action_input.action
            data = action_input.data or {}

            if action == "mark_assignment_complete":
                assignment_id = data.get("assignment_id")
                user_id = data.get("user_id")
                if not assignment_id or not user_id:
                    return ActionResult(status="error", message="Missing assignment_id or user_id")

                success = self.assignment_dao.mark_complete_by_id(assignment_id)
                if success:
                    return ActionResult(status="success", message="Assignment marked as complete")
                else:
                    return ActionResult(status="error", message="Failed to mark assignment as complete")

            elif action == "query_pending_assignments":
                user_id = data.get("user_id")
                if not user_id:
                    return ActionResult(status="error", message="Missing user_id")

                pending_assignments = self.assignment_dao.get_pending_by_user(user_id)
                return ActionResult(status="success", data={"pending_assignments": pending_assignments})

            elif action == "generate_study_plan":
                schedule_input = ScheduleInput(**data)
                schedule_result = self.schedule(schedule_input)
                return ActionResult(status="success", data={"schedule": schedule_result.schedule})

            else:
                return ActionResult(status="error", message=f"Unknown action: {action}")

        except Exception as e:
            return ActionResult(status="error", message=f"Action failed: {str(e)}")

    # ================================================================
    # schedule() 保持原方法名与签名
    # ================================================================

    def schedule(self, scheduleInput: ScheduleInput) -> ScheduleResult:
        try:
            user_id = scheduleInput.user_id
            tasks = scheduleInput.tasks or []
            date_range = scheduleInput.date_range

            if not user_id:
                return ScheduleResult(schedule=[{"type": "error", "content": "User ID is required"}])

            relevant_data = self._get_relevant_data(user_id, date_range)

            if not tasks:
                tasks = [a.get("title") for a in relevant_data["assignments"]]

            try:
                ai_plan = self._generate_intelligent_plan(tasks, relevant_data, user_id)
                return self._create_ai_schedule_response(ai_plan, relevant_data, tasks)
            except Exception as e:
                print(f"LLM planning failed, falling back to rule-based scheduling: {e}")
                return self._create_rule_based_schedule(relevant_data, tasks)

        except Exception as e:
            print(f"Schedule generation error: {e}")
            return ScheduleResult(schedule=[{"type": "error", "content": f"Failed to generate schedule: {str(e)}"}])

    # ================================================================
    # Helper methods kept from original implementation
    # ================================================================

    def _get_relevant_data(self, user_id: int, date_range: str) -> dict:
        from datetime import datetime, timedelta

        if date_range and " to " in date_range:
            start_str, end_str = date_range.split(" to ")
            start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d")
            end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")
        else:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=30)

        assignments = self.assignment_dao.get_assignments_by_date_range(user_id, start_date, end_date)
        study_sessions = self.study_session_dao.get_study_sessions_by_date_range(user_id, start_date, end_date)

        return {
            "assignments": assignments,
            "study_sessions": study_sessions,
            "date_range": {"start": start_date, "end": end_date},
        }

    def _generate_intelligent_plan(self, tasks: list[str], relevant_data: dict, user_id: int) -> dict:
        system_prompt = """你是一个智能学习规划助手。根据用户的任务和现有的学习数据，生成合理的日程安排建议。

请考虑：
1. 任务的优先级和复杂度
2. 合理的时间分配
3. 学习效率建议
4. 具体的执行步骤

用中文回复，格式清晰易读。"""

        tasks_text = "\n".join([f"- {task}" for task in tasks])
        assignments_text = "\n".join(
            [
                f"- {a.get('title', '')} (截止: {a.get('due_date')}, 状态: {a.get('status', 'pending')})"
                for a in relevant_data["assignments"][:10]
            ]
        )

        user_prompt = f"""请为以下学习任务生成日程安排：

待办任务：
{tasks_text}

现有作业：
{assignments_text}

时间范围：{relevant_data["date_range"]["start"].strftime("%Y-%m-%d")} 到 {relevant_data["date_range"]["end"].strftime("%Y-%m-%d")}

请提供一个实用的学习计划，包括时间安排和优先级建议。"""

        ai_response = self.call_llm(system_prompt, user_prompt)

        return {
            "ai_recommendation": ai_response,
            "tasks_analyzed": len(tasks),
            "assignments_considered": len(relevant_data["assignments"]),
        }

    def _create_ai_schedule_response(self, ai_plan: dict, relevant_data: dict, tasks: list[str]) -> "ScheduleResult":
        schedule_items = []

        schedule_items.append(
            {
                "type": "ai_recommendation",
                "content": ai_plan["ai_recommendation"],
                "source": "llm",
                "tasks_analyzed": ai_plan["tasks_analyzed"],
            }
        )

        for i, task in enumerate(tasks):
            schedule_items.append(
                {
                    "type": "scheduled_task",
                    "task_id": i + 1,
                    "title": task,
                    "suggested_order": i + 1,
                    "estimated_duration_minutes": 60,
                    "priority": "high" if i == 0 else "medium",
                }
            )

        schedule_items.append(
            {
                "type": "summary",
                "total_tasks": len(tasks),
                "upcoming_assignments": len(relevant_data["assignments"]),
                "study_sessions": len(relevant_data["study_sessions"]),
                "date_range": f"{relevant_data['date_range']['start'].strftime('%Y-%m-%d')} 到 {relevant_data['date_range']['end'].strftime('%Y-%m-%d')}",
            }
        )

        return ScheduleResult(schedule=schedule_items)

    def _create_fallback_schedule(self, relevant_data: dict, tasks: list[str]) -> "ScheduleResult":
        schedule_items = []
        schedule_items.append({"type": "info", "content": "基于现有数据的日程安排（AI规划暂不可用）"})
        for i, task in enumerate(tasks):
            schedule_items.append({"type": "task", "title": task, "order": i + 1, "suggested_time": f"第{i + 1}天"})
        return ScheduleResult(schedule=schedule_items)

    def _create_rule_based_schedule(self, relevant_data: dict, tasks: list[str]) -> "ScheduleResult":
        schedule_items = []
        for i, task in enumerate(tasks):
            schedule_items.append({"type": "task", "title": task, "order": i + 1, "suggested_time": f"Day {i + 1}"})
        return ScheduleResult(schedule=schedule_items)

    def _analyze_schedule_intent(self, query: str, date_range: str, user_id: int) -> dict:
        system_prompt = """你是一个智能学习规划助手。请分析用户的日程查询请求，理解其深层意图和需求。

请分析以下内容：
1. 主要意图（考试准备、作业规划、学习安排、复习计划等）
2. 时间紧迫程度
3. 用户可能的隐藏需求
4. 推荐的规划策略

返回JSON格式：{
    "intent": "考试准备|作业规划|学习安排|复习计划",
    "urgency": "高|中|低",
    "time_range": {"start": "...", "end": "..."},
    "hidden_needs": ["..."],
    "planning_strategy": "...",
    "focus_courses": ["课程名"],
    "priority_tasks": ["任务类型"]
}"""

        user_prompt = f"""
用户查询: {query}
时间范围: {date_range}
用户ID: {user_id}

当前时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}

请分析这个日程查询请求。
"""

        response = self.call_llm(system_prompt, user_prompt)
        try:
            return json.loads(response)
        except Exception:
            return self._fallback_intent_analysis(query, date_range)

    def _fallback_intent_analysis(self, query: str, date_range: str) -> dict:
        try:
            start, end = date_range.split(" to ")
        except Exception:
            start = end = date_range or ""
        return {
            "intent": "general",
            "urgency": "medium",
            "time_range": {"start": start, "end": end},
            "hidden_needs": [],
            "planning_strategy": "rule_based",
            "focus_courses": [],
            "priority_tasks": [],
        }

    def _calculate_time_range_based_on_urgency(self, urgency: str) -> int:
        if urgency == "high":
            return 7
        elif urgency == "medium":
            return 14
        else:
            return 30

    def _get_exam_preparation_sessions(self, user_id: int, focus_courses: list[str]) -> list[dict]:
        return (
            self.study_session_dao.get_sessions_by_courses(user_id, focus_courses)
            if hasattr(self.study_session_dao, "get_sessions_by_courses")
            else []
        )

    def _analyze_study_patterns(self, study_sessions: list[dict]) -> str:
        if not study_sessions:
            return "No recent study patterns available."
        total_hours = sum(
            session.get("duration_minutes", session.get("duration", 0)) or 0 for session in study_sessions
        )
        return f"Total study hours: {total_hours}"

    def _get_user_learning_profile(self, user_id: int) -> str:
        return (
            self.user_course_dao.get_learning_profile(user_id)
            if hasattr(self.user_course_dao, "get_learning_profile")
            else "Default Profile"
        )

    def _calculate_confidence(self, intent_analysis: dict, relevant_data: dict) -> float:
        return 0.9 if intent_analysis.get("intent") == "exam_preparation" else 0.7

    def _extract_structured_plan(self, ai_recommendations: str) -> list[dict]:
        return [
            {
                "task": "Example Task",
                "time": "10:00 AM",
                "priority": "high",
                "duration": "1 hour",
                "reasoning": "Example reasoning.",
            }
        ]

    def _calculate_recent_study_hours(self, study_sessions: list[dict]) -> int:
        return sum(session.get("duration_minutes", session.get("duration", 0)) or 0 for session in study_sessions)
