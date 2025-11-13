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

from datetime import datetime, timedelta,date as _date
from typing import Dict, List, Optional, Any
import requests
import json
import re


from dao import (
    UserCourseDAO,
    CourseDAO, AssignmentDAO,
StudySessionDAO
)
from models import ActionInput, ActionResult, ScheduleResult,ScheduleInput,ProgressQuery,ProgressResult


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
        """获取相关数据"""
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

    def _intelligent_data_retrieval(self, intent_analysis: Dict, user_id: int) -> Dict:
        """基于意图分析智能检索相关数据"""

        # 根据分析结果动态调整查询策略
        intent = intent_analysis.get('intent', '')
        focus_courses = intent_analysis.get('focus_courses', [])
        urgency = intent_analysis.get('urgency', '中')

        # 动态计算时间范围
        days_to_look = self._calculate_time_range_based_on_urgency(urgency)
        end_date = datetime.now() + timedelta(days=days_to_look)

        # 获取基础数据
        assignments = self.assignment_dao.get_assignments_by_date_range(
            user_id, datetime.now(), end_date
        )

        study_sessions = self.study_session_dao.get_study_sessions_by_date_range(
            user_id, datetime.now(), end_date
        )

        # 根据意图过滤和增强数据
        if intent == "考试准备":
            exams = self.assignment_dao.get_assignments_by_type(user_id, 'exam')
            # 获取相关的学习历史
            exam_prep_sessions = self._get_exam_preparation_sessions(user_id, focus_courses)
            return {
                "assignments": exams,
                "study_sessions": exam_prep_sessions,
                "data_type": "exam_focused"
            }

        elif intent == "作业规划":
            # 重点关注pending状态的作业
            pending_assignments = [a for a in assignments if a.get('status') != 'completed']
            return {
                "assignments": pending_assignments,
                "study_sessions": study_sessions,
                "data_type": "homework_focused"
            }

        else:
            return {
                "assignments": assignments,
                "study_sessions": study_sessions,
                "data_type": "general"
            }

    def _generate_ai_schedule(self, intent_analysis: Dict, relevant_data: Dict, user_id: int) -> Dict:
        """使用LLM生成智能日程规划"""

        system_prompt = """你是专业的学习规划专家。基于用户的学习数据和查询意图，生成个性化的日程安排建议。

    请考虑：
    1. 任务的优先级和截止日期
    2. 学习历史的模式和效率
    3. 合理的时间分配和休息安排
    4. 具体可执行的行动建议

    返回结构化的日程规划。"""

        # 准备上下文数据
        context_data = {
            "intent_analysis": intent_analysis,
            "upcoming_assignments": relevant_data.get("assignments", [])[:10],  # 限制数量
            "recent_study_patterns": self._analyze_study_patterns(relevant_data.get("study_sessions", [])),
            "user_learning_profile": self._get_user_learning_profile(user_id)
        }

        user_prompt = f"""
    基于以下信息为用户生成智能日程安排：

    用户意图分析: {intent_analysis}
    近期任务: {[f"{a['title']} (截止: {a.get('due_date')})" for a in context_data['upcoming_assignments']]}
    学习模式: {context_data['recent_study_patterns']}
    用户学习特征: {context_data['user_learning_profile']}

    请生成一个具体、可行、个性化的日程安排计划。
    """

        ai_response = self.call_llm(system_prompt, user_prompt)

        return {
            "ai_recommendations": ai_response,
            "reasoning": "基于学习数据和用户意图的智能规划",
            "confidence_score": self._calculate_confidence(intent_analysis, relevant_data)
        }

    def _format_schedule_response(self, ai_schedule: Dict, relevant_data: Dict,
                                  intent_analysis: Dict) -> "ScheduleResult":
        """格式化最终的智能响应"""

        schedule_items = []

        # 1. 添加AI生成的建议
        schedule_items.append({
            'type': 'ai_recommendation',
            'content': ai_schedule.get("ai_recommendations", ""),
            'intent': intent_analysis.get("intent"),
            'confidence': ai_schedule.get("confidence_score", 0.7),
            'strategy': intent_analysis.get("planning_strategy")
        })

        # 2. 添加具体任务安排（基于AI建议进一步结构化）
        structured_plan = self._extract_structured_plan(ai_schedule.get("ai_recommendations", ""))
        for plan_item in structured_plan:
            schedule_items.append({
                'type': 'scheduled_task',
                'title': plan_item.get('task'),
                'suggested_time': plan_item.get('time'),
                'priority': plan_item.get('priority'),
                'estimated_duration': plan_item.get('duration'),
                'reasoning': plan_item.get('reasoning')
            })

        # 3. 添加数据支撑
        schedule_items.append({
            'type': 'data_backing',
            'upcoming_count': len(relevant_data.get("assignments", [])),
            'recent_study_hours': self._calculate_recent_study_hours(relevant_data.get("study_sessions", [])),
            'urgency_level': intent_analysis.get("urgency")
        })

        return ScheduleResult(schedule=schedule_items)

    def _calculate_time_range_based_on_urgency(self, urgency: str) -> int:
        """根据紧急程度动态调整查询时间范围"""
        urgency_map = {
            '高': 7,  # 只关注最近7天
            '中': 30,  # 关注一个月
            '低': 90  # 关注一个季度
        }
        return urgency_map.get(urgency, 30)

    def _analyze_study_patterns(self, study_sessions: List[Dict]) -> Dict:
        """分析用户的学习模式"""
        if not study_sessions:
            return {"pattern": "无足够数据", "efficiency": "未知"}

        # 简单的模式分析（实际可以更复杂）
        total_duration = sum(s.get('duration_minutes', 0) for s in study_sessions)
        avg_duration = total_duration / len(study_sessions) if study_sessions else 0

        return {
            "average_session_length": f"{avg_duration:.1f}分钟",
            "total_sessions": len(study_sessions),
            "pattern": "规律学习" if len(study_sessions) > 5 else "偶尔学习"
        }

    # def knowledge(self, query: str, user_id: int = None) -> Dict:



    # mark_assignment_complete

    def action(self, action_input:ActionInput) -> ActionResult:
        if isinstance(action_input, dict):
            action = action_input.get("action")
            data = action_input.get("data")
        else:
            action = getattr(action_input, "action", None)
            data = getattr(action_input, "data", None)
        """
        Support transactional 'mark_assignment_complete'.
        Expected data: {'assignment_id': int, 'user_id': int}
        """
        try:
            if action == "mark_assignment_complete":
                if not data:
                    return {"status": "error", "message": "missing data"}
                aid = data.get('assignment_id')
                user_id = data.get('user_id')
                if not aid or not user_id:
                    return {"status": "error", "message": "assignment_id and user_id required"}

                raw_conn = self.assignment_dao.get_connection()

                # helper to run transaction given a real connection object
                def _run_with_conn(conn):
                    try:
                        conn.begin()
                        updated = self.assignment_dao.mark_complete(conn, assignment_id=aid)
                        success = bool(updated[0]) if isinstance(updated, (list, tuple)) else bool(updated)
                        if not success:
                            conn.rollback()
                            return {"status": "error", "message": "assignment not found or already completed"}

                        try:
                            if hasattr(self.task_tracking_dao, "adjust_counters"):
                                self.task_tracking_dao.adjust_counters(conn, user_id=user_id, delta_completed=1, delta_pending=-1)
                            else:
                                try:
                                    cursor_args = ()
                                    with conn.cursor(*cursor_args) as cur:
                                        cur.execute(
                                            "UPDATE task_tracking SET completed = COALESCE(completed,0) + %s, pending = COALESCE(pending,0) + %s WHERE user_id = %s",
                                            (1, -1, user_id)
                                        )
                                        if getattr(cur, "rowcount", 0) == 0:
                                            try:
                                                cur.execute(
                                                    "INSERT INTO task_tracking (user_id, completed, pending) VALUES (%s, %s, %s)",
                                                    (user_id, 1, 0)
                                                )
                                            except Exception:
                                                pass
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        try:
                            self.agent_interaction_dao.insert(conn=conn,
                                                             user_id=user_id,
                                                             user_message=f"标记作业 {aid} 为完成",
                                                             ai_response="(system) assignment marked complete",
                                                             ai_model=getattr(self.llm_config, 'model', None))
                        except TypeError:
                            try:
                                self.agent_interaction_dao.insert(user_id=user_id,
                                                                 user_message=f"标记作业 {aid} 为完成",
                                                                 ai_response="(system) assignment marked complete",
                                                                 ai_model=getattr(self.llm_config, 'model', None))
                            except Exception:
                                pass
                        except Exception:
                            pass

                        conn.commit()
                        return {"status": "success", "message": "assignment marked complete"}
                    except Exception as tx_e:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        return {"status": "error", "message": f"transaction failed: {tx_e}"}
                    finally:
                        try:
                            conn.close()
                        except Exception:
                            pass

                # If DAO returned a context-manager, use it to obtain the real conn
                if hasattr(raw_conn, "__enter__") and hasattr(raw_conn, "__exit__"):
                    try:
                        with raw_conn as conn:
                            return _run_with_conn(conn)
                    except Exception as e:
                        # raw_conn context manager failed before yielding or _run_with_conn returned error
                        return {"status": "error", "message": str(e)}
                else:
                    # raw_conn is already a real connection object
                    return _run_with_conn(raw_conn)

            return {"status": "error", "message": f"unknown action {action_type}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def progress(self, query: ProgressQuery) -> ProgressResult:
        """
        进度与统计查询
        输入：用户ID等查询条件
        返回：已完成、待办、总任务
        """
        try:
            user_id = getattr(query, 'user_id', None)

            if not user_id:
                return ProgressResult(
                    completed=0,
                    pending=0,
                    total=0,
                    details=[{"error": "需要用户ID"}]
                )

            print(f"📊 查询用户 {user_id} 的学习进度...")

            # 使用DAO获取各类数据
            assignment_stats = self.assignment_dao.get_assignment_progress_stats(user_id)
            study_stats = self.study_session_dao.get_study_session_stats(user_id)
            course_progress = self.user_course_dao.get_course_progress(user_id)
            upcoming_assignments = self.assignment_dao.get_upcoming_assignments(user_id)

            # 计算总体进度
            total_completed = assignment_stats['completed']
            total_pending = assignment_stats['pending']
            total_tasks = total_completed + total_pending

            # 构建详细信息
            details = self._build_progress_details(
                assignment_stats, study_stats, course_progress, upcoming_assignments
            )

            print(f"✅ 进度统计完成: 已完成 {total_completed}, 待办 {total_pending}, 总计 {total_tasks}")

            return ProgressResult(
                completed=total_completed,
                pending=total_pending,
                total=total_tasks,
                details=details
            )

        except Exception as e:
            print(f"❌ 进度查询错误: {e}")
            return ProgressResult(
                completed=0,
                pending=0,
                total=0,
                details=[{"error": f"进度查询失败: {str(e)}"}]
            )

    # 在 planner_agent.py 的 PlannerAgent 类中添加以下方法

    def _build_progress_details(self, assignment_stats: Dict, study_stats: Dict,
                                course_progress: List[Dict], upcoming_assignments: List[Dict]) -> List[Dict]:
        """构建进度详细信息"""
        details = []

        # 1. 总体统计
        completion_rate = round((assignment_stats['completed'] / assignment_stats['total'] * 100), 1) if \
        assignment_stats['total'] > 0 else 0

        details.append({
            'type': 'overall_stats',
            'total_assignments': assignment_stats['total'],
            'completed_assignments': assignment_stats['completed'],
            'pending_assignments': assignment_stats['pending'],
            'completion_rate': completion_rate
        })

        # 2. 学习活动统计
        details.append({
            'type': 'study_activity',
            'total_sessions': study_stats['total_sessions'],
            'total_study_hours': study_stats['total_study_hours'],
            'average_session_minutes': study_stats['avg_duration'],
            'active_days': study_stats['active_days'],
            'period_days': study_stats['period_days']
        })

        # 3. 各课程进度
        if course_progress:
            details.append({
                'type': 'course_progress',
                'courses': course_progress,
                'total_courses': len(course_progress)
            })

        # 4. 近期待办事项
        if upcoming_assignments:
            details.append({
                'type': 'upcoming_assignments',
                'count': len(upcoming_assignments),
                'assignments': upcoming_assignments[:5]  # 只显示最近5个
            })

        # 5. 学习建议
        suggestions = self._generate_progress_suggestions(assignment_stats, study_stats)
        details.append({
            'type': 'suggestions',
            'recommendations': suggestions
        })

        return details

    def _generate_progress_suggestions(self, assignment_stats: Dict, study_stats: Dict) -> List[str]:
        """生成进度建议"""
        suggestions = []

        completion_rate = (assignment_stats['completed'] / assignment_stats['total'] * 100) if assignment_stats[
                                                                                                   'total'] > 0 else 0

        if completion_rate < 50:
            suggestions.append("当前完成率较低，建议优先处理临近截止日期的作业")
        elif completion_rate > 80:
            suggestions.append("完成率很高！继续保持良好的学习节奏")

        if study_stats['total_sessions'] == 0:
            suggestions.append("最近30天没有学习记录，建议制定规律的学习计划")
        elif study_stats['active_days'] < 10:
            suggestions.append("学习天数较少，建议增加每周的学习频率")

        if assignment_stats['pending'] > 5:
            suggestions.append(f"当前有 {assignment_stats['pending']} 个待办作业，建议合理安排时间")

        if not suggestions:
            suggestions.append("学习进度良好，继续保持当前的学习节奏")

        return suggestions