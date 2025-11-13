from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel  # 移除 EmailStr 导入
from auth import verify_hku_credentials
from dao import UserDAO
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

class HKUAuthRequest(BaseModel):
    """HKU认证请求模型"""
    email: str  # 改回 str 类型
    password: str

class CheckAndCreateUserRequest(BaseModel):
    """检查并创建用户的请求模型"""
    email: str  # 改回 str 类型

@router.post("/hku-auth", status_code=status.HTTP_200_OK)
async def hku_auth(request: HKUAuthRequest):
    """
    验证HKU邮箱和密码
    - 调用HKU认证服务验证凭据
    - 返回验证结果（成功/失败原因）
    """
    try:
        logger.info(f"Authenticating user: {request.email}")
        result = verify_hku_credentials(
            email=request.email,
            password=request.password,
            headless=True,
            verbose=True
        )
        
        # 补充日志记录
        if result.get("success"):
            logger.info(f"User {request.email} authenticated successfully")
        else:
            logger.warning(f"Authentication failed for {request.email}: {result.get('message')}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error during HKU authentication: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": "Authentication service unavailable"}
        )

@router.post("/user/check-and-create", status_code=status.HTTP_201_CREATED)
async def check_and_create_user(request: CheckAndCreateUserRequest):
    """
    检查用户是否存在，不存在则创建
    - 仅允许HKU邮箱（connect.hku.hk/hku.hk）
    - 返回用户ID和邮箱信息
    """
    email = request.email
    logger.info(f"Checking/creating user: {email}")

    # 验证HKU邮箱域名（保留核心校验逻辑）
    if not (email.endswith("@connect.hku.hk") or email.endswith("@hku.hk")):
        logger.warning(f"Invalid HKU email attempt: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "Please use a valid HKU email (xxx@connect.hku.hk or xxx@hku.hk)"}
        )

    user_dao = UserDAO()
    try:
        # 检查用户是否已存在
        user = user_dao.find_by_email(email)
        
        if not user:
            # 创建新用户（密码字段留空，因密码验证由HKU服务处理）
            new_user_id = user_dao.insert_user(user_email=email, pwd="")
            user = user_dao.find_by_id(new_user_id)
            logger.info(f"Created new user: {email} (ID: {new_user_id})")
        else:
            logger.info(f"User already exists: {email} (ID: {user['id']})")

        # 返回用户信息（确保包含id字段，供前端存储）
        return {
            "success": True,
            "message": "User retrieved or created successfully",
            "data": {
                "id": user["id"],
                "email": user["user_email"]
            }
        }

    except RuntimeError as e:
        logger.error(f"Database error while processing user {email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": "Failed to process user data"}
        )
    except Exception as e:
        logger.error(f"Unexpected error with user {email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": "Server error. Please try again later"}
        )