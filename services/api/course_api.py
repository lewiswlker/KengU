from flask import Blueprint, jsonify
from dao import CourseDAO, UserCourseDAO

# 创建课程相关蓝图
course_bp = Blueprint("course", __name__, url_prefix="/courses")

@course_bp.route("/user/courses", methods=["GET"])
def get_user_courses():
    # 测试用的硬编码用户ID（后续应从认证信息中获取）
    user_id = 1
    
    if not user_id:
        return jsonify({
            "success": False,
            "message": "user_id is required (请提供用户ID)"
        }), 400

    try:
        user_course_dao = UserCourseDAO()
        course_dao = CourseDAO()

        # 1. 获取用户-课程关联记录（返回字典列表：包含id、user_id、course_id）
        user_course_records = user_course_dao.find_user_courses_by_userid(user_id)
        
        # 2. 从记录中提取课程ID列表
        course_ids = [record["course_id"] for record in user_course_records]
        
        if not course_ids:
            return jsonify({
                "success": True,
                "message": "该用户暂无课程",
                "data": []
            }), 200  # 空结果用200成功状态码

        # 3. 遍历课程ID，获取课程名称（因find_name_by_id仅返回名称字符串）
        courses = []
        for course_id in course_ids:
            # 调用CourseDAO的find_name_by_id，返回课程名称字符串（如"COMP7103"）
            course_name = course_dao.find_name_by_id(course_id)
            if course_name:
                # 补充获取课程的时间戳（如需）
                moodle_time, exambase_time = course_dao.find_update_time_byid(course_id)
                courses.append({
                    "id": course_id,  # 课程ID（从循环变量中直接获取）
                    "name": course_name,  # 课程名称（从find_name_by_id获取）
                    "update_time_moodle": moodle_time,  # 从find_update_time_byid获取
                    "update_time_exambase": exambase_time  # 从find_update_time_byid获取
                })

        # 4. 返回结果
        return jsonify({
            "success": True,
            "message": f"成功获取{len(courses)}门课程",
            "data": courses
        }), 200

    except RuntimeError as e:
        return jsonify({
            "success": False,
            "message": f"获取课程失败：{str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"服务器错误：{str(e)}"
        }), 500