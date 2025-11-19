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
                return f"Error: Unsupported provider {self.llm_config.provider}"
        except Exception as e:
            print(f"LLM call failed: {e}")
            return f"Error: Unable to generate response. {str(e)}"

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
            raise Exception(f"Ollama API error: {response.status_code}")

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
            raise Exception(f"vLLM API error: {response.status_code}")

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
            raise Exception(f"Local API error: {response.status_code}")

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
                    reply = "You currently have no enrolled courses."
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
                                lines.append(f"- {cname} (Progress: {prog}%)")
                            else:
                                lines.append(f"- {cname}")
                    else:
                        for p in progress_list:
                            lines.append(f"- {p.get('course_name')} (Progress: {p.get('progress_percentage')}%)")

                    reply = "Your current courses:\n" + "\n".join(lines)

                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)
        except Exception:
            # On any unexpected error, fall back to LLM path
            pass

        # Check if user is responding to a previous question
        conv = self._conversations.get(user_id, [])
        if len(conv) >= 2 and conv[-2]['role'] == 'assistant' and '是否要添加为新任务' in conv[-2]['content'] and message.lower().strip() in ['是', 'yes', 'y']:
            reply = "Okay, please provide the course name and due date for the assignment, for example: Course COMP7103 Data Mining, due 2025-11-20."
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
                            due_text = dm.group(1) if dm else 'not specified'
                            reply = f"Added assignment '{title}' for course '{found_course.get('course_name')}', due: {due_text}."
                        else:
                            reply = "Attempted to add assignment, but failed."

                        self._append_conversation(user_id, 'assistant', reply)
                        return ChatResult(reply=reply)
                    else:
                        # Course not found, try to add the course first
                        try:
                            # Parse course_id from course_name, e.g., COMP7404 -> 7404
                            import re
                            match = re.match(r'COMP(\d+)', course_name)
                            if match:
                                external_course_id = int(match.group(1))
                                # Try to insert the course
                                internal_course_id = self.course_dao.insert_name(course_name, external_course_id)
                                if internal_course_id:
                                    # Add to user courses
                                    self.user_course_dao.insert_user_courses(user_id, internal_course_id)
                                    reply = f"Added course '{course_name}' to your course list. Now adding the assignment."
                                    self._append_conversation(user_id, 'assistant', reply)
                                    # Now add the assignment
                                    title = None
                                    tm = re.search(r"called\s+([A-Za-z0-9]+)", message, re.IGNORECASE)
                                    if not tm:
                                        tm = re.search(r"叫\s*([^，,。\n]+)", message)
                                    if not tm:
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
                                        print(f"Failed to insert assignment after adding course: {e}")
                                        success = False

                                    if success:
                                        due_text = dm.group(1) if dm else 'not specified'
                                        reply = f"Added assignment '{title}' for course '{course_name}', due: {due_text}."
                                    else:
                                        reply = "Attempted to add assignment, but failed."
                                else:
                                    reply = "Failed to add the course to your list."
                            else:
                                reply = "Could not parse course ID from course name."
                        except Exception as e:
                            reply = f"Error adding course: {str(e)}"

                        self._append_conversation(user_id, 'assistant', reply)
                        return ChatResult(reply=reply)
        except Exception:
            # if heuristic fails, continue to LLM path
            pass

        system_prompt = (
            "You are a course planning assistant. You can suggest plans, identify user intents, and return structured actions.\n"
            "When the user says \"I completed assignment X\", return JSON: {\"action\":\"mark_complete\", \"assignment_title\": \"...\"}\n"
            "When the user says \"I studied assignment X for Y hours\", return JSON: {\"action\":\"log_study_session\", \"assignment_title\": \"...\", \"duration_minutes\": 120}\n"
            "When the user asks \"Tell me what assignments I still need to complete\", return JSON: {\"action\":\"list_pending\"}\n"
            "If the user mentions a new task like \"I need to submit a poster report the day after tomorrow\", return JSON: {\"action\":\"reply\", \"message\":\"Which course is this poster report for? What is the deadline?\"}\n"
            "If the user says \"I completed assignment X\" but no match is found, return JSON: {\"action\":\"reply\", \"message\":\"Assignment not found, do you want to add it as a new task?\"}\n"
            "When the user says \"Assignment X is actually not completed yet\", return JSON: {\"action\":\"unmark_complete\", \"assignment_title\": \"...\"}\n"
            "When the user says \"Delete study session X\", return JSON: {\"action\":\"delete_study_session\", \"assignment_title\": \"...\"}\n"
            "When the user asks \"Schedule plan for month X\", return JSON: {\"action\":\"generate_monthly_plan\", \"month\": \"X\"}\nFor example, if the user says \"Schedule plan for November\", return {\"action\":\"generate_monthly_plan\", \"month\": \"11\"}\n"
            "When the user says \"Help me plan course X\", return JSON: {\"action\":\"generate_course_plan\", \"course_name\": \"X\"}\n"
            "When the user says \"Add note Y to assignment X\", return JSON: {\"action\":\"add_note\", \"assignment_title\": \"X\", \"note\": \"Y\"}\n"
            "When the user says \"Upload attachment to assignment X, path Y\", return JSON: {\"action\":\"upload_attachment\", \"assignment_title\": \"X\", \"path\": \"Y\"}\n"
            "Return only JSON, no extra explanation, unless intent cannot be identified, then return {\"action\":\"reply\", \"message\":\"...\"}\n"
        )

        user_prompt = f"User: {message}\nCurrent time: {datetime.now().isoformat()}"
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
                reply = f"Marked assignment '{assign['title']}' as complete." if success else f"Attempted to mark assignment '{assign['title']}' as complete, but failed."
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
                    reply = f"Assignment '{completed_assign['title']}' is already marked as complete."
                    self._append_conversation(user_id, 'assistant', reply)
                    return ChatResult(reply=reply)
                else:
                    reply = "Assignment not found, do you want to add it as a new task?"
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
                reply = "Assignment not found, cannot unmark as complete."
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            success = self.assignment_dao.mark_incomplete_by_id(assign['id'])
            reply = f"Marked assignment '{assign['title']}' as incomplete." if success else f"Attempted to unmark assignment '{assign['title']}' as complete, but failed."
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
                reply = f"No assignment found with title matching '{title}' to log study time."
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            sid = self.study_session_dao.add_study_session(assign['id'], datetime.now(), int(duration), notes=parsed.get('notes'))
            reply = f"Logged {duration} minutes of study time, associated with assignment: {assign['title']} (session_id: {sid})."
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
                reply = f"No assignment found with title matching '{title}' to delete study session."
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            sessions = self.study_session_dao.get_sessions_by_assignment_id(assign['id'])
            if not sessions:
                reply = f"No study sessions found associated with assignment '{assign['title']}'."
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            # 删除最新的学习记录
            latest_session = sessions[-1]
            self.study_session_dao.delete_study_session_by_id(latest_session['id'])
            reply = f"Deleted the latest study session for assignment '{assign['title']}' (session_id: {latest_session['id']})."
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        elif action == 'list_pending':
            pending = self.assignment_dao.get_pending_by_user(user_id)
            if not pending:
                reply = "No pending assignments."
            else:
                lines = [f"- [{p.get('course_name')}] {p.get('title')} due: {p.get('due_date')}, description: {p.get('description', 'none')}, notes: {p.get('notes', 'none')}, attachment: {p.get('assignment_path', 'none')}" for p in pending]
                # Get user's study session stats
                study_stats = self.study_session_dao.get_study_session_stats(user_id, days=30)
                stats_text = f"User's recent 30-day study stats: total study hours {study_stats['total_study_hours']} hours, average per session {study_stats['avg_duration']} minutes, active days {study_stats['active_days']} days."
                brief_sys = "You are a schedule planning assistant. Based on the following pending items (including descriptions, notes, attachments) and the user's study history, generate a personalized study plan (3-5 suggestions). Try to parse attachments to understand requirements, time arrangements, etc. Reply in English."
                brief_user = stats_text + "\n\nPending items:\n" + "\n".join(lines)
                suggestion = self.call_llm(brief_sys, brief_user)
                reply = "Pending assignments:\n" + "\n".join(lines) + "\n\nSuggested plan:\n" + suggestion
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
                reply = "Invalid month format, please enter something like '11'."
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            assignments = self.assignment_dao.get_assignments_by_date_range(user_id, start_date, end_date)
            study_sessions = self.study_session_dao.get_study_sessions_by_date_range(user_id, start_date, end_date)

            assign_text = "\n".join([f"- {a['title']} ({a['course_name']}) due: {a['due_date']}, status: {a['status']}, description: {a.get('description', 'none')}, notes: {a.get('notes', 'none')}, attachment: {a.get('assignment_path', 'none')}" for a in assignments])
            session_text = "\n".join([f"- {s['assignment_title']} ({s['course_name']}) duration: {s['duration_minutes']} minutes, time: {s['start_time']}, notes: {s.get('notes', 'none')}" for s in study_sessions])

            plan_sys = "You are a time management assistant. Based on the user's assignments (including descriptions, notes, attachments) and study records (including notes), generate a detailed plan for month X, including a text-based Gantt chart (represented with characters like [Task] [-----] 1-5). Try to parse attachments to understand requirements, time arrangements, etc. Reply in English."
            plan_user = f"{month} month assignments:\n{assign_text}\n\nStudy records:\n{session_text}"
            plan = self.call_llm(plan_sys, plan_user)
            reply = f"{month} month schedule plan:\n{plan}"
            self._append_conversation(user_id, 'assistant', reply)
            return ChatResult(reply=reply)

        elif action == 'generate_course_plan':
            course_name = parsed.get('course_name')
            if not course_name:
                reply = "Course name cannot be empty."
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            # Get assignments for the course
            all_assignments = self.assignment_dao.get_assignments_by_date_range(user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365))
            course_assignments = [a for a in all_assignments if a.get('course_name') and course_name.lower() in a.get('course_name').lower()]

            # Get study sessions for the course
            all_sessions = self.study_session_dao.get_study_sessions_by_date_range(user_id, datetime.now() - timedelta(days=365), datetime.now() + timedelta(days=365))
            course_sessions = [s for s in all_sessions if s.get('course_name') and course_name.lower() in s.get('course_name').lower()]

            assign_text = "\n".join([f"- {a['title']} due: {a['due_date']}, status: {a['status']}, description: {a.get('description', 'none')}, notes: {a.get('notes', 'none')}, attachment: {a.get('assignment_path', 'none')}" for a in course_assignments])
            session_text = "\n".join([f"- {s['assignment_title']} duration: {s['duration_minutes']} minutes, time: {s['start_time']}, notes: {s.get('notes', 'none')}" for s in course_sessions])

            plan_sys = "You are a course planning assistant. Based on the user's assignments (including descriptions, notes, attachments) and study records (including notes), generate a detailed study plan for course X, including time arrangements, priorities, and suggestions. Reply in English."
            plan_user = f"{course_name} assignments:\n{assign_text}\n\nStudy records:\n{session_text}"
            plan = self.call_llm(plan_sys, plan_user)
            reply = f"{course_name} course study plan:\n{plan}"
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
                reply = f"No assignment found with title matching '{title}' to add note."
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            success = self.assignment_dao.update_notes_by_id(assign['id'], note)
            reply = f"Added note to assignment '{assign['title']}'." if success else f"Attempted to add note to assignment '{assign['title']}', but failed."
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
                reply = f"No assignment found with title matching '{title}' to upload attachment."
                self._append_conversation(user_id, 'assistant', reply)
                return ChatResult(reply=reply)

            success = self.assignment_dao.update_path_by_id(assign['id'], path)
            reply = f"Uploaded attachment to assignment '{assign['title']}', path: {path}." if success else f"Attempted to upload attachment to assignment '{assign['title']}', but failed."
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
        system_prompt = """You are an intelligent learning planning assistant. Based on the user's tasks and existing learning data, generate reasonable schedule suggestions.

Please consider:
1. Task priority and complexity
2. Reasonable time allocation
3. Learning efficiency suggestions
4. Specific execution steps

Reply in English, clear and readable format."""

        tasks_text = "\n".join([f"- {task}" for task in tasks])
        assignments_text = "\n".join([
            f"- {a.get('title', '')} (due: {a.get('due_date')}, status: {a.get('status', 'pending')})"
            for a in relevant_data['assignments'][:10]
        ])

        user_prompt = f"""Please generate a schedule for the following learning tasks:

Pending tasks:
{tasks_text}

Existing assignments:
{assignments_text}

Time range: {relevant_data['date_range']['start'].strftime('%Y-%m-%d')} to {relevant_data['date_range']['end'].strftime('%Y-%m-%d')}

Please provide a practical learning plan, including time arrangements and priority suggestions."""

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
            'date_range': f"{relevant_data['date_range']['start'].strftime('%Y-%m-%d')} to {relevant_data['date_range']['end'].strftime('%Y-%m-%d')}"
        })

        return ScheduleResult(schedule=schedule_items)

    def _create_fallback_schedule(self, relevant_data: Dict, tasks: List[str]) -> "ScheduleResult":
        schedule_items = []
        schedule_items.append({
            'type': 'info',
            'content': 'Schedule based on existing data (AI planning not available)'
        })
        for i, task in enumerate(tasks):
            schedule_items.append({
                'type': 'task',
                'title': task,
                'order': i + 1,
                'suggested_time': f'Day {i + 1}'
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
        system_prompt = """You are an intelligent learning planning assistant. Please analyze the user's schedule query request, understand their deep intentions and needs.

Please analyze the following:
1. Main intent (exam preparation, assignment planning, learning arrangements, review plans, etc.)
2. Time urgency level
3. User's possible hidden needs
4. Recommended planning strategies

Return JSON format: {
    "intent": "exam_preparation|assignment_planning|learning_arrangements|review_plans",
    "urgency": "high|medium|low",
    "time_range": {"start": "...", "end": "..."},
    "hidden_needs": ["..."],
    "planning_strategy": "...",
    "focus_courses": ["course names"],
    "priority_tasks": ["task types"]
}"""

        user_prompt = f"""
User query: {query}
Time range: {date_range}
User ID: {user_id}

Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Please analyze this schedule query request.
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
