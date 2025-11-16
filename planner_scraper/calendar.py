from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime, timedelta
import re

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings

from dao import CourseDAO

# Set DB password
settings.DB_PASS = "123456"

CONNECT_TIME_OUT = 15  # seconds

class MoodleCalendarCrawler:
    def __init__(self, headless=True, verbose=False):
        """
        Initialize HKU Moodle Scraper

        Args:
            headless (bool): Run browser in headless mode
            verbose (bool): Enable verbose logging
        """
        self.verbose = verbose
        self.headless = headless
        self.course_urls = {}  # Initialize course URLs dictionary
        self.courses = []
        self.CONNECT_TIME_OUT = CONNECT_TIME_OUT  # Instance variable for timeout

        # Initialize browser
        self._initialize_driver()

    def _initialize_driver(self):
        """Initialize or reinitialize the Chrome WebDriver"""
        # Setup Chrome options
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--disable-css")
        chrome_options.add_experimental_option(
            "prefs", {"profile.default_content_setting_values.stylesheets": 2}
        )
        chrome_options.add_argument("--fast")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-plugin-types=all")
        chrome_options.add_argument("--disable-http2")
        chrome_options.add_argument("--disable-prefetching")
        chrome_options.add_argument("--disable-preconnect")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--disable-dom-distiller")

        # Initialize WebDriver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def connect_moodle(self, username, password):
        """Login to HKU Moodle using Selenium and retrieve courses with retry logic"""
        if "@" not in username or "hku" not in username:
            print("Error: Please enter a valid HKU email address.")
            return 0

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            login_start_time = time.time()

            try:
                if attempt > 1:
                    print(
                        f"🔄 Retry attempt {attempt}/{max_retries} - Restarting browser..."
                    )
                    # Close and reinitialize browser
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self._initialize_driver()
                    time.sleep(2)

                print(
                    f"Start login! (Attempt {attempt}/{max_retries}) This may take a while depends on your network and hardware, please be patient...")

                # Step 1: Access CAS login page with timeout
                print("Accessing CAS login page directly...")
                self.driver.set_page_load_timeout(CONNECT_TIME_OUT)
                try:
                    self.driver.get("https://moodle.hku.hk/login/index.php?authCAS=CAS")
                except TimeoutException:
                    raise TimeoutException("Page load timeout: CAS login page")
                time.sleep(1)

                # Step 2: Enter email on HKU Portal login page with timeout
                print("Entering email on HKU Portal page...")
                try:
                    email_input = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.presence_of_element_located((By.ID, "email"))
                    )
                    email_input.clear()
                    email_input.send_keys(username)
                    print(f"Entered email: {username}")
                    time.sleep(0.5)

                    login_button = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.element_to_be_clickable((By.ID, "login_btn"))
                    )
                    login_button.click()
                    print("Clicked LOG IN button, waiting for password page...")
                    time.sleep(1)
                except TimeoutException as e:
                    raise TimeoutException(f"Timeout during email entry: {e}")

                # Step 3: Enter password with timeout
                print("Entering password...")
                try:
                    password_input = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.presence_of_element_located((By.ID, "passwordInput"))
                    )
                    password_input.clear()
                    password_input.send_keys(password)
                    print("Password entered")
                    time.sleep(0.5)

                    submit_button = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.element_to_be_clickable((By.ID, "submitButton"))
                    )
                    submit_button.click()
                    print("Clicked login button, waiting for login completion...")
                    time.sleep(1)
                except TimeoutException as e:
                    raise TimeoutException(f"Timeout during password entry: {e}")

                # Step 4: Handle Microsoft "Stay signed in" page with timeout
                print("Checking for 'Stay signed in' page...")
                try:
                    continue_button = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.element_to_be_clickable((By.ID, "idSIButton9"))
                    )
                    print(
                        "Found 'Stay signed in' page, clicking 'Continue' button..."
                    )
                    continue_button.click()
                    print("Clicked 'Continue' button, waiting for next step...")
                    time.sleep(1)
                except TimeoutException:
                    print("No 'Stay signed in' page found or click failed")

                # Step 5: Handle "Stay signed in?" dialog with timeout
                print("Checking for 'Stay signed in?' dialog...")
                try:
                    yes_button = None
                    try:
                        yes_button = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                            EC.element_to_be_clickable((By.ID, "idSIButton9"))
                        )
                    except TimeoutException:
                        try:
                            yes_button = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, "//input[@value='是' or @value='Yes']")
                                )
                            )
                        except TimeoutException:
                            print("'Yes' button not found")

                    if yes_button:
                        print(
                            "Found 'Stay signed in?' dialog, clicking 'Yes' button..."
                        )
                        yes_button.click()
                        print(
                            "Clicked 'Yes' button, waiting for redirect to Moodle..."
                        )
                        time.sleep(1)
                except Exception as e:
                    print(f"Failed to handle 'Stay signed in?' dialog: {e}")

                # Step 6: Wait and confirm redirect to Moodle with timeout
                print("Waiting for redirect to Moodle...")
                max_wait = 5
                wait_count = 0
                while wait_count < max_wait:
                    current_url = self.driver.current_url
                    print(f"Current URL ({wait_count}s): {current_url}")
                    if (
                        "moodle.hku.hk" in current_url
                        and "login" not in current_url.lower()
                    ):
                        print("Successfully logged in to Moodle!")
                        break
                    time.sleep(1)
                    wait_count += 1

                if wait_count >= max_wait:
                    raise TimeoutException(
                        "Timeout: Failed to redirect to Moodle after login"
                    )

                # Check if successfully logged in to Moodle
                if "moodle.hku.hk" in self.driver.current_url:
                    print("Successfully logged in to Moodle")
                else:
                    raise Exception(
                        f"Login verification failed, current URL: {self.driver.current_url}"
                    )

                # Calculate and return login time
                login_end_time = time.time()
                login_duration = login_end_time - login_start_time
                print(
                    f"✅ Login successful in {login_duration:.2f}s")
                return login_duration

            except (TimeoutException, WebDriverException, Exception) as e:
                error_msg = str(e)
                print(
                    f"⚠️ Login attempt {attempt}/{max_retries} failed: {error_msg}"
                )

                if attempt >= max_retries:
                    print(
                        f"❌ Login failed after {max_retries} attempts. Please check your network, email, or password and try again."
                    )
                    return 0

                # Wait before retry
                time.sleep(2)

        return 0

    def _get_unix_timestamp(self, date_str):
        """将日期字符串（YYYY-MM-DD）转��为Unix时间戳（UTC）"""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return int(dt.timestamp())
        except ValueError:
            print(f"日期格式错误: {date_str}（应为YYYY-MM-DD）")
            return None

    def get_calendar_events(self, start_date, end_date, course_id=None):
        """
        获取指定日期范围内的日历事件

        Args:
            start_date (str): 开始日期（YYYY-MM-DD）
            end_date (str): 结束日期（YYYY-MM-DD）
            course_id (str, optional): 课程ID（如127998）， None表示所有课程

        Returns:
            list: 日历事件列表，每个事件包含标题、时间、课程、链接等信息
        """
        # 转换日期为时间戳
        start_ts = self._get_unix_timestamp(start_date)
        end_ts = self._get_unix_timestamp(end_date)
        if not start_ts or not end_ts:
            return []

        # 验证日期范围有效性
        if start_ts > end_ts:
            print("开始日期不能晚于结束日期")
            return []

        print(f"开始获取{start_date}至{end_date}的日历事件...")
        self.calendar_events = []

        # 计算日期范围的天数，逐天获取（Moodle日历按日视图展示更清晰）
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end_dt - current_date).days + 1

        for day in range(total_days):
            target_date = current_date + timedelta(days=day)
            date_str = target_date.strftime("%Y-%m-%d")
            ts = int(target_date.timestamp())
            print(f"\n处理日期: {date_str}（时间戳: {ts}）")

            # 构建日历URL（日视图）
            url_params = f"view=day&time={ts}"
            if course_id:
                url_params += f"&course={course_id}"
            calendar_url = f"https://moodle.hku.hk/calendar/view.php?{url_params}"

            try:
                # 访问日历页面
                self.driver.get(calendar_url)
                time.sleep(1)

                # 等待事件加载完成
                WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".calendarwrapper"))
                )
                time.sleep(0.5)

                # 解析页面内容
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                self._parse_calendar_day(soup, date_str)

            except TimeoutException:
                print(f"获取{date_str}日历超时，跳过该日期")
            except Exception as e:
                print(f"处理{date_str}日历时出错: {str(e)}")

        print(f"✅ 日历事件获取完成，共{len(self.calendar_events)}条记录")
        return self.calendar_events

    def _parse_calendar_day(self, soup, date_str):
        # 定位所有事件容器（带有data-type="event"属性的标签）
        event_containers = soup.select('[data-type="event"]')
        if not event_containers:
            print(f"  {date_str}没有找到日历事件")
            return

        print(f"  找到{len(event_containers)}个事件，开始解析...")

        for idx, container in enumerate(event_containers, 1):
            try:
                # 1. 从data属性直接提取核心信息（最可靠的方式）
                event_title = container.get('data-event-title', '未命名事件')  # 直接获取data-event-title
                course_id = container.get('data-course-id', '未知��程ID')
                event_id = container.get('data-event-id', '未知事件ID')
                event_type = container.get('data-event-eventtype', '未知类型')
                component = container.get('data-event-component', '未知组件')

                # 2. 解析时间（从链接或文本中提取）
                time_link = container.select_one('a[href*="calendar/view.php?view=day"]')
                if time_link:
                    time_text = time_link.get_text(strip=True)  # 例如："Monday, 17 November"
                    time_full = f"{time_text}, {container.select_one('.col-11').get_text(strip=True).split(',')[-1].strip()}"
                else:
                    time_full = date_str

                # 3. 解析课程名称（从链接文本提取）
                course_link = container.select_one('a[href*="course/view.php?id="]')
                course_name = course_link.get_text(strip=True) if course_link else f"课程ID: {course_id}"

                # 4. 解析描述（从.description-content提取）
                desc_elem = container.select_one('.description-content')
                description = desc_elem.get_text(separator='\n', strip=True) if desc_elem else ""

                # 5. 解析提交链接（作业提交入口）
                submit_link = container.select_one('.card-footer .card-link')['href'] if container.select_one('.card-footer .card-link') else ""
                if submit_link and submit_link.startswith('/'):
                    submit_link = f"https://moodle.hku.hk{submit_link}"

                # 构建事件字典
                event = {
                    "date": date_str,
                    "title": event_title,  # 从data-event-title获取的标题
                    "time": time_full,
                    "course": course_name,
                    "course_id": course_id,
                    "event_id": event_id,
                    "event_type": event_type,  # 例如：due（截止）
                    "component": component,    # 例如：mod_assign（作业模块）
                    "description": description,
                    "submit_link": submit_link
                }
                self.calendar_events.append(event)
                print(f"  解析事件{idx}: {event_title}（{event_type}）")

            except Exception as e:
                print(f"  解析事件{idx}失败: {str(e)}")
                continue

    def _parse_calendar_day_single(self, soup, date_str):
        """Parse calendar events for a single day (from threaded processing)"""
        event_containers = soup.select('[data-type="event"]')
        events = []

        if not event_containers:
            print(f"  {date_str}没有找到日历事件")
            return events

        print(f"  找到{len(event_containers)}个事件，开始解析...")

        for idx, container in enumerate(event_containers, 1):
            try:
                # 1. 从data属性直接提取核心信息（最可靠的方式）
                event_title = container.get('data-event-title', '未命名事件')  # 直接获取data-event-title
                course_id = container.get('data-course-id', '未知课程ID')
                event_id = container.get('data-event-id', '未知事件ID')
                event_type = container.get('data-event-eventtype', '未知类型')
                component = container.get('data-event-component', '未知组件')

                # 2. 解析时间（从链接中提取）
                time_link = container.select_one('a[href*="calendar/view.php?view=day"]')
                if time_link:
                    time_text = time_link.get_text(strip=True)  # 例如："Monday, 17 November"
                    time_full = f"{time_text}, {container.select_one('.col-11').get_text(strip=True).split(',')[-1].strip()}"
                else:
                    time_full = date_str

                # 3. 解析课程名称（从链接文本提取）
                course_link = container.select_one('a[href*="course/view.php?id="]')
                course_name = course_link.get_text(strip=True) if course_link else f"课程ID: {course_id}"

                # 4. 解析描述（从.description-content提取）
                desc_elem = container.select_one('.description-content')
                description = desc_elem.get_text(separator='\n', strip=True) if desc_elem else ""

                # 5. 解析提交链接（作业提交入口）
                submit_link = container.select_one('.card-footer .card-link')['href'] if container.select_one('.card-footer .card-link') else ""
                if submit_link and submit_link.startswith('/'):
                    submit_link = f"https://moodle.hku.hk{submit_link}"

                # 构建事件字典
                event = {
                    "date": date_str,
                    "title": event_title,  # 从data-event-title获取的标题
                    "time": time_full,
                    "course": course_name,
                    "course_id": course_id,
                    "event_id": event_id,
                    "event_type": event_type,  # 例如：due（截止）
                    "component": component,    # 例如：mod_assign（作业模块）
                    "description": description,
                    "submit_link": submit_link
                }
                events.append(event)
                print(f"  解析事件{idx}: {event_title}（{event_type}）")

            except Exception as e:
                print(f"  解析事件{idx}失败: {str(e)}")
                continue

        return events

    def close(self):
        """关闭浏览器"""
        if self.driver:
            print("关闭浏览器...")
            self.driver.quit()
            self.driver = None

    def get_assignments_by_course(self, course_ids, start_date, end_date):
        """
        获取指定课程列表的作业ID

        Args:
            course_ids (list): 课程ID列表
            start_date (str): 开始日期（YYYY-MM-DD）
            end_date (str): 结束日期（YYYY-MM-DD）

        Returns:
            dict: {course_id: [assignment_ids]}
        """
        assignments_by_course = {}

        for course_id in course_ids:
            print(f"获取课程 {course_id} 的作业...")
            events = self.get_calendar_events(start_date, end_date, course_id=str(course_id))

            # 过滤作业事件（截止事件且为作业组件）
            assignment_ids = []
            for event in events:
                if (event.get('event_type') == 'due' and
                    event.get('component') in ['mod_assign', 'mod_turnitintooltwo']):  # 常见的作业模块
                    assignment_ids.append(event.get('event_id'))

            assignments_by_course[course_id] = assignment_ids
            print(f"课程 {course_id} 找到 {len(assignment_ids)} 个作业")

        return assignments_by_course

    def get_course_ids_from_db(self, user_id=1):
        """
        Get course IDs from database for a user
        :param user_id: User ID
        :return: List of dicts with 'course_id' and 'course_name'
        """
        course_dao = CourseDAO()
        return course_dao.get_user_courses(user_id)

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="HKU Moodle Assignment Crawler")
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        default="u3665686@connect.hku.hk",
        help="HKU email address",
    )
    parser.add_argument(
        "-p", "--password", type=str, default="yupei626513", help="Password"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (default: True)",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Run with visible browser",
    )
    parser.add_argument("--user-id", type=int, required=True, help="User ID to query courses for")
    parser.add_argument("--start-date", default="2025-11-16", help="开始日期（格式: YYYY-MM-DD）")
    parser.add_argument("--end-date", default="2025-11-22", help="结束日期（格式: YYYY-MM-DD）")

    args = parser.parse_args()

    # Get credentials
    if args.username and args.password:
        username = args.username
        password = args.password
    else:
        username = input("Please enter your HKU email: ").strip()
        password = input("Please enter your password: ").strip()

    print(f"Logging in with account: {username}")

    # Query user's courses from database
    from dao import AssignmentDAO, CourseDAO
    course_dao = CourseDAO()
    try:
        courses = []
        conn = course_dao.db_connector.get_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT c.course_id, c.course_name
                FROM user_courses uc
                JOIN courses c ON uc.course_id = c.id
                WHERE uc.user_id = %s
            """
            cursor.execute(sql, (args.user_id,))
            results = cursor.fetchall()
            courses = [{'course_id': row['course_id'], 'course_name': row['course_name']} for row in results]
    except Exception as e:
        print(f"Error querying courses for user {args.user_id}: {e}")
        return

    if not courses:
        print(f"No courses found for user {args.user_id}")
        return

    print(f"Found {len(courses)} courses for user {args.user_id}: {courses}")
    print("Creating scraper instance...")

    # Create scraper instance
    scraper = MoodleCalendarCrawler(headless=args.headless)

    try:
        # Login
        if not scraper.connect_moodle(username, password):
            print("Failed to login to Moodle")
            return

        # Initialize DAO
        assignment_dao = AssignmentDAO()

        # Crawl assignments for each course
        total_saved = 0
        for course_info in courses:
            course_id = course_info['course_id']
            course_name = course_info['course_name']
            print(f"\nProcessing course {course_id} ({course_name})...")

            events = scraper.get_calendar_events(
                start_date=args.start_date,
                end_date=args.end_date,
                course_id=str(course_id)
            )

            # Process assignments
            saved_count = 0
            for event in events:
                if event.get('event_type') == 'due' and event.get('component') in ['mod_assign', 'mod_turnitintooltwo']:
                    # Convert to assignment
                    from datetime import datetime
                    due_date = datetime.strptime(event["date"], "%Y-%m-%d") if event.get("date") else None

                    assignment_type = "homework"
                    if "exam" in event.get("title", "").lower():
                        assignment_type = "exam"
                    elif "quiz" in event.get("title", "").lower():
                        assignment_type = "quiz"
                    elif "project" in event.get("title", "").lower():
                        assignment_type = "project"

                    assignment = {
                        "title": event.get("title", ""),
                        "description": event.get("description", ""),
                        "course_id": int(event.get("course_id", 0)),
                        "user_id": args.user_id,
                        "due_date": due_date,
                        "status": "pending",
                        "assignment_type": assignment_type,
                        "instructions": event.get("description", ""),
                        "attachment_path": event.get("submit_link", "")
                    }

                    # Check if exists
                    existing = assignment_dao.get_assignments_by_date_range(args.user_id, assignment['due_date'], assignment['due_date'])
                    exists = any(a['title'] == assignment['title'] for a in existing)

                    if not exists:
                        success = assignment_dao.insert_assignment(assignment)
                        if success:
                            print(f"  Inserted assignment: ID {event.get('event_id')} - '{assignment['title']}'")
                            saved_count += 1
                        else:
                            print(f"  Failed to insert: {assignment['title']}")
                    else:
                        print(f"  Assignment already exists: {assignment['title']}")

            print(f"Course {course_id} ({course_name}): {saved_count} assignments inserted")
            total_saved += saved_count

        print(f"\nTotal assignments inserted: {total_saved}")

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
