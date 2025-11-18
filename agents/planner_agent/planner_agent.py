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

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import json

from dao import (
    UserCourseDAO,
    CourseDAO, AssignmentDAO,
    StudySessionDAO
)
from models import ActionInput, ActionResult, ScheduleResult, ScheduleInput, ChatInput, ChatResult


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
            timeout: int = 30
    ):
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @staticmethod
    def openai_api(api_key: str, model: str = "gpt-4",base_url="https://dashscope.aliyuncs.com/compatible-mode/v1") -> "LLMConfig":
        return LLMConfig(provider="openai", api_key=api_key, model=model, base_url=base_url)

    @staticmethod
    def local_ollama(base_url: str = "http://localhost:11434", model: str = "deepseek-r1:1.5b") -> "LLMConfig":
        return LLMConfig(provider="ollama", base_url=base_url, model=model)

    @staticmethod
    def local_vllm(base_url: str = "http://localhost:8000", model: str = "meta-llama/Llama-2-7b-hf") -> "LLMConfig":
        return LLMConfig(provider="vllm", base_url=base_url, model=model)

    @staticmethod
    def local_api(base_url: str, model: str = "local-model") -> "LLMConfig":
        return LLMConfig(provider="local_api", base_url=base_url, model=model)

    def to_dict(self) -> Dict:
        return {
            'provider': self.provider,
            'base_url': self.base_url,
            'api_key': self.api_key if self.api_key and len(self.api_key) > 10 else '***',
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'timeout': self.timeout
        }


