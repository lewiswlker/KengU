from flask import Flask
from flask_cors import CORS
from .api.auth_api import auth_bp
from .api.course_api import course_bp

# 初始化 Flask 应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 注册蓝图（将 auth 接口挂载到 /api 路径下）
app.register_blueprint(auth_bp, url_prefix="/api")
app.register_blueprint(course_bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)