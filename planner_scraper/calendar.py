# python
import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sqlite3


class MoodleCalendarCrawler:
    def __init__(self, session_cookie: str, base_url: str = "https://moodle.hku.hk"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': session_cookie
        })

    def get_month_data(self, timestamp: int) -> Dict[str, Any]:
        url = f"{self.base_url}/calendar/view.php"
        params = {
            'view': 'month',
            'time': timestamp
        }

        try:
            response = self.session.get(url, params=params)

            # Debugging information: request URL / params / status / body
            req_url = getattr(response, "url", None) or \
                      (getattr(getattr(response, "request", None), "url", None)) or url
            print(f"📍 Request URL: {req_url}  📊 Status Code: {getattr(response, 'status_code', 'N/A')}")
            try:
                body = response.json()
                print("📝 Response Body:", json.dumps(body, ensure_ascii=False))
            except Exception:
                text = getattr(response, "text", "<no body>")
                print("📝 Response Text:", text[:2000])

            response.raise_for_status()
            try:
                return response.json()
            except Exception:
                return None
        except requests.RequestException as e:
            print(f"获取月份数据失败: {e}")
            return None

    def extract_events_from_month(self, month_data: Dict) -> List[Dict]:
        events = []
        if not month_data or 'data' not in month_data:
            return events
        weeks = month_data['data'].get('weeks', [])
        for week in weeks:
            days = week.get('days', [])
            for day in days:
                day_events = day.get('events', [])
                for event in day_events:
                    event_info = {
                        'event_id': event.get('id'),
                        'name': event.get('name'),
                        'description': event.get('description', ''),
                        'course_id': event.get('course', {}).get('id'),
                        'course_name': event.get('course', {}).get('fullname'),
                        'event_type': event.get('eventtype'),
                        'timestart': event.get('timestart'),
                        'timeduration': event.get('timeduration', 0),
                        'activity_type': event.get('modulename'),
                        'activity_name': event.get('activityname'),
                        'url': event.get('url', ''),
                        'formatted_time': event.get('formattedtime', ''),
                        'is_action_event': event.get('isactionevent', False),
                        'overdue': event.get('overdue', False)
                    }
                    events.append(event_info)
        return events

    def get_recent_months_data(self, months: int = 3) -> List[Dict]:
        all_events = []
        today = datetime.now()
        for i in range(months):
            target_date = today + timedelta(days=30 * i)
            month_start = datetime(target_date.year, target_date.month, 1)
            timestamp = int(month_start.timestamp())
            print(f"获取 {target_date.year}-{target_date.month} 的数据...")
            month_data = self.get_month_data(timestamp)
            if month_data:
                events = self.extract_events_from_month(month_data)
                all_events.extend(events)
                print(f"  找到 {len(events)} 个事件")
            else:
                print(f"  获取数据失败")
            time.sleep(1)
        return all_events

    def save_to_mysql_structure(self, events: List[Dict]):
        assignments = []
        for event in events:
            if event['event_type'] == 'due' and event['activity_type'] == 'assign':
                due_date = datetime.fromtimestamp(event['timestart']) if event['timestart'] else None
                assignment = {
                    'assignment_id': event['event_id'],
                    'course_id': event['course_id'],
                    'course_name': event['course_name'],
                    'title': event['name'],
                    'type': 'assignment',
                    'due_date': due_date,
                    'description': event['description'],
                    'url': event['url'],
                    'status': 'overdue' if event['overdue'] else 'pending'
                }
                assignments.append(assignment)
        return assignments

    def generate_vector_data(self, events: List[Dict]) -> List[Dict]:
        vector_data = []
        for event in events:
            if event['event_type'] == 'due':
                text_content = f"{event['name']}。{event['description']}"
                vector_item = {
                    "text": text_content,
                    "metadata": {
                        "assignment_id": event['event_id'],
                        "course_id": event['course_id'],
                        "course_name": event['course_name'],
                        "type": "assignment_due",
                        "due_timestamp": event['timestart'],
                        "activity_type": event['activity_type']
                    }
                }
                vector_data.append(vector_item)
        return vector_data


def main():
    MOODLE_SESSION_COOKIE = "你的Moodle_Session_Cookie_这里"
    crawler = MoodleCalendarCrawler(MOODLE_SESSION_COOKIE)
    print("开始爬取Moodle日历数据...")
    all_events = crawler.get_recent_months_data(months=3)
    print(f"\n总共找到 {len(all_events)} 个事件")
    assignments = crawler.save_to_mysql_structure(all_events)
    print(f"其中作业截止事件: {len(assignments)} 个")
    vector_data = crawler.generate_vector_data(all_events)
    print(f"生成的向量数据条目: {len(vector_data)} 个")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f'moodle_events_{timestamp}.json', 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)
    with open(f'assignments_{timestamp}.json', 'w', encoding='utf-8') as f:
        assignments_serializable = []
        for assignment in assignments:
            assignment_copy = assignment.copy()
            if assignment_copy['due_date']:
                assignment_copy['due_date'] = assignment_copy['due_date'].isoformat()
            assignments_serializable.append(assignment_copy)
        json.dump(assignments_serializable, f, ensure_ascii=False, indent=2)
    with open(f'vector_data_{timestamp}.json', 'w', encoding='utf-8') as f:
        json.dump(vector_data, f, ensure_ascii=False, indent=2)
    print(f"\n数据已保存到文件:")
    print(f"- 原始事件: moodle_events_{timestamp}.json")
    print(f"- 作业数据: assignments_{timestamp}.json")
    print(f"- 向量数据: vector_data_{timestamp}.json")
    if assignments:
        print(f"\n最近的作业截止日期:")
        for assignment in sorted(assignments, key=lambda x: x['due_date'] if x['due_date'] else datetime.max)[:5]:
            due_str = assignment['due_date'].strftime("%Y-%m-%d %H:%M") if assignment['due_date'] else "未知"
            print(f"  - {assignment['title']} ({due_str})")


if __name__ == "__main__":
    main()
