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

CONNECT_TIME_OUT = 5  # seconds

class MoodleCalendar:
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
        """将日期字符串（YYYY-MM-DD）转换为Unix时间戳（UTC）"""
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
                course_id = container.get('data-course-id', '未知课程ID')
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
    def save_calendar_events(self, filename="calendar_events.json"):
        """将日历事件保存为JSON文件"""
        if not self.calendar_events:
            print("没有可保存的日历事件")
            return False

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({
                    "scraped_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "events": self.calendar_events
                }, f, ensure_ascii=False, indent=4)
            print(f"日历事件已保存至: {os.path.abspath(filename)}")
            return True
        except IOError as e:
            print(f"保存日历事件失败: {str(e)}")
            return False

    def close(self):
        """关闭浏览器"""
        if self.driver:
            print("关闭浏览器...")
            self.driver.quit()
            self.driver = None

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="HKU Moodle Course Scraper")
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        default="u3665673@connect.hku.hk",
        help="HKU email address",
    )
    parser.add_argument(
        "-p", "--password", type=str, default="htngb20030912", help="Password"
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
    parser.add_argument(
        "-d", "--download", action="store_true", help="Download all course materials"
    )

    parser.add_argument("--start-date", required=True, help="开始日期（格式: YYYY-MM-DD）")
    parser.add_argument("--end-date", required=True, help="结束日期（格式: YYYY-MM-DD）")
    parser.add_argument("--course-id", help="课程ID（可选，如127998）")
    parser.add_argument("-o", "--output", default="calendar_events.json", help="输出JSON文件名")

    args = parser.parse_args()

    # Initialize logger for main function

    # Get credentials
    if args.username and args.password:
        username = args.username
        password = args.password
    else:
        username = input("Please enter your HKU email: ").strip()
        password = input("Please enter your password: ").strip()

    print(f"Logging in with account: {username}")

    # Create scraper instance with verbose mode
    scraper = MoodleCalendar(headless=args.headless)

    # Login and get courses
    try:
        # 登录并获取日历事件
        if scraper.connect_moodle(args.username, args.password):
            events = scraper.get_calendar_events(
                start_date=args.start_date,
                end_date=args.end_date,
                course_id=args.course_id
            )
            # 保存结果
            if events:
                scraper.save_calendar_events(args.output)
                # 打印摘要
                print(f"\n获取到{len(events)}条日历事件：")
                for i, event in enumerate(events[:5], 1):  # 只显示前5条
                    print(f"{i}. {event['date']} {event['time']} - {event['title']}")
                if len(events) > 5:
                    print(f"... 还有{len(events)-5}条事件未显示")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
