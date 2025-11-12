from typing import List, Optional
from pydantic import BaseModel

# ===========================
# 接口参数和返回值定义（示例）
# ===========================

class SuggestInput(BaseModel):
    task_desc: str
    resources: Optional[List[str]] = None
    user_id: Optional[int] = None

class SuggestResult(BaseModel):
    plan_steps: List[str]
    ai_summary: Optional[str] = None

class ScheduleInput(BaseModel):
    tasks: List[str]
    date_range: Optional[str] = None
    user_id: Optional[int] = None

class ScheduleResult(BaseModel):
    schedule: List[dict]  # 含任务名、时间点等

class ProgressQuery(BaseModel):
    user_id: Optional[int] = None

class ProgressResult(BaseModel):
    completed: int
    pending: int
    total: int
    details: Optional[List[dict]] = None

class ChatInput(BaseModel):
    message: str
    user_id: Optional[int] = None
    context: Optional[dict] = None

class ChatResult(BaseModel):
    reply: str
    references: Optional[List[str]] = None

class KnowledgeInput(BaseModel):
    query: str
    user_id: Optional[int] = None

class KnowledgeResult(BaseModel):
    found: bool
    answer: str
    source: Optional[str] = None

class AssignInput(BaseModel):
    task_id: int
    assign_to: int

class AssignResult(BaseModel):
    success: bool
    detail: Optional[str] = None

class ActionInput(BaseModel):
    action: str
    data: Optional[dict] = None

class ActionResult(BaseModel):
    status: str
    message: Optional[str] = None



__all__ = [
    "SuggestInput", "SuggestResult",
    "ScheduleInput", "ScheduleResult",
    "ProgressQuery", "ProgressResult",
    "ChatInput", "ChatResult",
    "KnowledgeInput", "KnowledgeResult",
    "AssignInput", "AssignResult",
    "ActionInput", "ActionResult",
]