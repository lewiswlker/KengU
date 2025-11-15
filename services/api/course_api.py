from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dao import CourseDAO, UserCourseDAO, UserDAO
from agents import update_knowledge_base
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional

router = APIRouter(tags=["course"])

# 任务状态存储（新增进度相关字段）
task_status: Dict[str, Dict[str, Any]] = {}


# 数据模型保持不变
class UpdateKnowledgeBaseRequest(BaseModel):
    email: str
    password: str
    id: int

class GetUserCoursesRequest(BaseModel):
    email: str

class TaskStatusRequest(BaseModel):
    task_id: str


@router.post("/update-data")
async def api_update_knowledge_base(
    request: UpdateKnowledgeBaseRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    # 参数校验
    if not request.email:
        raise HTTPException(status_code=400, detail={"success": False, "error": "Missing email"})
    if not request.password:
        raise HTTPException(status_code=400, detail={"success": False, "error": "Missing password"})
    if not request.id:
        raise HTTPException(status_code=400, detail={"success": False, "error": "Missing id"})

    user_id = int(request.id)
    task_id = str(uuid.uuid4())
    
    # 初始化任务状态（预设步骤和进度占比）
    task_status[task_id] = {
        "status": "running",
        "percent": 0,
        "message": "准备更新...",
        "result": None,
        "error": None,
        "start_time": datetime.now().isoformat(),
        "completed": False,
        "failed": False
    }

    # 定义带进度估算的后台任务
    def run_update_with_estimated_progress():
        try:
            # 步骤1：登录验证（10%）
            task_status[task_id].update({
                "percent": 10,
                "message": "验证用户身份..."
            })
            time.sleep(2)  # 模拟登录耗时（根据实际情况调整）

            # 步骤2：执行Moodle爬取（20%-50%）
            task_status[task_id].update({
                "percent": 20,
                "message": "开始爬取Moodle课程..."
            })
            # 记录开始时间，用于估算进度
            moodle_start = time.time()
            
            # 执行核心更新（不修改原函数，仅在外部跟踪时间）
            result = update_knowledge_base(
                user_id=user_id,
                user_email=request.email,
                user_password=request.password,
                headless=True,
                verbose=True
            )
            
            # 步骤3：处理Exambase（50%-80%）
            task_status[task_id].update({
                "percent": 50,
                "message": "开始处理Exambase数据..."
            })
            exambase_start = time.time()
            # 假设Exambase处理耗时约为Moodle的0.6倍（根据实际情况调整）
            moodle_duration = exambase_start - moodle_start
            time.sleep(min(3, moodle_duration * 0.6))  # 估算耗时

            # 步骤4：保存数据（80%-100%）
            task_status[task_id].update({
                "percent": 80,
                "message": "保存课程数据..."
            })
            time.sleep(1)  # 模拟保存耗时

            # 完成
            task_status[task_id].update({
                "status": "completed",
                "percent": 100,
                "message": "更新完成",
                "result": result,
                "completed": True
            })

        except Exception as e:
            task_status[task_id].update({
                "status": "failed",
                "message": f"更新失败: {str(e)}",
                "error": str(e),
                "failed": True
            })

    background_tasks.add_task(run_update_with_estimated_progress)
    return {
        "success": True,
        "message": "更新任务已启动",
        "task_id": task_id
    }


@router.post("/update-status")
async def get_update_status(request: TaskStatusRequest) -> Dict[str, Any]:
    task_id = request.task_id
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail={"success": False, "error": "任务ID不存在"})
    
    status = task_status[task_id]
    return {
        "success": True,
        "task_id": task_id,
        "status": status["status"],
        "percent": status["percent"],
        "message": status["message"],
        "result": status["result"],
        "error": status["error"],
        "completed": status["completed"],
        "failed": status["failed"]
    }

@router.post("/user/courses")
async def get_user_courses(request: GetUserCoursesRequest):
    email = request.email
    if not email:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": "email is required (请提供邮箱)"}
        )
    
    if not (email.endswith("@connect.hku.hk") or email.endswith("@hku.hk")):
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": "invalid email (请使用HKU邮箱)"}
        )

    try:
        user_dao = UserDAO()
        user = user_dao.find_by_email(email)
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "message": "user not found (该用户不存在)"}
            )
        user_id = user["id"]

        user_course_dao = UserCourseDAO()
        course_dao = CourseDAO()

        user_course_records = user_course_dao.find_user_courses_by_userid(user_id)
        course_ids = [record["course_id"] for record in user_course_records]
        
        if not course_ids:
            return {
                "success": True,
                "message": "该用户暂无课程",
                "data": []
            }

        courses = []
        for course_id in course_ids:
            course_name = course_dao.find_name_by_id(course_id)
            if course_name:
                moodle_time, exambase_time = course_dao.find_update_time_byid(course_id)
                courses.append({
                    "id": course_id,
                    "name": course_name,
                    "update_time_moodle": moodle_time.isoformat() if moodle_time else None,
                    "update_time_exambase": exambase_time.isoformat() if exambase_time else None
                })

        return {
            "success": True,
            "message": f"成功获取{len(courses)}门课程",
            "data": courses
        }

    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": f"获取课程失败：{str(e)}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": f"服务器错误：{str(e)}"}
        )