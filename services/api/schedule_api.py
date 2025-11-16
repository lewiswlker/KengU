# file: api/assignment.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dao import AssignmentDAO
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any

router = APIRouter(tags=["assignment"])


# 数据模型定义
class UserAssignmentRequest(BaseModel):
    user_id: int


class DateRangeRequest(UserAssignmentRequest):
    start_date: str  # 格式: YYYY-MM-DD
    end_date: str    # 格式: YYYY-MM-DD


class AssignmentTypeRequest(UserAssignmentRequest):
    assignment_type: str
    start_date: Optional[str] = None  # 可选，格式同上
    end_date: Optional[str] = None    # 可选，格式同上


class UpcomingAssignmentsRequest(UserAssignmentRequest):
    days: Optional[int] = 7  # 默认为7天内

class MarkCompleteRequest(BaseModel):
    assignment_id: int


# 转换日期字符串为datetime对象
def parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": f"无效的日期格式: {date_str}，请使用YYYY-MM-DD"}
        )


@router.post("/assignments/date-range")
async def get_assignments_by_date_range(request: DateRangeRequest) -> Dict[str, Any]:
    """获取指定日期范围内的作业"""
    try:
        start_date = parse_date(request.start_date)
        end_date = parse_date(request.end_date)
        
        if start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "error": "开始日期不能晚于结束日期"}
            )

        assignment_dao = AssignmentDAO()
        assignments = assignment_dao.get_assignments_by_date_range(
            user_id=request.user_id,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "count": len(assignments),
            "data": assignments,
            "message": f"成功获取{len(assignments)}条作业数据"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": f"获取作业失败: {str(e)}"}
        )


@router.post("/assignments/type")
async def get_assignments_by_type(request: AssignmentTypeRequest) -> Dict[str, Any]:
    """根据类型获取作业（可指定日期范围）"""
    try:
        start_date = parse_date(request.start_date) if request.start_date else None
        end_date = parse_date(request.end_date) if request.end_date else None

        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "error": "开始日期不能晚于结束日期"}
            )

        assignment_dao = AssignmentDAO()
        assignments = assignment_dao.get_assignments_by_type(
            user_id=request.user_id,
            assignment_type=request.assignment_type,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "count": len(assignments),
            "data": assignments,
            "message": f"成功获取{len(assignments)}条[{request.assignment_type}]类型作业"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": f"获取作业失败: {str(e)}"}
        )


@router.post("/assignments/stats")
async def get_assignment_progress_stats(request: UserAssignmentRequest) -> Dict[str, Any]:
    """获取作业进度统计（总数、已完成、待完成）"""
    try:
        assignment_dao = AssignmentDAO()
        stats = assignment_dao.get_assignment_progress_stats(
            user_id=request.user_id
        )

        return {
            "success": True,
            "data": stats,
            "message": "成功获取作业进度统计"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": f"获取统计数据失败: {str(e)}"}
        )


@router.post("/assignments/upcoming")
async def get_upcoming_assignments(request: UpcomingAssignmentsRequest) -> Dict[str, Any]:
    """获取近期待办作业（默认7天内）"""
    try:
        if request.days <= 0:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "error": "天数必须为正数"}
            )

        assignment_dao = AssignmentDAO()
        assignments = assignment_dao.get_upcoming_assignments(
            user_id=request.user_id,
            days=request.days
        )

        return {
            "success": True,
            "count": len(assignments),
            "data": assignments,
            "message": f"成功获取{request.days}天内{len(assignments)}条待办作业"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": f"获取近期待办作业失败: {str(e)}"}
        )
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("assignment")

# api/assignment.py（仅修改接口层）
import contextlib  # 需导入 contextlib

@router.post("/assignments/mark-complete")
async def mark_assignment_complete(request: MarkCompleteRequest):
    try:
        logger.info(f"接收到标记完成请求：assignment_id={request.assignment_id}")
        assignment_dao = AssignmentDAO()

        # 1. 获取上下文管理器（生成器包装对象）
        conn_context = assignment_dao.get_connection()

        # 2. 从上下文管理器中获取原始生成器（gen 属性）
        gen = conn_context.gen

        # 3. 手动驱动生成器获取连接对象（相当于 with 语句的进入逻辑）
        conn = next(gen)  # 此时 conn 应为真正的数据库连接

        try:
            # 验证连接类型
            print(f"当前连接类型：{type(conn)}")  # 应显示数据库连接类型

            # 执行 DAO 操作
            updated, rowcount, last_executed = assignment_dao.mark_complete(conn, request.assignment_id)
            conn.commit()
            logger.info(f"作业标记完成成功：assignment_id={request.assignment_id}, 影响行数={rowcount}")
            return {"success": True, "message": "作业已标记为完成"}

        except Exception as e:
            # 回滚事务
            conn.rollback()
            logger.error(f"执行失败，已回滚：{str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="处理失败")

        finally:
            # 4. 手动关闭生成器（相当于 with 语句的退出逻辑）
            try:
                # 触发生成器的 finally 块（关闭连接）
                next(gen, None)
            except StopIteration:
                pass  # 正常结束，忽略此异常
            except Exception as e:
                print(f"清理资源失败：{str(e)}")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"接口整体错误：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")
    
@router.post("/assignments/mark-pending")
async def mark_assignment_pending(request: MarkCompleteRequest):
    try:
        logger.info(f"接收到标记完成请求：assignment_id={request.assignment_id}")
        assignment_dao = AssignmentDAO()

        # 1. 获取上下文管理器（生成器包装对象）
        conn_context = assignment_dao.get_connection()

        # 2. 从上下文管理器中获取原始生成器（gen 属性）
        gen = conn_context.gen

        # 3. 手动驱动生成器获取连接对象（相当于 with 语句的进入逻辑）
        conn = next(gen)  # 此时 conn 应为真正的数据库连接

        try:
            # 验证连接类型
            print(f"当前连接类型：{type(conn)}")  # 应显示数据库连接类型

            # 执行 DAO 操作
            updated, rowcount, last_executed = assignment_dao.mark_incomplete_by_id(conn, request.assignment_id)
            conn.commit()
            logger.info(f"作业标记完成成功：assignment_id={request.assignment_id}, 影响行数={rowcount}")
            return {"success": True, "message": "作业已标记为完成"}

        except Exception as e:
            # 回滚事务
            conn.rollback()
            logger.error(f"执行失败，已回滚：{str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="处理失败")

        finally:
            # 4. 手动关闭生成器（相当于 with 语句的退出逻辑）
            try:
                # 触发生成器的 finally 块（关闭连接）
                next(gen, None)
            except StopIteration:
                pass  # 正常结束，忽略此异常
            except Exception as e:
                print(f"清理资源失败：{str(e)}")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"接口整体错误：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")