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

from datetime import datetime
from typing import Dict, List
import requests
import json

from dao import (
    UserCourseDAO,
    CourseDAO, AssignmentDAO,
    StudySessionDAO
)
from models import ActionInput, ActionResult, ScheduleResult, ScheduleInput


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
    def openai_api(api_key: str, model: str = "gpt-4") -> "LLMConfig":
        return LLMConfig(provider="openai", api_key=api_key, model=model, base_url="https://api.openai.com/v1")

    @staticmethod
    def local_ollama(base_url: str = "http://localhost:11434", model: str = "qwen2:7b") -> "LLMConfig":
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

        # 配置 LLM
        if llm_config:
            self.llm_config = llm_config
        elif openai_api_key:
            self.llm_config = LLMConfig.openai_api(openai_api_key)
        else:
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
        """调用 OpenAI API"""
        import openai
        openai.api_key = self.llm_config.api_key
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
        """调用本地 Ollama"""
        url = f"{self.llm_config.base_url}/api/chat"
        payload = {
            "model": self.llm_config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.llm_config.temperature,
            "stream": False
        }
        response = requests.post(url, json=payload, timeout=self.llm_config.timeout)
        if response.status_code == 200:
            return response.json()['message']['content']
        else:
            raise Exception(f"Ollama API 错误: {response.status_code}")

    def _call_vllm(self, system_prompt: str, user_prompt: str) -> str:
        """调用本地 vLLM"""
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
        """调用本地通用 API"""
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
        """动态更新 LLM 配置（后期可修改，无需重新初始化）"""
        for key, value in kwargs.items():
            if hasattr(self.llm_config, key):
                setattr(self.llm_config, key, value)

    def get_llm_config(self) -> Dict:
        """获取当前 LLM 配置"""
        return self.llm_config.to_dict()

    #
    # def chat(self, user_id: int, message: str) -> str:
    #
    # # ================================================================
    # # 新增方法：suggest() - 提供学习建议
    # # ================================================================
    #
    # def suggest(self, task_desc: str, resources: List[str] = None, user_id: int = None) -> Dict:
    #
    #
    # # ================================================================
    # # 新增方法：schedule() - 生成日程安排
    # # ================================================================
    #

    # python
    def schedule(self, scheduleInput: "ScheduleInput") -> "ScheduleResult":
        """
        智能日程安排Agent - 使用配置的LLM进行智能规划
        """
        try:
            user_id = getattr(scheduleInput, 'user_id', None)
            tasks = getattr(scheduleInput, 'tasks', [])
            date_range = getattr(scheduleInput, 'date_range', None)

            if not user_id:
                return ScheduleResult(schedule=[{
                    'type': 'error',
                    'content': '需要用户ID'
                }])

            print(f"🔍 开始智能日程规划 - 用户: {user_id}, 任务数: {len(tasks)}")
            print(f"🤖 使用模型: {self.llm_config.model}")

            # 1. 获取基础数据
            relevant_data = self._get_relevant_data(user_id, date_range)

            # 2. 使用LLM生成智能规划（如果LLM可用）
            if self.llm_config.provider != "unknown":
                try:
                    ai_plan = self._generate_intelligent_plan(tasks, relevant_data, user_id)
                    return self._create_ai_schedule_response(ai_plan, relevant_data, tasks)
                except Exception as e:
                    print(f"⚠️ LLM规划失败，使用回退方案: {e}")
                    return self._create_fallback_schedule(relevant_data, tasks)
            else:
                # LLM不可用，使用规则基础方案
                return self._create_rule_based_schedule(relevant_data, tasks)

        except Exception as e:
            print(f"❌ 日程规划错误: {e}")
            return ScheduleResult(schedule=[{
                'type': 'error',
                'content': f'规划失败: {str(e)}'
            }])

    def _get_relevant_data(self, user_id: int, date_range: str) -> Dict:
        """
        获取相关数据
        """
        from datetime import datetime, timedelta

        # 解析日期范围
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
        """使用LLM生成智能规划"""

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
            for a in relevant_data['assignments'][:5]  # 限制数量避免过长
        ])

        user_prompt = f"""请为以下学习任务生成日程安排：

    待办任务：
    {tasks_text}

    现有作业：
    {assignments_text}

    时间范围：{relevant_data['date_range']['start'].strftime('%Y-%m-%d')} 到 {relevant_data['date_range']['end'].strftime('%Y-%m-%d')}

    请提供一个实用的学习计划，包括时间安排和优先级建议。"""

        print("🧠 调用LLM生成智能规划...")
        ai_response = self.call_llm(system_prompt, user_prompt)

        return {
            'ai_recommendation': ai_response,
            'tasks_analyzed': len(tasks),
            'assignments_considered': len(relevant_data['assignments'])
        }

    def _create_ai_schedule_response(self, ai_plan: Dict, relevant_data: Dict, tasks: List[str]) -> "ScheduleResult":
        """创建AI增强的日程响应"""

        schedule_items = []

        # 1. AI建议
        schedule_items.append({
            'type': 'ai_recommendation',
            'content': ai_plan['ai_recommendation'],
            'source': 'llm',
            'tasks_analyzed': ai_plan['tasks_analyzed']
        })

        # 2. 具体任务安排
        for i, task in enumerate(tasks):
            schedule_items.append({
                'type': 'scheduled_task',
                'task_id': i + 1,
                'title': task,
                'suggested_order': i + 1,
                'estimated_duration_minutes': 60,  # 默认1小时
                'priority': 'high' if i == 0 else 'medium'
            })

        # 3. 数据统计
        schedule_items.append({
            'type': 'summary',
            'total_tasks': len(tasks),
            'upcoming_assignments': len(relevant_data['assignments']),
            'study_sessions': len(relevant_data['study_sessions']),
            'date_range': f"{relevant_data['date_range']['start'].strftime('%Y-%m-%d')} 到 {relevant_data['date_range']['end'].strftime('%Y-%m-%d')}"
        })

        return ScheduleResult(schedule=schedule_items)

    def _create_fallback_schedule(self, relevant_data: Dict, tasks: List[str]) -> "ScheduleResult":
        """LLM失败时的回退方案"""
        schedule_items = []

        schedule_items.append({
            'type': 'info',
            'content': '基于现有数据的日程安排（AI规划暂不可用）'
        })

        # 简单的任务安排
        for i, task in enumerate(tasks):
            schedule_items.append({
                'type': 'task',
                'title': task,
                'order': i + 1,
                'suggested_time': f'第{i + 1}天'
            })

        return ScheduleResult(schedule=schedule_items)

    def _analyze_schedule_intent(self, query: str, date_range: str, user_id: int) -> Dict:
        """使用LLM分析用户查询的深层意图"""

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
        except:
            # 如果LLM返回非JSON，使用规则回退
            return self._fallback_intent_analysis(query, date_range)

    def _fallback_intent_analysis(self, query: str, date_range: str) -> Dict:
        """Fallback method for intent analysis if LLM fails."""
        return {
            "intent": "general",
            "urgency": "medium",
            "time_range": {"start": date_range.split(' to ')[0], "end": date_range.split(' to ')[1]},
            "hidden_needs": [],
            "planning_strategy": "rule_based",
            "focus_courses": [],
            "priority_tasks": []
        }

    def _calculate_time_range_based_on_urgency(self, urgency: str) -> int:
        """Calculate the number of days to look ahead based on urgency."""
        if urgency == "high":
            return 7
        elif urgency == "medium":
            return 14
        else:
            return 30

    def _get_exam_preparation_sessions(self, user_id: int, focus_courses: List[str]) -> List[Dict]:
        """Retrieve study sessions focused on exam preparation."""
        return self.study_session_dao.get_sessions_by_courses(user_id, focus_courses) if hasattr(self.study_session_dao, 'get_sessions_by_courses') else []

    def _analyze_study_patterns(self, study_sessions: List[Dict]) -> str:
        """Analyze study patterns from past sessions."""
        if not study_sessions:
            return "No recent study patterns available."
        total_hours = sum(session.get("duration", 0) for session in study_sessions)
        return f"Total study hours: {total_hours}"

    def _get_user_learning_profile(self, user_id: int) -> str:
        """Retrieve the user's learning profile."""
        return self.user_course_dao.get_learning_profile(user_id) if hasattr(self.user_course_dao, 'get_learning_profile') else "Default Profile"

    def _calculate_confidence(self, intent_analysis: Dict, relevant_data: Dict) -> float:
        """Calculate confidence score for the generated plan."""
        return 0.9 if intent_analysis.get("intent") == "exam_preparation" else 0.7

    def _extract_structured_plan(self, ai_recommendations: str) -> List[Dict]:
        """Extract structured plan items from AI recommendations."""
        # Placeholder logic for parsing AI recommendations
        return [{"task": "Example Task", "time": "10:00 AM", "priority": "high", "duration": "1 hour", "reasoning": "Example reasoning."}]

    def _calculate_recent_study_hours(self, study_sessions: List[Dict]) -> int:
        """Calculate total recent study hours."""
        return sum(session.get("duration", 0) for session in study_sessions)

    def action(self, action_input: ActionInput) -> ActionResult:
        """
        Handle user actions dynamically, such as marking assignments complete,
        querying pending tasks, or generating study plans.
        """
        try:
            action = action_input.action
            data = action_input.data

            if action == "mark_assignment_complete":
                assignment_id = data.get("assignment_id")
                user_id = data.get("user_id")
                if not assignment_id or not user_id:
                    return ActionResult(status="error", message="Missing assignment_id or user_id")

                success = self.assignment_dao.mark_complete(assignment_id, user_id)
                if success:
                    return ActionResult(status="success", message="Assignment marked as complete")
                else:
                    return ActionResult(status="error", message="Failed to mark assignment as complete")

            elif action == "query_pending_assignments":
                user_id = data.get("user_id")
                if not user_id:
                    return ActionResult(status="error", message="Missing user_id")

                pending_assignments = self.assignment_dao.get_pending_by_user(user_id) if hasattr(self.assignment_dao, 'get_pending_by_user') else []
                return ActionResult(status="success", data={"pending_assignments": pending_assignments})

            elif action == "generate_study_plan":
                schedule_input = ScheduleInput(**data)
                schedule_result = self.schedule(schedule_input)
                return ActionResult(status="success", data={"schedule": schedule_result.schedule})

            else:
                return ActionResult(status="error", message=f"Unknown action: {action}")

        except Exception as e:
            return ActionResult(status="error", message=f"Action failed: {str(e)}")

    def schedule(self, scheduleInput: ScheduleInput) -> ScheduleResult:
        """
        Generate a study schedule based on assignments and study sessions.
        """
        try:
            user_id = scheduleInput.user_id
            tasks = scheduleInput.tasks
            date_range = scheduleInput.date_range

            if not user_id:
                return ScheduleResult(schedule=[{"type": "error", "content": "User ID is required"}])

            # Fetch relevant data
            relevant_data = self._get_relevant_data(user_id, date_range)

            # Generate intelligent plan using LLM
            try:
                ai_plan = self._generate_intelligent_plan(tasks, relevant_data, user_id)
                return self._create_ai_schedule_response(ai_plan, relevant_data, tasks)
            except Exception as e:
                print(f"LLM planning failed, falling back to rule-based scheduling: {e}")
                return self._create_rule_based_schedule(relevant_data, tasks)

        except Exception as e:
            print(f"Schedule generation error: {e}")
            return ScheduleResult(schedule=[{"type": "error", "content": f"Failed to generate schedule: {str(e)}"}])

    def _get_relevant_data(self, user_id: int, date_range: str) -> Dict:
        """
        Fetch assignments and study sessions within the specified date range.
        """
        from datetime import datetime, timedelta

        # Parse date range
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
            "date_range": {"start": start_date, "end": end_date}
        }

    def _create_rule_based_schedule(self, relevant_data: Dict, tasks: List[str]) -> "ScheduleResult":
        """Fallback rule-based schedule creation."""
        schedule_items = []
        for i, task in enumerate(tasks):
            schedule_items.append({
                'type': 'task',
                'title': task,
                'order': i + 1,
                'suggested_time': f'Day {i + 1}'
            })
        return ScheduleResult(schedule=schedule_items)
