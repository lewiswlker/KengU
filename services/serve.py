# services/serve.py 完整代码（含启动逻辑）
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

knowledge_base_path = Path(__file__).parent.parent / "knowledge_base"

# 映射静态资源
app.mount(
    "/knowledge_base",  # URL 路径
    StaticFiles(directory=knowledge_base_path),  # 实际文件目录
    name="knowledge_base"
)


from .api.auth_api import router as auth_router
from .api.course_api import router as course_router
from .api.chat_api import router as chat_router
from .api.schedule_api import router as schedule_router
app.include_router(auth_router, prefix="/api")
app.include_router(course_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(schedule_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.serve:app",
        host="127.0.0.1",
        port=8009,
        reload=True,
        log_level="info"     
    )