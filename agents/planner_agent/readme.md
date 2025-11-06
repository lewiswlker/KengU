# 安装依赖（poetry 安装环境，装完自动用虚拟环境）
poetry install

# 启动服务（默认开发环境，含自动重载）
poetry run uvicorn app.main:app --reload
