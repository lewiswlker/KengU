from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dao import CourseDAO, UserCourseDAO, UserDAO, AssignmentDAO
from planner_scraper.calendar import MoodleCalendarCrawler
from agents import update_knowledge_base
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional

router = APIRouter(tags=["course"])

# 任务状态存储（新增进度相关字段）
task_status: Dict[str, Dict[str, Any]] = {}

def convert_event_to_assignment(event, user_id=1):
    """Convert calendar event to assignment dict"""
    try:
        # Parse date
        due_date = datetime.strptime(event["date"], "%Y-%m-%d") if event.get("date") else None

        # Determine assignment type based on title/description
        title = event.get("title", "")
        description = event.get("description", "")
        assignment_type = "homework"  # default

        if "exam" in title.lower() or "exam" in description.lower():
            assignment_type = "exam"
        elif "quiz" in title.lower() or "quiz" in description.lower():
            assignment_type = "quiz"
        elif "project" in title.lower() or "project" in description.lower():
            assignment_type = "project"

        # Extract course_id from event
        course_id = int(event.get("course_id", 0)) if event.get("course_id") else None

        assignment = {
            "title": title,
            "description": description,
            "course_id": course_id,
            "user_id": user_id,
            "due_date": due_date,
            "status": "pending",  # Default status
            "assignment_type": assignment_type,
            "max_score": None,
            "instructions": description,
            "attachment_path": event.get("submit_link", "")
        }
        return assignment
    except Exception as e:
        print(f"Error converting event {event}: {e}")
        return None


# 数据模型保持不变
class UpdateKnowledgeBaseRequest(BaseModel):
    email: str
    password: str
    id: int

class GetUserCoursesRequest(BaseModel):
    email: str

class TaskStatusRequest(BaseModel):
    task_id: str

class GetUCoursesRequest(BaseModel):
    course_id: int

