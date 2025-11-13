# services/serve.py 完整代码（含启动逻辑）
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import io

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

from .api.auth_api import router as auth_router
from .api.course_api import router as course_router
from .api.chat_api import router as chat_router
app.include_router(auth_router, prefix="/api")
app.include_router(course_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.serve:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"     
    )