class PlannerAgent:
    """学期规划智能体（RAG + LLM + 配置化 + 本学期专注）"""

    def __init__(
            self,
            llm_config: LLMConfig = None,
            openai_api_key: str = None,
            current_semester: str = "2025-Fall"
    ):
        self.current_semester = current_semester
        self.semester_months = [9, 10, 11, 12]

        # 初始化 DAO
        self.user_course_dao = UserCourseDAO()
        self.course_dao = CourseDAO()
        self.assignment_dao = AssignmentDAO()
        self.study_session_dao = StudySessionDAO()

        # 会话状态（支持多轮）
        self._conversations: Dict[int, List[Dict]] = {}

        # 配置 LLM：优先使用传入配置 -> 环境配置 -> 本地 Ollama
        try:
            from core.config import settings
        except Exception:
            settings = None

        if llm_config:
            self.llm_config = llm_config
        elif openai_api_key:
            self.llm_config = LLMConfig.openai_api(openai_api_key)
        elif settings and getattr(settings, 'LLM_API_ENDPOINT', None):
            self.llm_config = LLMConfig.local_api(settings.LLM_API_ENDPOINT, model=getattr(settings, 'LLM_MODEL_NAME', 'local-model'))
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
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.llm_config.api_key, base_url=self.llm_config.base_url or "https://api.openai.com/v1")
            response = client.chat.completions.create(
                model=self.llm_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens
            )
            return response.choices[0].message.content
        except ImportError:
            # Fallback to old API if new version not available
            import openai
            openai.api_key = self.llm_config.api_key
            openai.api_base = self.llm_config.base_url or "https://api.openai.com/v1"
            response = openai.ChatCompletion.create(
                model=self.llm_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens
            )
            return response['choices'][0]['message']['content']

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.llm_config.base_url}/api/generate"
        payload = {
            "model": self.llm_config.model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False
        }
        response = requests.post(url, json=payload, timeout=self.llm_config.timeout)
        if response.status_code == 200:
            data = response.json()
            raw_response = data.get('response', json.dumps(data))
            # For deepseek-r1, extract content after </think> if present
            if '</think>' in raw_response:
                raw_response = raw_response.split('</think>', 1)[1].strip()
            return raw_response
        else:
            raise Exception(f"Ollama API 错误: {response.status_code}")

    def _call_vllm(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.llm_config.base_url}/v1/chat/completions"
        payload = {
            "model": self.llm_config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.llm_config.temperature,
            "max_tokens": self.llm_config.max_tokens
        }
        response = requests.post(url, json=payload, timeout=self.llm_config.timeout)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            raise Exception(f"vLLM API 错误: {response.status_code}")

    def _call_local_api(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.llm_config.base_url}/chat"
        payload = {
            "model": self.llm_config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.llm_config.temperature,
            "max_tokens": self.llm_config.max_tokens
        }
        response = requests.post(url, json=payload, timeout=self.llm_config.timeout)
        if response.status_code == 200:
            result = response.json()
            if 'content' in result:
                return result['content']
            elif 'message' in result:
                return result['message']
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

    def get_llm_config(self) -> Dict:
        return self.llm_config.to_dict()

    # ================================================================
    # Conversation / Chat 支持（多轮）
    # ================================================================

    def _append_conversation(self, user_id: int, role: str, content: str):
        conv = self._conversations.setdefault(user_id, [])
        conv.append({'role': role, 'content': content, 'ts': datetime.now().isoformat()})

    def chat(self, chat_input: 'ChatInput') -> 'ChatResult':
        """对话接口：支持多轮上下文、解析意图并触发相应动作（修改作业状态、记录学习时长、返回待办）
        保持输入/输出数据结构与 models 中定义一致。
        """
        user_id = getattr(chat_input, 'user_id', None) or 0
        message = getattr(chat_input, 'message', '')

        self._append_conversation(user_id, 'user', message)

        # Quick rule: if user asks about their courses, return course list directly
        low = message.lower()
        course_query_keywords = ["有哪些课", "我有哪些课", "有哪些课程", "查看我有哪些课"]
        try:
            if any(k in low for k in course_query_keywords):
                # Prefer progress info if available
                try:
                    progress_list = self.user_course_dao.get_course_progress(user_id)
                except Exception:
                    progress_list = []
                try:
                    active_courses = self.user_course_dao.get_user_active_courses(user_id)
                except Exception:
                    active_courses = []

                if not active_courses and not progress_list:
                    reply = "您当前没有已选课程。"
                else:
                    # Build mapping of progress by course_name
                    prog_map = {p.get('course_name'): p for p in progress_list} if progress_list else {}
                    lines = []
                    # Use active_courses order; fall back to progress_list if needed
                    if active_courses:
                        for c in active_courses:
                            cname = c.get('course_name') or c.get('course') or 'Unknown Course'
                            prog = prog_map.get(cname, {}).get('progress_percentage') if prog_map else None
                            if prog is not None:
                                lines.append(f"- {cname} (进度: {prog}%)")
                            else:
                                lines.append(f"- {cname}")
                    else:
                        for p in progress_list:
                            lines.append(f"- {p.get('course_name')} (进度: {p.get('progress_percentage')}%)")

                    reply = "您当前的课程：\n" + "\n".join(lines)

                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)
        except Exception:
            # On any unexpected error, fall back to LLM path
            pass

        # Check if user is responding to a previous question
        conv = self._conversations.get(user_id, [])
        if len(conv) >= 2 and conv[-2]['role'] == 'assistant' and '是否要添加为新任务' in conv[-2]['content'] and message.lower().strip() in ['是', 'yes', 'y']:
            reply = "好的，请提供作业的课程名和截止日期，例如：课程 COMP7103 Data Mining，截止 2025-11-20。"
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        # Heuristic: if the user is adding an assignment and already mentions a course, try to add it directly
        try:
            import re
            add_keywords = ["添加一个assignment", "添加assignment", "添加作业", "新建作业", "添加一个作业", "创建作业", "Add an assignment", "add assignment", "create assignment", "new assignment"]
            if any(k in message for k in add_keywords) or message.strip().startswith("添加"):
                # try to extract course code or course name
                course_name = None
                # common patterns: '属于课程COMP7103', '属于课程 COMP7103', '课程COMP7103', '课程 COMP7103'
                m = re.search(r"属于课程\s*([A-Za-z0-9\-\s]+)", message)
                if not m:
                    m = re.search(r"课程\s*([A-Za-z0-9\-\s]+)", message)
                if not m:
                    # English: "belongs to the course COMP7404", "course COMP7404"
                    m = re.search(r"(?:belongs to the course|course)\s*([A-Za-z0-9\-\s]+)", message, re.IGNORECASE)
                if m:
                    course_name = m.group(1).strip()
                # Also accept patterns like '它属于课程COMP7103' or '属于COMP7103'
                if not course_name:
                    m2 = re.search(r"属于\s*([A-Za-z0-9\-]+)", message)
                    if m2:
                        course_name = m2.group(1).strip()

                if course_name:
                    try:
                        active_courses = self.user_course_dao.get_user_active_courses(user_id)
                    except Exception:
                        active_courses = []

                    found_course = None
                    for c in active_courses:
                        cname = (c.get('course_name') or '')
                        # match by substrings or by exact code
                        if course_name.lower() in cname.lower() or course_name.lower() == (cname.split()[0].lower() if cname else ''):
                            found_course = c
                            break

                    if found_course:
                        # extract title and due date
                        title = None
                        # English: "called CC", "called AA"
                        tm = re.search(r"called\s+([A-Za-z0-9]+)", message, re.IGNORECASE)
                        if not tm:
                            # Chinese: "叫\s*([^，,。\n]+)"
                            tm = re.search(r"叫\s*([^，,。\n]+)", message)
                        if not tm:
                            # fallback: pick phrase after 'add' or '添加' up to comma
                            tm2 = re.search(r"(?:add|添加)[^,。]*?([A-Za-z0-9]+)", message, re.IGNORECASE)
                            if tm2:
                                title = tm2.group(1).strip()
                        if tm:
                            title = tm.group(1).strip()
                        if not title:
                            title = "New Assignment"

                        due = None
                        dm = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", message)
                        if dm:
                            try:
                                due = datetime.strptime(dm.group(1).replace('/', '-'), "%Y-%m-%d")
                            except Exception:
                                due = None

                        # Resolve external course_id stored in courses.course_id.
                        # user_course DAO returns internal courses.id in the 'course_id' field.
                        external_course_id = None
                        try:
                            internal_id = found_course.get('course_id') or found_course.get('id')
                            all_courses = self.course_dao.get_all_courses()
                            for cr in all_courses:
                                # cr has keys 'id' (internal) and 'course_id' (external)
                                if cr.get('id') == internal_id:
                                    external_course_id = cr.get('course_id')
                                    break
                        except Exception:
                            external_course_id = None

                        # Fallback: if not resolved, try to use provided value (may be external already)
                        if not external_course_id:
                            try:
                                # attempt to coerce numeric-like values
                                external_course_id = int(found_course.get('course_id')) if found_course.get('course_id') else None
                            except Exception:
                                external_course_id = None

                        assignment_data = {
                            'title': title,
                            'description': None,
                            'course_id': external_course_id,
                            'user_id': user_id,
                            'due_date': due or datetime.now(),
                            'status': 'pending'
                        }

                        try:
                            success = self.assignment_dao.insert_assignment(assignment_data)
                        except Exception as e:
                            # log error for diagnosis
                            print(f"Failed to insert assignment for user {user_id}, course internal_id={found_course.get('course_id')}, resolved external_course_id={external_course_id}: {e}")
                            success = False

                        if success:
                            due_text = dm.group(1) if dm else '未指定'
                            reply = f"已为课程 '{found_course.get('course_name')}' 添加作业 '{title}'，截止: {due_text}。"
                        else:
                            reply = "尝试添加作业，但失败。"

                        self._append_conversation(user_id, 'assistant', reply)
                        return ChatResult(reply=reply)
                    else:
                        reply = "我没有在您的选课中找到该课程，是否要将这门课程添加到您的课程列表并创建该作业？"
                        self._append_conversation(user_id, 'assistant', reply)
                        return ChatResult(reply=reply)
        except Exception:
            # if heuristic fails, continue to LLM path
            pass

        system_prompt = (
            "你是课程规划助手。你可以建议计划、识别用户意图并返回结构化动作。\n"
            "当用户说明\"我完成了作业 X\"时，返回 JSON: {\"action\":\"mark_complete\", \"assignment_title\": \"...\"}\n"
            "当用户说明\"我复习了作业 X 花了 Y 小时\"时，返回 JSON: {\"action\":\"log_study_session\", \"assignment_title\": \"...\", \"duration_minutes\": 120}\n"
            "当用户询问\"告诉我还需要完成的作业\"时，返回 JSON: {\"action\":\"list_pending\"}\n"
            "如果用户提到新任务如“后天需要提交一份poster报告”，返回 JSON: {\"action\":\"reply\", \"message\":\"这是哪门课程的poster报告？截止日期是什么时候？\"}\n"
            "如果用户说“我完成了作业 X”但未找到匹配，返回 JSON: {\"action\":\"reply\", \"message\":\"未找到该作业，是否要添加为新任务？\"}\n"
            "当用户说“作业X其实还没完成”时，返回 JSON: {\"action\":\"unmark_complete\", \"assignment_title\": \"...\"}\n"
            "当用户说“删除学习记录X”时，返回 JSON: {\"action\":\"delete_study_session\", \"assignment_title\": \"...\"}\n"
            "当用户问“X月份的时间安排计划”时，返回 JSON: {\"action\":\"generate_monthly_plan\", \"month\": \"X\"}\n例如，如果用户说“11月份的时间安排计划”，返回 {\"action\":\"generate_monthly_plan\", \"month\": \"11\"}\n"
            "当用户说“帮我规划X课程”时，返回 JSON: {\"action\":\"generate_course_plan\", \"course_name\": \"X\"}\n"
            "当用户说“为作业X添加笔记Y”时，返回 JSON: {\"action\":\"add_note\", \"assignment_title\": \"X\", \"note\": \"Y\"}\n"
            "当用户说“上传附件到作业X，路径Y”时，返回 JSON: {\"action\":\"upload_attachment\", \"assignment_title\": \"X\", \"path\": \"Y\"}\n"
            "仅返回 JSON，不要额外解释，除非无法识别意图则返回 {\"action\":\"reply\", \"message\":\"...\"}\n"
        )

        user_prompt = f"用户: {message}\n当前时间: {datetime.now().isoformat()}"
        llm_response = self.call_llm(system_prompt, user_prompt)

        # 尝试解析 LLM 返回的 JSON 指令
        try:
            # Handle markdown code blocks
            if llm_response.startswith('```json') and '```' in llm_response:
                llm_response = llm_response.split('```json', 1)[1].split('```', 1)[0].strip()
            parsed = json.loads(llm_response)
        except Exception:
            # 非 JSON 则直接把 llm_response 做为回复
            self._append_conversation(user_id, 'assistant', llm_response)
            return ChatResult(reply=llm_response)

        action = parsed.get('action')
        if action == 'mark_complete':
            title = parsed.get('assignment_title')
            pending = self.assignment_dao.get_pending_by_user(user_id)
            assign = None
            for a in pending:
                if title and title.strip().lower() in (a.get('title') or '').strip().lower():
                    assign = a
                    break
            if assign:
                success = self.assignment_dao.mark_complete_by_id(assign['id'])
                reply = f"已将作业 '{assign['title']}' 标记为完成。" if success else f"尝试标记作业 '{assign['title']}' 为完成，但失败。"
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)
            else:
                # Check if already completed
                all_assignments = self.assignment_dao.get_assignments_by_date_range(user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365))
                completed_assign = None
                for a in all_assignments:
                    if a.get('status') == 'completed' and title and title.strip().lower() in (a.get('title') or '').strip().lower():
                        completed_assign = a
                        break
                if completed_assign:
                    reply = f"作业 '{completed_assign['title']}' 已经标记为完成。"
                    self._append_conversation(user_id, 'assistant', reply)
                    return ChatResult(reply=reply)
                else:
                    reply = "未找到该作业，是否要添加为新任务？"
                    self._append_conversation(user_id, 'assistant', reply)
                    return ChatResult(reply=reply)

        elif action == 'unmark_complete':
            title = parsed.get('assignment_title')
            pending = self.assignment_dao.get_pending_by_user(user_id)
            assign = None
            for a in pending:
                if title and title.strip().lower() in (a.get('title') or '').strip().lower():
                    assign = a
                    break
            if not assign:
                reply = "未找到该作业，无法取消完成状态。"
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            success = self.assignment_dao.mark_incomplete_by_id(assign['id'])
            reply = f"已将作业 '{assign['title']}' 标记为未完成。" if success else f"尝试取消作业 '{assign['title']}' 的完成状态，但失败。"
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        elif action == 'log_study_session':
            title = parsed.get('assignment_title')
            duration = parsed.get('duration_minutes') or parsed.get('duration') or 0
            pending = self.assignment_dao.get_pending_by_user(user_id)
            assign = None
            for a in pending:
                if title and title.strip().lower() in (a.get('title') or '').strip().lower():
                    assign = a
                    break
            if not assign:
                reply = f"未找到标题匹配为 '{title}' 的作业以记录学习时长。"
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            sid = self.study_session_dao.add_study_session(assign['id'], datetime.now(), int(duration), notes=parsed.get('notes'))
            reply = f"已记录学习时长 {duration} 分钟，关联作业: {assign['title']} (session_id: {sid})。"
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        elif action == 'delete_study_session':
            title = parsed.get('assignment_title')
            pending = self.assignment_dao.get_pending_by_user(user_id)
            assign = None
            for a in pending:
                if title and title.strip().lower() in (a.get('title') or '').strip().lower():
                    assign = a
                    break
            if not assign:
                reply = f"未找到标题匹配为 '{title}' 的作业以删除学习记录。"
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            sessions = self.study_session_dao.get_sessions_by_assignment_id(assign['id'])
            if not sessions:
                reply = f"未找到与作业 '{assign['title']}' 关联的学习记录。"
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            # 删除最新的学习记录
            latest_session = sessions[-1]
            self.study_session_dao.delete_study_session_by_id(latest_session['id'])
            reply = f"已删除作业 '{assign['title']}' 的最新学习记录 (session_id: {latest_session['id']})。"
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        elif action == 'list_pending':
            pending = self.assignment_dao.get_pending_by_user(user_id)
            if not pending:
                reply = "没有未完成的作业。"
            else:
                lines = [f"- [{p.get('course_name')}] {p.get('title')} 截止: {p.get('due_date')}, 描述: {p.get('description', '无')}, 笔记: {p.get('notes', '无')}, 附件: {p.get('assignment_path', '无')}" for p in pending]
                # Get user's study session stats
                study_stats = self.study_session_dao.get_study_session_stats(user_id, days=30)
                stats_text = f"用户最近30天学习统计：总学习时长 {study_stats['total_study_hours']} 小时，平均每次 {study_stats['avg_duration']} 分钟，活跃天数 {study_stats['active_days']} 天。"
                brief_sys = "你是日程规划助手，根据以下待办项（包括描述、笔记、附件）和用户学习历史，生成一个个性化学习计划（3-5条建议），尽可能解析附件了解要求、时间安排等。用中文回复。"
                brief_user = stats_text + "\n\n待办项：\n" + "\n".join(lines)
                suggestion = self.call_llm(brief_sys, brief_user)
                reply = "未完成作业:\n" + "\n".join(lines) + "\n\n建议计划:\n" + suggestion
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        elif action == 'generate_monthly_plan':
            month = parsed.get('month')
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
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            assignments = self.assignment_dao.get_assignments_by_date_range(user_id, start_date, end_date)
            study_sessions = self.study_session_dao.get_study_sessions_by_date_range(user_id, start_date, end_date)

            assign_text = "\n".join([f"- {a['title']} ({a['course_name']}) 截止: {a['due_date']}, 状态: {a['status']}, 描述: {a.get('description', '无')}, 笔记: {a.get('notes', '无')}, 附件: {a.get('assignment_path', '无')}" for a in assignments])
            session_text = "\n".join([f"- {s['assignment_title']} ({s['course_name']}) 时长: {s['duration_minutes']}分钟, 时间: {s['start_time']}, 笔记: {s.get('notes', '无')}" for s in study_sessions])

            plan_sys = "你是时间管理助手。根据用户的作业（包括描述、笔记、附件）和学习记录（包括笔记），生成X月份的详细计划，包括一个文本形式的甘特图（用字符表示，如[Task] [-----] 1-5）。尽可能解析附件了解要求、时间安排等。用中文回复。"
            plan_user = f"{month}月份作业:\n{assign_text}\n\n学习记录:\n{session_text}"
            plan = self.call_llm(plan_sys, plan_user)
            reply = f"{month}月份时间安排计划:\n{plan}"
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        elif action == 'generate_course_plan':
            course_name = parsed.get('course_name')
            if not course_name:
                reply = "课程名不能为空。"
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            # Get assignments for the course
            all_assignments = self.assignment_dao.get_assignments_by_date_range(user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365))
            course_assignments = [a for a in all_assignments if a.get('course_name') and course_name.lower() in a.get('course_name').lower()]

            # Get study sessions for the course
            all_sessions = self.study_session_dao.get_study_sessions_by_date_range(user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365))
            course_sessions = [s for s in all_sessions if s.get('course_name') and course_name.lower() in s.get('course_name').lower()]

            assign_text = "\n".join([f"- {a['title']} 截止: {a['due_date']}, 状态: {a['status']}, 描述: {a.get('description', '无')}, 笔记: {a.get('notes', '无')}, 附件: {a.get('assignment_path', '无')}" for a in course_assignments])
            session_text = "\n".join([f"- {s['assignment_title']} 时长: {s['duration_minutes']}分钟, 时间: {s['start_time']}, 笔记: {s.get('notes', '无')}" for s in course_sessions])

            plan_sys = "你是课程规划助手。根据用户的作业（包括描述、笔记、附件）和学习记录（包括笔记），为X课程生成详细学习计划，包括时间安排、优先级和建议。用中文回复。"
            plan_user = f"{course_name}作业:\n{assign_text}\n\n学习记录:\n{session_text}"
            plan = self.call_llm(plan_sys, plan_user)
            reply = f"{course_name}课程学习计划:\n{plan}"
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        elif action == 'add_note':
            title = parsed.get('assignment_title')
            note = parsed.get('note')
            all_assignments = self.assignment_dao.get_assignments_by_date_range(user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365))
            assign = None
            for a in all_assignments:
                if title and title.strip().lower() in (a.get('title') or '').strip().lower():
                    assign = a
                    break
            if not assign:
                reply = f"未找到标题匹配为 '{title}' 的作业以添加笔记。"
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            success = self.assignment_dao.update_notes_by_id(assign['id'], note)
            reply = f"已为作业 '{assign['title']}' 添加笔记。" if success else f"尝试为作业 '{assign['title']}' 添加笔记，但失败。"
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        elif action == 'upload_attachment':
            title = parsed.get('assignment_title')
            path = parsed.get('path')
            all_assignments = self.assignment_dao.get_assignments_by_date_range(user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365))
            assign = None
            for a in all_assignments:
                if title and title.strip().lower() in (a.get('title') or '').strip().lower():
                    assign = a
                    break
            if not assign:
                reply = f"未找到标题匹配为 '{title}' 的作业以上传附件。"
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            success = self.assignment_dao.update_path_by_id(assign['id'], path)
            reply = f"已为作业 '{assign['title']}' 上传附件，路径: {path}。" if success else f"尝试为作业 '{assign['title']}' 上传附件，但失败。"
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        else:
            reply = parsed.get('message') or str(parsed)
            self._append_conversation(user_id, 'assistant', reply)
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
                tasks = [a.get('title') for a in relevant_data['assignments']]

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

    def _get_relevant_data(self, user_id: int, date_range: str) -> Dict:
        from datetime import datetime, timedelta

        if date_range and ' to ' in date_range:
            start_str, end_str = date_range.split(' to ')
            start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d')
            end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d')
        else:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=30)

        assignments = self.assignment_dao.get_assignments_by_date_range(user_id, start_date, end_date)
        study_sessions = self.study_session_dao.get_study_sessions_by_date_range(user_id, start_date, end_date)

        return {
            'assignments': assignments,
            'study_sessions': study_sessions,
            'date_range': {'start': start_date, 'end': end_date}
        }

    def _generate_intelligent_plan(self, tasks: List[str], relevant_data: Dict, user_id: int) -> Dict:
        system_prompt = """你是一个智能学习规划助手。根据用户的任务和现有的学习数据，生成合理的日程安排建议。

请考虑：
1. 任务的优先级和复杂度
2. 合理的时间分配
3. 学习效率建议
4. 具体的执行步骤

用中文回复，格式清晰易读。"""

        tasks_text = "\n".join([f"- {task}" for task in tasks])
        assignments_text = "\n".join([
            f"- {a.get('title', '')} (截止: {a.get('due_date')}, 状态: {a.get('status', 'pending')})"
            for a in relevant_data['assignments'][:10]
        ])

        user_prompt = f"""请为以下学习任务生成日程安排：

待办任务：
{tasks_text}

现有作业：
{assignments_text}

时间范围：{relevant_data['date_range']['start'].strftime('%Y-%m-%d')} 到 {relevant_data['date_range']['end'].strftime('%Y-%m-%d')}

请提供一个实用的学习计划，包括时间安排和优先级建议。"""

        ai_response = self.call_llm(system_prompt, user_prompt)

        return {
            'ai_recommendation': ai_response,
            'tasks_analyzed': len(tasks),
            'assignments_considered': len(relevant_data['assignments'])
        }

    def _create_ai_schedule_response(self, ai_plan: Dict, relevant_data: Dict, tasks: List[str]) -> "ScheduleResult":
        schedule_items = []

        schedule_items.append({
            'type': 'ai_recommendation',
            'content': ai_plan['ai_recommendation'],
            'source': 'llm',
            'tasks_analyzed': ai_plan['tasks_analyzed']
        })

        for i, task in enumerate(tasks):
            schedule_items.append({
                'type': 'scheduled_task',
                'task_id': i + 1,
                'title': task,
                'suggested_order': i + 1,
                'estimated_duration_minutes': 60,
                'priority': 'high' if i == 0 else 'medium'
            })

        schedule_items.append({
            'type': 'summary',
            'total_tasks': len(tasks),
            'upcoming_assignments': len(relevant_data['assignments']),
            'study_sessions': len(relevant_data['study_sessions']),
            'date_range': f"{relevant_data['date_range']['start'].strftime('%Y-%m-%d')} 到 {relevant_data['date_range']['end'].strftime('%Y-%m-%d')}"
        })

        return ScheduleResult(schedule=schedule_items)

    def _create_fallback_schedule(self, relevant_data: Dict, tasks: List[str]) -> "ScheduleResult":
        schedule_items = []
        schedule_items.append({
            'type': 'info',
            'content': '基于现有数据的日程安排（AI规划暂不可用）'
        })
        for i, task in enumerate(tasks):
            schedule_items.append({
                'type': 'task',
                'title': task,
                'order': i + 1,
                'suggested_time': f'第{i + 1}天'
            })
        return ScheduleResult(schedule=schedule_items)

    def _create_rule_based_schedule(self, relevant_data: Dict, tasks: List[str]) -> "ScheduleResult":
        schedule_items = []
        for i, task in enumerate(tasks):
            schedule_items.append({
                'type': 'task',
                'title': task,
                'order': i + 1,
                'suggested_time': f'Day {i + 1}'
            })
        return ScheduleResult(schedule=schedule_items)

    def _analyze_schedule_intent(self, query: str, date_range: str, user_id: int) -> Dict:
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