class EventRequest(BaseModel):
    user_email: str
    user_password: str
    start_date: str
    end_date: str
    user_id: int

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
                "message": "Verifying user identity..."
            })
            time.sleep(2)  # 模拟登录耗时（根据实际情况调整）

            # 步骤2：执行Moodle爬取（20%-50%）
            task_status[task_id].update({
                "percent": 20,
                "message": "Getting Moodle courses..."
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
                "message": "Solving Exambase data..."
            })
            exambase_start = time.time()
            # 假设Exambase处理耗时约为Moodle的0.6倍（根据实际情况调整）
            moodle_duration = exambase_start - moodle_start
            time.sleep(min(3, moodle_duration * 0.6))  # 估算耗时

            # 步骤4：保存数据（80%-100%）
            task_status[task_id].update({
                "percent": 80,
                "message": "Loading information..."
            })
            time.sleep(1)  # 模拟保存耗时

            # 完成
            task_status[task_id].update({
                "status": "completed",
                "percent": 100,
                "message": "Updating completed",
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
        "message": "Updating start",
        "task_id": task_id
    }


@router.post("/update-events")
async def get_events_update(
    request: EventRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Crawl calendar events and save to assignment table (with background task & progress tracking)"""
    # 提取请求参数
    username = request.user_email
    password = request.user_password
    user_id = request.user_id
    start_date = request.start_date
    end_date = request.end_date

    # 参数校验
    if not all([username, password, user_id, start_date, end_date]):
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Missing required parameters"}
        )

    # 生成任务ID并初始化进度状态
    task_id = str(uuid.uuid4())
    task_status[task_id] = {
        "status": "running",
        "percent": 0,
        "message": "准备爬取日历事件...",
        "result": None,
        "error": None,
        "start_time": datetime.now().isoformat(),
        "completed": False,
        "failed": False,
        "total_courses": 0,
        "processed_courses": 0
    }

    # 定义后台任务（带进度跟踪）
    def run_event_crawl():
        main_scraper = None
        try:
            # 步骤1：初始化爬虫（10%）
            task_status[task_id].update({
                "percent": 10,
                "message": "Initializing..."
            })
            main_scraper = MoodleCalendarCrawler(headless=True, verbose=False)

            # 步骤2：登录验证（20%）
            task_status[task_id].update({
                "percent": 20,
                "message": "Verifying Moodle account..."
            })
            if not main_scraper.connect_moodle(username, password):
                raise Exception("Moodle登录失败，请检查账号密码")

            # 步骤3：清理历史作业（30%）
            task_status[task_id].update({
                "percent": 30,
                "message": "清理历史作业数据..."
            })
            assignment_dao = AssignmentDAO()
            with assignment_dao.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM assignment WHERE user_id = %s", (user_id,))
                conn.commit()

            # 步骤4：获取课程列表（40%）
            task_status[task_id].update({
                "percent": 40,
                "message": "Getting user courses..."
            })

            start_time = time.time()
            while True:
                course_ids = main_scraper.get_course_ids_from_db(user_id)
                if course_ids:
                    break
                elapsed_time = time.time() - start_time
                if elapsed_time >= 1800:
                    break
                time.sleep(60)
            if not course_ids:
                task_status[task_id].update({
                    "status": "completed",
                    "percent": 100,
                    "message": "No courses",
                    "result": {"saved_count": 0, "total_events": 0},
                    "completed": True
                })
                return

            total_courses = len(course_ids)
            task_status[task_id].update({
                "total_courses": total_courses,
                "message": f"Find {total_courses} courses, start getting..."
            })

            # 步骤5：并发爬取课程事件（40%-90%）
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading

            all_events = []
            lock = threading.Lock()  # 线程安全锁

            def crawl_course(course_info):
                """单课程事件爬取（子线程）"""
                course_id = course_info['course_id']
                course_name = course_info['course_name']
                course_scraper = MoodleCalendarCrawler(headless=True, verbose=False)
                try:
                    # 子线程登录（Moodle会话不共享）
                    if not course_scraper.connect_moodle(username, password):
                        print(f"Course {course_id} failed to load, skip")
                        return []
                    
                    # 爬取事件
                    events = course_scraper.get_calendar_events(
                        start_date=start_date,
                        end_date=end_date,
                        course_id=str(course_id)
                    )
                    print(f"Course {course_id}（{course_name}）：get {len(events)} events")

                    # 更新进度（原子操作）
                    with lock:
                        task_status[task_id]["processed_courses"] += 1
                        processed = task_status[task_id]["processed_courses"]
                        # 进度计算：40% + (已处理/总课程)*50%（上限90%）
                        progress = 40 + (processed / total_courses) * 50
                        task_status[task_id].update({
                            "percent": min(90, int(progress)),
                            "message": f"Dealing：{course_name}（{processed}/{total_courses}）"
                        })
                    return events
                finally:
                    course_scraper.close()

            # 并发执行爬取（限制最大4线程，避免Moodle限流）
            with ThreadPoolExecutor(max_workers=min(total_courses, 4)) as executor:
                future_to_course = {
                    executor.submit(crawl_course, course): course 
                    for course in course_ids
                }
                for future in as_completed(future_to_course):
                    try:
                        events = future.result()
                        with lock:
                            all_events.extend(events)
                    except Exception as e:
                        course = future_to_course[future]
                        print(f"课程{course['course_id']}爬取异常：{str(e)}")

            # 步骤6：保存作业数据（90%-100%）
            task_status[task_id].update({
                "percent": 90,
                "message": f"Start storing information（{len(all_events)}events in total）..."
            })

            saved_count = 0
            for event in all_events:
                if event.get('event_type') == 'due' and event.get('component') in ['mod_assign', 'mod_turnitintooltwo']:
                    assignment = convert_event_to_assignment(event, user_id)
                    if assignment:
                        # 检查重复
                        existing = assignment_dao.get_assignments_by_date_range(
                            user_id, 
                            assignment['due_date'], 
                            assignment['due_date']
                        )
                        if not any(a['title'] == assignment['title'] for a in existing):
                            if assignment_dao.insert_assignment(assignment):
                                saved_count += 1

            # 完成处理（100%）
            task_status[task_id].update({
                "status": "completed",
                "percent": 100,
                "message": f"Updating completed, {saved_count}new events",
                "result": {
                    "saved_count": saved_count,
                    "total_events": len(all_events),
                    "user_id": user_id
                },
                "completed": True
            })

        except Exception as e:
            # 异常处理
            error_msg = str(e)
            task_status[task_id].update({
                "status": "failed",
                "message": f"爬取失败：{error_msg}",
                "error": error_msg,
                "failed": True
            })
        finally:
            # 确保爬虫资源释放
            if main_scraper:
                main_scraper.close()

    # 添加到后台任务队列
    background_tasks.add_task(run_event_crawl)

    # 立即返回任务ID，供前端查询进度
    return {
        "success": True,
        "message": "日历事件爬取任务已启动",
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
    
@router.post("/user/courses_id")
async def get_courses_by_id(request: GetUCoursesRequest):
    course_id = request.course_id
    if not course_id:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": "course_id is required (请提供邮箱)"}
        )
    
    try:
        course_dao = CourseDAO()

        course_name = course_dao.find_name_by_course_id(course_id)

        return {
            "success": True,
            "message": f"成功获取1门课程",
            "data": course_name
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