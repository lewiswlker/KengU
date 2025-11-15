from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from auth import verify_hku_credentials
from dao import UserDAO
import logging
import hashlib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

class HKUAuthRequest(BaseModel):
    """HKU认证请求模型"""
    email: str
    password: str

class CheckAndCreateUserRequest(BaseModel):
    """检查并创建用户的请求模型"""
    email: str

def md5_hash(password: str) -> str:
    """生成MD5哈希"""
    return hashlib.md5(password.encode('utf-8')).hexdigest()

@router.post("/hku-auth", status_code=status.HTTP_200_OK)
async def hku_auth(request: HKUAuthRequest):
    """
    验证HKU邮箱和密码
    - 先查数据库，如果用户存在则验证本地密码
    - 如果用户不存在或密码为空，则通过HKU验证并存储MD5密码
    - 返回验证结果（成功/失败原因）及用户信息
    """
    email = request.email
    password = request.password
    
    # 验证HKU邮箱域名
    if not (email.endswith("@connect.hku.hk") or email.endswith("@hku.hk")):
        logger.warning(f"Invalid HKU email attempt: {email}")
        return {
            "success": False,
            "message": "Please use a valid HKU email (xxx@connect.hku.hk or xxx@hku.hk)"
        }
    
    user_dao = UserDAO()
    
    try:
        logger.info(f"Authenticating user: {email}")
        
        # 查询数据库中的用户
        user = user_dao.find_by_email(email)
        
        if user and user.get("pwd"):
            # 用户存在且有密码，验证本地密码
            logger.info(f"User found in database, verifying local password: {email}")
            password_hash = md5_hash(password)
            
            if password_hash == user["pwd"]:
                logger.info(f"User {email} authenticated successfully with local password")
                return {
                    "success": True,
                    "message": "Authentication successful",
                    "data": {
                        "id": user["id"],
                        "email": user["user_email"]
                    }
                }
            else:
                logger.warning(f"Password mismatch for user {email}")
                return {
                    "success": False,
                    "message": "Invalid email or password"
                }
        else:
            # 用户不存在或密码为空，需要通过HKU验证
            logger.info(f"User not found or no password set, verifying with HKU: {email}")
            
            result = verify_hku_credentials(
                email=email,
                password=password,
                headless=True,
                verbose=True
            )
            
            if result.get("success"):
                # HKU验证成功，保存或更新用户密码
                password_hash = md5_hash(password)
                
                if user:
                    # 用户存在但密码为空，更新密码
                    user_dao.update_pwd(user["id"], password_hash)
                    logger.info(f"Updated password for existing user: {email} (ID: {user['id']})")
                    user_id = user["id"]
                else:
                    # 用户不存在，创建新用户
                    user_id = user_dao.insert_user(user_email=email, pwd=password_hash)
                    logger.info(f"Created new user: {email} (ID: {user_id})")
                
                return {
                    "success": True,
                    "message": "Authentication successful",
                    "data": {
                        "id": user_id,
                        "email": email
                    }
                }
            else:
                logger.warning(f"HKU authentication failed for {email}: {result.get('message')}")
                return {
                    "success": False,
                    "message": result.get("message", "Authentication failed")
                }
    
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}", exc_info=True)
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