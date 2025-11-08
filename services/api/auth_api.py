from flask import Blueprint, request, jsonify
from auth import verify_hku_credentials  # 从项目根目录的 auth 包导入

# 创建蓝图，用于分组管理接口
auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/hku-auth", methods=["POST"])
def hku_auth():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    result = verify_hku_credentials(
        email=email,
        password=password,
        headless=True,
        verbose=True
    )
    return jsonify(result)

@auth_bp.route("/auth/login", methods=["POST"])
def system_login():
    # 系统登录的业务逻辑（如验证用户密码、生成token等）
    data = request.json
    email = data.get("email")
    password = data.get("password")
    # 此处添加系统登录的验证逻辑
    return jsonify({"success": True, "message": "系统登录成功"})