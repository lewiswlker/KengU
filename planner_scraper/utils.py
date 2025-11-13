# utils.py - 辅助函数
import re
from datetime import datetime


def parse_course_code(course_name: str) -> str:
    """
    从课程全名中解析课程代码
    """
    # 匹配类似 "COMP7104_DASC7104 Advanced database systems" 的格式
    match = re.match(r'^([A-Z]+\d+(?:_[A-Z]+\d+)?)', course_name)
    return match.group(1) if match else "Unknown"


def categorize_assignment(title: str, description: str) -> str:
    """
    根据作业标题和描述分类作业类型
    """
    title_lower = title.lower()
    desc_lower = description.lower()

    if any(word in title_lower for word in ['exam', 'final', 'midterm', 'quiz']):
        return 'exam'
    elif any(word in title_lower for word in ['project', 'final project']):
        return 'project'
    elif any(word in title_lower for word in ['assignment', 'hw', 'homework']):
        return 'homework'
    elif any(word in title_lower for word in ['lab', 'experiment']):
        return 'lab'
    else:
        return 'other'


def estimate_completion_hours(assignment_type: str, description: str) -> int:
    """
    根据作业类型和描述预估完成所需小时数
    """
    base_hours = {
        'exam': 10,
        'project': 20,
        'homework': 5,
        'lab': 3,
        'other': 4
    }
    return base_hours.get(assignment_type, 4)


# 增强的爬虫类方法
def enhanced_save_to_mysql_structure(self, events: List[Dict]):
    """
    增强版的MySQL数据结构化方法
    """
    from utils import parse_course_code, categorize_assignment, estimate_completion_hours

    assignments = []

    for event in events:
        if event['event_type'] == 'due' and event['activity_type'] == 'assign':
            due_date = datetime.fromtimestamp(event['timestart']) if event['timestart'] else None

            # 解析更多信息
            course_code = parse_course_code(event['course_name'])
            assignment_type = categorize_assignment(event['name'], event['description'])
            estimated_hours = estimate_completion_hours(assignment_type, event['description'])

            assignment = {
                'assignment_id': event['event_id'],
                'course_id': event['course_id'],
                'course_code': course_code,
                'course_name': event['course_name'],
                'title': event['name'],
                'type': assignment_type,
                'due_date': due_date,
                'description': event['description'],
                'url': event['url'],
                'status': 'overdue' if event['overdue'] else 'pending',
                'estimated_hours': estimated_hours,
                'weight': None,  # 需要从课程大纲获取
                'priority': 'high' if assignment_type in ['exam', 'project'] else 'medium'
            }
            assignments.append(assignment)

    return assignments