from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dao import CourseDAO, UserCourseDAO, UserDAO
from agents import update_knowledge_base

router = APIRouter(tags=["course"])

class UpdateKnowledgeBaseRequest(BaseModel):
    email: str
    password: str
    id: int

class GetUserCoursesRequest(BaseModel):
    email: str

@router.post("/update-data")
async def api_update_knowledge_base(request: UpdateKnowledgeBaseRequest):
    email = request.email
    password = request.password
    id = request.id

    if not email:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Missing required parameter: email"}
        )
    if not password:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Missing required parameter: password"}
        )

    if not id:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Missing required parameter: id"}
        )
    user_id = int(id)

    try:
        update_result = update_knowledge_base(
            user_id=user_id,
            user_email=email,
            user_password=password,
            headless=True,
            verbose=True
        )
        return update_result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": f"Update failed: {str(e)}"}
        )

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