当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

请分析这个日程查询请求。
"""

        response = self.call_llm(system_prompt, user_prompt)
        try:
            return json.loads(response)
        except Exception:
            return self._fallback_intent_analysis(query, date_range)

    def _fallback_intent_analysis(self, query: str, date_range: str) -> Dict:
        try:
            start, end = date_range.split(' to ')
        except Exception:
            start = end = date_range or ''
        return {
            "intent": "general",
            "urgency": "medium",
            "time_range": {"start": start, "end": end},
            "hidden_needs": [],
            "planning_strategy": "rule_based",
            "focus_courses": [],
            "priority_tasks": []
        }

    def _calculate_time_range_based_on_urgency(self, urgency: str) -> int:
        if urgency == "high":
            return 7
        elif urgency == "medium":
            return 14
        else:
            return 30

    def _get_exam_preparation_sessions(self, user_id: int, focus_courses: List[str]) -> List[Dict]:
        return self.study_session_dao.get_sessions_by_courses(user_id, focus_courses) if hasattr(self.study_session_dao, 'get_sessions_by_courses') else []

    def _analyze_study_patterns(self, study_sessions: List[Dict]) -> str:
        if not study_sessions:
            return "No recent study patterns available."
        total_hours = sum(session.get("duration_minutes", session.get("duration", 0)) or 0 for session in study_sessions)
        return f"Total study hours: {total_hours}"

    def _get_user_learning_profile(self, user_id: int) -> str:
        return self.user_course_dao.get_learning_profile(user_id) if hasattr(self.user_course_dao, 'get_learning_profile') else "Default Profile"

    def _calculate_confidence(self, intent_analysis: Dict, relevant_data: Dict) -> float:
        return 0.9 if intent_analysis.get("intent") == "exam_preparation" else 0.7

    def _extract_structured_plan(self, ai_recommendations: str) -> List[Dict]:
        return [{"task": "Example Task", "time": "10:00 AM", "priority": "high", "duration": "1 hour", "reasoning": "Example reasoning."}]

    def _calculate_recent_study_hours(self, study_sessions: List[Dict]) -> int:
        return sum(session.get("duration_minutes", session.get("duration", 0)) or 0 for session in study_sessions)
