from flask import Blueprint, jsonify, request
from dao import CourseDAO, UserCourseDAO, UserDAO

course_bp = Blueprint("course", __name__)

@course_bp.route("/user/courses", methods=["POST"])
def get_user_courses():
    data = request.json
    email = data.get("email")
    if not email:
        return jsonify({
            "success": False,
            "message": "email is required (请提供邮箱)"
        }), 400
    
    if not (email.endswith("@connect.hku.hk") or email.endswith("@hku.hk")):
        return jsonify({
            "success": False,
            "message": "invalid email (请使用HKU邮箱)"
        }), 400

    try:
        user_dao = UserDAO()
        user = user_dao.find_by_email(email)
        if not user:
            return jsonify({
                "success": False,
                "message": "user not found (该用户不存在)"
            }), 404
        user_id = user["id"]

        user_course_dao = UserCourseDAO()
        course_dao = CourseDAO()

        user_course_records = user_course_dao.find_user_courses_by_userid(user_id)
        
        course_ids = [record["course_id"] for record in user_course_records]
        
        if not course_ids:
            return jsonify({
                "success": True,
                "message": "该用户暂无课程",
                "data": []
            }), 200

        courses = []
        for course_id in course_ids:
            course_name = course_dao.find_name_by_id(course_id)
            if course_name:
                moodle_time, exambase_time = course_dao.find_update_time_byid(course_id)
                courses.append({
                    "id": course_id,
                    "name": course_name,
                    "update_time_moodle": moodle_time,
                    "update_time_exambase": exambase_time
                })

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