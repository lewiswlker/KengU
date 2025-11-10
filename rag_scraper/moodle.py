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
from .logger import get_logger

CONNECT_TIME_OUT = 5  # seconds

class HKUMoodleScraper:
    def __init__(self, headless=True, verbose=False):
        """
        Initialize HKU Moodle Scraper

        Args:
            headless (bool): Run browser in headless mode
            verbose (bool): Enable verbose logging
        """
        self.verbose = verbose
        self.headless = headless
        self.logger = get_logger(log_file="rag_scraper.log", verbose=verbose)
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

    def _log(self, message):
        """Print message only if verbose mode is enabled"""
        if self.verbose:
            self.logger.info(message)

    def connect_moodle(self, username, password):
        """Login to HKU Moodle using Selenium and retrieve courses with retry logic"""
        if "@" not in username or "hku" not in username:
            self.logger.error("Error: Please enter a valid HKU email address.")
            return 0

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            login_start_time = time.time()

            try:
                if attempt > 1:
                    self.logger.warning(
                        f"🔄 Retry attempt {attempt}/{max_retries} - Restarting browser..."
                    )
                    # Close and reinitialize browser
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self._initialize_driver()
                    time.sleep(2)

                self.logger.info(
                    f"Start login! (Attempt {attempt}/{max_retries}) This may take a while depends on your network and hardware, please be patient...",
                    force=True,
                )

                # Step 1: Access CAS login page with timeout
                self._log("Accessing CAS login page directly...")
                self.driver.set_page_load_timeout(CONNECT_TIME_OUT)
                try:
                    self.driver.get("https://moodle.hku.hk/login/index.php?authCAS=CAS")
                except TimeoutException:
                    raise TimeoutException("Page load timeout: CAS login page")
                time.sleep(1)

                # Step 2: Enter email on HKU Portal login page with timeout
                self._log("Entering email on HKU Portal page...")
                try:
                    email_input = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.presence_of_element_located((By.ID, "email"))
                    )
                    email_input.clear()
                    email_input.send_keys(username)
                    self._log(f"Entered email: {username}")
                    time.sleep(0.5)

                    login_button = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.element_to_be_clickable((By.ID, "login_btn"))
                    )
                    login_button.click()
                    self._log("Clicked LOG IN button, waiting for password page...")
                    time.sleep(1)
                except TimeoutException as e:
                    raise TimeoutException(f"Timeout during email entry: {e}")

                # Step 3: Enter password with timeout
                self._log("Entering password...")
                try:
                    password_input = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.presence_of_element_located((By.ID, "passwordInput"))
                    )
                    password_input.clear()
                    password_input.send_keys(password)
                    self._log("Password entered")
                    time.sleep(0.5)

                    submit_button = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.element_to_be_clickable((By.ID, "submitButton"))
                    )
                    submit_button.click()
                    self._log("Clicked login button, waiting for login completion...")
                    time.sleep(1)
                except TimeoutException as e:
                    raise TimeoutException(f"Timeout during password entry: {e}")

                # Step 4: Handle Microsoft "Stay signed in" page with timeout
                self._log("Checking for 'Stay signed in' page...")
                try:
                    continue_button = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                        EC.element_to_be_clickable((By.ID, "idSIButton9"))
                    )
                    self._log(
                        "Found 'Stay signed in' page, clicking 'Continue' button..."
                    )
                    continue_button.click()
                    self._log("Clicked 'Continue' button, waiting for next step...")
                    time.sleep(1)
                except TimeoutException:
                    self._log("No 'Stay signed in' page found or click failed")

                # Step 5: Handle "Stay signed in?" dialog with timeout
                self._log("Checking for 'Stay signed in?' dialog...")
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
                            self._log("'Yes' button not found")

                    if yes_button:
                        self._log(
                            "Found 'Stay signed in?' dialog, clicking 'Yes' button..."
                        )
                        yes_button.click()
                        self._log(
                            "Clicked 'Yes' button, waiting for redirect to Moodle..."
                        )
                        time.sleep(1)
                except Exception as e:
                    self._log(f"Failed to handle 'Stay signed in?' dialog: {e}")

                # Step 6: Wait and confirm redirect to Moodle with timeout
                self._log("Waiting for redirect to Moodle...")
                max_wait = 5
                wait_count = 0
                while wait_count < max_wait:
                    current_url = self.driver.current_url
                    self._log(f"Current URL ({wait_count}s): {current_url}")
                    if (
                        "moodle.hku.hk" in current_url
                        and "login" not in current_url.lower()
                    ):
                        self._log("Successfully logged in to Moodle!")
                        break
                    time.sleep(1)
                    wait_count += 1

                if wait_count >= max_wait:
                    raise TimeoutException(
                        "Timeout: Failed to redirect to Moodle after login"
                    )

                # Check if successfully logged in to Moodle
                if "moodle.hku.hk" in self.driver.current_url:
                    self._log("Successfully logged in to Moodle")
                else:
                    raise Exception(
                        f"Login verification failed, current URL: {self.driver.current_url}"
                    )

                # Calculate and return login time
                login_end_time = time.time()
                login_duration = login_end_time - login_start_time
                self.logger.info(
                    f"✅ Login successful in {login_duration:.2f}s", force=True
                )
                return login_duration

            except (TimeoutException, WebDriverException, Exception) as e:
                error_msg = str(e)
                self.logger.warning(
                    f"⚠️ Login attempt {attempt}/{max_retries} failed: {error_msg}"
                )

                if attempt >= max_retries:
                    self.logger.error(
                        f"❌ Login failed after {max_retries} attempts. Please check your network, email, or password and try again."
                    )
                    return 0

                # Wait before retry
                time.sleep(2)

        return 0

    def get_courses(self):
        # Step 6: Access my courses page
        self.logger.info("Checking your courses page...", force=True)
        start_time = time.time()
        self.driver.get("https://moodle.hku.hk/my/courses.php")

        # Wait for courses to be loaded via JavaScript
        self._log("Waiting for course content to load via JavaScript...")
        try:
            # Wait for course links to appear (max 20 seconds)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'a[href*="course/view.php"]')
                )
            )
            self._log("Course content loaded successfully")
            time.sleep(1)  # Extra wait to ensure all courses are loaded

        except TimeoutException:
            self._log(
                "Timeout, courses may not have loaded completely, but continuing extraction..."
            )
            time.sleep(1)

        # Step 7: Extract course information and URLs
        page_source = self.driver.page_source

        courses = self.extract_courses(page_source)

        # Also extract course URLs for downloading
        soup = BeautifulSoup(page_source, "html.parser")
        course_links = soup.select('a[href*="course/view.php"]')
        course_urls = {}

        for link in course_links:
            course_name = link.get_text(separator=" ", strip=True)
            if (
                course_name
                and len(course_name) > 10
                and not course_name.startswith("Course is starred")
            ):
                href = link.get("href")
                if href and course_name not in course_urls:
                    # Make absolute URL
                    if href.startswith("/"):
                        href = f"https://moodle.hku.hk{href}"
                    course_urls[course_name] = href

        self.course_urls = course_urls

        extract_course_end = time.time()
        extract_course_duration = extract_course_end - start_time

        return courses, extract_course_duration

    def download_all_courses(self, base_dir="knowledge_base", course_filter=None):
        """
        Download all files from all courses

        Improvements:
        1. No subdirectories - all files saved directly to course folder
        2. Only download document files (pdf, doc, ppt, txt, md)
        3. Skip data files (.zip, .rar, etc. with 'data' in name)
        4. Check for duplicates before downloading
        5. Special handling for NLP courses (external site)

        Args:
            base_dir (str): Base directory to save course materials
            course_filter (list, optional): List of course names to download. If None, download all courses.
            
        Returns:
            tuple: (downloaded_files_count, downloaded_file_paths)
                - downloaded_files_count: Total number of files downloaded
                - downloaded_file_paths: List of absolute paths of downloaded files
        """
        from urllib.parse import unquote

        self.logger.info(f"\n{'='*50}", force=True)
        self.logger.info("Starting to download course materials...", force=True)
        self.logger.info(f"{'='*50}\n", force=True)

        # Create base directory
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            self._log(f"Created base directory: {base_dir}")

        downloaded_files_count = 0
        downloaded_file_paths = []  # Track all downloaded file paths

        # Filter courses if specified
        if course_filter:
            course_urls_to_download = {
                name: url
                for name, url in self.course_urls.items()
                if name in course_filter
            }
            total_courses = len(course_urls_to_download)
            self.logger.info(
                f"Filtering to {total_courses} courses based on provided list",
                force=True,
            )
        else:
            course_urls_to_download = self.course_urls
            total_courses = len(course_urls_to_download)

        # Valid file extensions for knowledge base
        VALID_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"}

        for idx, (course_name, course_url) in enumerate(
            course_urls_to_download.items(), 1
        ):
            self.logger.info(
                f"\n[{idx}/{total_courses}] Processing course: {course_name}",
                force=True,
            )
            self._log(f"Course URL: {course_url}")

            # Special handling for NLP courses
            if (
                "Natural language processing" in course_name
                or "NLP" in course_name.upper()
            ):
                self.logger.info(
                    "  → Special NLP course - downloading from external site...",
                    force=True,
                )
                nlp_files, nlp_paths = self._download_nlp_course(base_dir, course_name)
                downloaded_files_count += nlp_files
                downloaded_file_paths.extend(nlp_paths)  # Add NLP file paths
                continue

            # Create course directory
            safe_course_name = self._sanitize_filename(course_name)
            course_dir = os.path.join(base_dir, safe_course_name)

            if not os.path.exists(course_dir):
                os.makedirs(course_dir)
                self._log(f"Created course directory: {course_dir}")

            # Track files already in directory to avoid duplicates
            existing_files = set(f.lower() for f in os.listdir(course_dir))
            downloaded_in_this_run = set()

            try:
                # Navigate to course page
                self.driver.get(course_url)
                time.sleep(0.5)

                # Get all downloadable resources
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")

                # Strategy: Find resource/folder links, fetch their HTML with requests,
                # then extract pluginfile.php links (avoids triggering browser downloads)

                import requests

                # Get cookies from Selenium for authenticated requests
                selenium_cookies = self.driver.get_cookies()
                session = requests.Session()
                for cookie in selenium_cookies:
                    session.cookies.set(cookie["name"], cookie["value"])

                download_links = []

                # Find all resource and folder links
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    # Make absolute URL first
                    if href.startswith("/"):
                        href = f"https://moodle.hku.hk{href}"

                    # Case 1: Direct pluginfile.php links - download directly
                    if "/pluginfile.php" in href:

                        filename = href.split("/")[-1].split("?")[0]
                        filename = unquote(filename)

                        if not filename or len(filename) < 3:
                            continue

                        # Skip images and archives
                        if any(
                            ext in filename.lower()
                            for ext in [
                                ".png",
                                ".jpg",
                                ".jpeg",
                                ".gif",
                                ".ico",
                                ".svg",
                                ".zip",
                                ".rar",
                                ".7z",
                                ".gz",
                                ".tar",
                            ]
                        ):
                            continue

                        # Only include document files
                        file_ext = os.path.splitext(filename)[1].lower()
                        if file_ext in [
                            ".pdf",
                            ".doc",
                            ".docx",
                            ".ppt",
                            ".pptx",
                            ".txt",
                            ".md",
                        ]:
                            self._log(f"    Found direct file: {filename}")
                            download_links.append({"filename": filename, "url": href})
                        continue

                    # Case 2: Resource/folder pages - fetch HTML to extract links
                    if (
                        "/mod/resource/view.php" in href
                        or "/mod/folder/view.php" in href
                    ):
                        # Skip archive files
                        if any(
                            ext in href.lower()
                            for ext in [".zip", ".rar", ".7z", ".gz", ".tar"]
                        ):
                            self._log(f"    Skipping archive: {text}")
                            continue

                        try:
                            # Fetch resource page to check what it returns
                            self._log(f"    Checking: {text[:60]}")
                            response = session.get(
                                href, timeout=10, allow_redirects=True
                            )

                            # Check content type
                            content_type = response.headers.get("Content-Type", "")

                            # If it's a direct file (not HTML), treat the URL as download link
                            if "html" not in content_type:
                                # Extract filename from URL or Content-Disposition
                                filename = None
                                content_disp = response.headers.get(
                                    "Content-Disposition", ""
                                )
                                if "filename=" in content_disp:
                                    filename = content_disp.split("filename=")[
                                        -1
                                    ].strip("\"'")

                                if not filename:
                                    # Try to extract from URL
                                    filename = response.url.split("/")[-1].split("?")[0]

                                    filename = unquote(filename)

                                # Check if valid document
                                if filename and len(filename) > 3:
                                    file_ext = os.path.splitext(filename)[1].lower()
                                    if file_ext in [
                                        ".pdf",
                                        ".doc",
                                        ".docx",
                                        ".ppt",
                                        ".pptx",
                                        ".txt",
                                        ".md",
                                    ]:
                                        self._log(
                                            f"      Found direct file: {filename}"
                                        )
                                        download_links.append(
                                            {"filename": filename, "url": response.url}
                                        )
                                continue

                            # Parse HTML with explicit encoding to avoid charset detection hang
                            resource_soup = BeautifulSoup(
                                response.content, "html.parser", from_encoding="utf-8"
                            )

                            # Extract pluginfile.php links
                            for file_link in resource_soup.find_all("a", href=True):
                                file_href = file_link.get("href", "")

                                if "/pluginfile.php" in file_href:
                                    if file_href.startswith("/"):
                                        file_href = f"https://moodle.hku.hk{file_href}"

                                    filename = file_href.split("/")[-1].split("?")[0]
                                    filename = unquote(filename)

                                    if not filename or len(filename) < 3:
                                        continue
                                    if any(
                                        ext in filename.lower()
                                        for ext in [
                                            ".png",
                                            ".jpg",
                                            ".jpeg",
                                            ".gif",
                                            ".ico",
                                            ".svg",
                                        ]
                                    ):
                                        continue

                                    file_ext = os.path.splitext(filename)[1].lower()

                                    if file_ext in [
                                        ".zip",
                                        ".rar",
                                        ".7z",
                                        ".gz",
                                        ".tar",
                                    ]:
                                        continue

                                    if file_ext in VALID_EXTENSIONS:
                                        if not any(
                                            d["filename"] == filename
                                            for d in download_links
                                        ):
                                            download_links.append(
                                                {"filename": filename, "url": file_href}
                                            )
                                            self._log(f"      Found: {filename}")

                            # Check for embedded objects/iframes
                            for obj in resource_soup.find_all(
                                ["object", "embed", "iframe"]
                            ):
                                url = obj.get("data") or obj.get("src")
                                if url and "/pluginfile.php" in url:
                                    if url.startswith("/"):
                                        url = f"https://moodle.hku.hk{url}"

                                    filename = url.split("/")[-1].split("?")[0]
                                    filename = unquote(filename)
                                    file_ext = os.path.splitext(filename)[1].lower()

                                    if file_ext in VALID_EXTENSIONS:
                                        if not any(
                                            d["filename"] == filename
                                            for d in download_links
                                        ):
                                            download_links.append(
                                                {"filename": filename, "url": url}
                                            )
                                            self._log(
                                                f"      Found (embedded): {filename}"
                                            )

                        except Exception as e:
                            self._log(f"      Error: {e}")
                            continue

                self._log(f"Found {len(download_links)} downloadable files")

                # Download each file
                for idx, item in enumerate(download_links, 1):
                    try:
                        filename = item["filename"]
                        file_url = item["url"]

                        # Check for duplicates
                        if (
                            filename.lower() in existing_files
                            or filename.lower() in downloaded_in_this_run
                        ):
                            self._log(
                                f"  [{idx}/{len(download_links)}] {filename} - Already exists"
                            )
                            continue

                        self._log(
                            f"  [{idx}/{len(download_links)}] Downloading: {filename}"
                        )

                        # Download file
                        file_path = os.path.join(course_dir, filename)

                        if self._download_file_safe(file_url, file_path):
                            downloaded_in_this_run.add(filename.lower())
                            downloaded_files_count += 1
                            downloaded_file_paths.append(os.path.abspath(file_path))  # Record absolute path
                            self._log(f"      ✓ Downloaded")
                        else:
                            self._log(f"      ✗ Failed")

                    except Exception as e:
                        self._log(f"      Error: {e}")
                        continue

                self.logger.info(
                    f"  ✓ Completed: {course_name} ({len(downloaded_in_this_run)} new files)",
                    force=True,
                )

            except Exception as e:
                self.logger.error(f"  ✗ Error processing course {course_name}: {e}")
                self._log(f"Error details: {e}")
                continue

        self.logger.info(f"\n{'='*50}", force=True)
        self.logger.info("Download completed!", force=True)
        self.logger.info(
            f"Total files downloaded: {downloaded_files_count}", force=True
        )
        self.logger.info(f"Saved to: {os.path.abspath(base_dir)}", force=True)
        self.logger.info(f"{'='*50}\n", force=True)

        return downloaded_files_count, downloaded_file_paths

    def _download_file_safe(self, url, filepath):
        """
        Download file with error handling and return success status

        Args:
            url (str): File URL
            filepath (str): Local file path to save

        Returns:
            bool: True if download succeeded, False otherwise
        """
        import requests

        try:
            # Get cookies from Selenium
            selenium_cookies = self.driver.get_cookies()

            # Create session with cookies
            session = requests.Session()
            for cookie in selenium_cookies:
                session.cookies.set(cookie["name"], cookie["value"])

            # Download
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Save
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return True

        except Exception as e:
            self._log(f"        Download failed: {e}")
            return False

    def _download_nlp_course(self, base_dir, course_name):
        """
        Download NLP course from external website

        Args:
            base_dir (str): Base directory
            course_name (str): Course name

        Returns:
            tuple: (downloaded_count, downloaded_paths)
                - downloaded_count: Number of files downloaded
                - downloaded_paths: List of absolute paths of downloaded files
        """
        import requests

        nlp_url = "https://nlp.cs.hku.hk/comp7607-fall2025/"

        self.logger.info(f"  Downloading from external site: {nlp_url}", force=True)

        # Create course directory
        safe_course_name = self._sanitize_filename(course_name)
        course_dir = os.path.join(base_dir, safe_course_name)
        if not os.path.exists(course_dir):
            os.makedirs(course_dir)

        existing_files = set(f.lower() for f in os.listdir(course_dir))
        downloaded_count = 0
        downloaded_paths = []  # Track downloaded file paths

        try:
            # Get page content (no authentication needed)
            response = requests.get(nlp_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Find all document links
            all_links = soup.find_all("a", href=True)

            for link in all_links:
                href = link.get("href")

                # Check if it's a document
                if any(
                    ext in href.lower()
                    for ext in [".pdf", ".pptx", ".ppt", ".doc", ".docx"]
                ):
                    # Make absolute URL
                    if href.startswith("/"):
                        file_url = f"https://nlp.cs.hku.hk{href}"
                    elif href.startswith("http"):
                        file_url = href
                    else:
                        file_url = f"https://nlp.cs.hku.hk/comp7607-fall2025/{href}"

                    # Extract filename
                    filename = href.split("/")[-1]

                    # Check duplicate
                    if filename.lower() in existing_files:
                        self._log(f"    Already exists: {filename}")
                        continue

                    # Download
                    filepath = os.path.join(course_dir, filename)
                    try:
                        file_response = requests.get(file_url, timeout=30)
                        file_response.raise_for_status()

                        with open(filepath, "wb") as f:
                            f.write(file_response.content)

                        self._log(f"    ✓ {filename}")
                        downloaded_count += 1
                        downloaded_paths.append(os.path.abspath(filepath))  # Record absolute path

                    except Exception as e:
                        self._log(f"    Failed: {filename} - {e}")
                        continue

            self.logger.info(
                f"  ✓ NLP course completed: {downloaded_count} files", force=True
            )
            return downloaded_count, downloaded_paths

        except Exception as e:
            self.logger.error(f"  ✗ Error downloading NLP course: {e}")
            return 0, []

    def _sanitize_filename(self, filename):
        """
        Sanitize filename for filesystem compatibility

        Args:
            filename (str): Original filename

        Returns:
            str: Sanitized filename
        """
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # Limit length
        if len(filename) > 200:
            filename = filename[:200]

        return filename.strip()

    def close(self):
        self._log("Closing browser...")
        self.driver.quit()
        self._log("Browser closed")

    def extract_courses(self, html_content):
        """Extract course information from HTML content"""
        soup = BeautifulSoup(html_content, "html.parser")

        courses = []

        # Method 1: Extract from "My courses" page - Find course cards and links
        self._log("Method 1: Finding course cards and links...")

        # First try to find all links containing course information
        course_links = soup.select('a[href*="course/view.php"]')
        if course_links:
            self._log(f"Found {len(course_links)} course links")
            for link in course_links:
                # Get complete text of link, including all sub-elements
                course_name = link.get_text(separator=" ", strip=True)

                # Filter out too short or meaningless text
                if course_name and len(course_name) > 10:
                    # Exclude some common navigation links and duplicate "Course is starred" text
                    excluded_texts = [
                        "Click to enter this course",
                        "Course",
                        "View",
                        "Go to course",
                        "Enter course",
                    ]

                    # Check if starts with excluded keywords
                    is_valid = True
                    if course_name.startswith("Course is starred"):
                        is_valid = False
                    else:
                        for excluded in excluded_texts:
                            if course_name == excluded:
                                is_valid = False
                                break

                    # Add course (deduplicate)
                    if is_valid and course_name not in courses:
                        courses.append(course_name)

        # Method 2: Find course cards (as supplement)
        if not courses:
            self._log("Method 2: Finding course cards...")
            course_cards = soup.select("div.card-deck div.card, div.coursebox")
            if course_cards:
                self._log(f"Found {len(course_cards)} course cards")
                for card in course_cards:
                    # Find course name element
                    course_name_elem = (
                        card.select_one("h3.card-title a")
                        or card.select_one(".coursename a")
                        or card.select_one("a[href*='course/view.php']")
                        or card.select_one("h3")
                    )

                    if course_name_elem:
                        course_name = course_name_elem.get_text(
                            separator=" ", strip=True
                        )
                        if course_name and course_name not in courses:
                            courses.append(course_name)

        # Method 3: Find course list containers
        if not courses:
            self._log("Method 3: Finding course list containers...")
            course_containers = soup.select(
                ".course-listitem, div[data-region='course-item'], .course-info-container, .coursebox"
            )
            if course_containers:
                self._log(f"Found {len(course_containers)} course containers")
                for container in course_containers:
                    course_link = container.select_one('a[href*="course/view.php"]')
                    if course_link:
                        course_name = course_link.get_text(separator=" ", strip=True)
                        if course_name and course_name not in courses:
                            courses.append(course_name)

        # Method 4: Find from Dashboard or other areas
        if not courses:
            self._log("Method 4: Finding from main page area...")
            main_region = soup.select_one("#region-main, .content, main")
            if main_region:
                all_links = main_region.select('a[href*="course/view.php"]')
                for link in all_links:
                    course_name = link.get_text(separator=" ", strip=True)
                    if (
                        course_name
                        and len(course_name) > 10
                        and course_name not in courses
                    ):
                        courses.append(course_name)

        if not courses:
            self._log("No course information found")
            # Output some debug information
            self._log("\n=== Debug Information ===")
            self._log(f"Page title: {soup.title.string if soup.title else 'None'}")
            all_links = soup.find_all("a", href=True, limit=20)
            self._log(f"First 20 links found:")
            for i, link in enumerate(all_links, 1):
                self._log(f"{i}. {link.text.strip()[:50]} -> {link['href'][:100]}")
        else:
            self._log(f"\nSuccessfully found {len(courses)} courses:")
            for i, course in enumerate(courses, 1):
                self._log(f"{i}. {course}")
            self.courses = courses

        return courses

    def save_courses(self, filename="courses.json"):
        """Save courses to file"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({"courses": self.courses}, f, ensure_ascii=False, indent=4)
            self.logger.info(f"Course information saved to {filename}", force=True)
            return True
        except (IOError, OSError) as e:
            self.logger.error(f"Error saving course information: {e}")
            return False


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="HKU Moodle Course Scraper")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        default="u3665467@connect.hku.hk",
        help="HKU email address",
    )
    parser.add_argument(
        "-p", "--password", type=str, default="your hku password", help="Password"
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

    args = parser.parse_args()

    # Initialize logger for main function
    logger = get_logger(log_file="rag_scraper.log", verbose=args.verbose)

    # Get credentials
    if args.username and args.password:
        username = args.username
        password = args.password
    else:
        username = input("Please enter your HKU email: ").strip()
        password = input("Please enter your password: ").strip()

    logger.info(f"Logging in with account: {username}", force=True)

    # Create scraper instance with verbose mode
    scraper = HKUMoodleScraper(headless=args.headless, verbose=args.verbose)

    # Login and get courses
    login_duration = scraper.connect_moodle(username, password)
    courses, extract_course_duration = scraper.get_courses()

    # Save course information
    if courses:
        scraper.save_courses()
        logger.info("\n========== Summary ==========", force=True)
        logger.info(f"Successfully scraped {len(courses)} courses:", force=True)
        for i, course in enumerate(courses, 1):
            logger.info(f"{i}. {course}", force=True)
        logger.info("============================\n", force=True)
    else:
        logger.error("Failed to scrape any course information")
        scraper.close()
        return

    logger.info(f"Login Cost: {login_duration:.2f} seconds", force=True)
    logger.info(
        f"Courses Getting Cost: {extract_course_duration:.2f} seconds", force=True
    )

    # Download course materials if requested
    if args.download:
        logger.info("\n" + "=" * 50, force=True)
        logger.info("Starting download of course materials...", force=True)
        logger.info("=" * 50 + "\n", force=True)

        downloaded_count = scraper.download_all_courses()

        logger.info(f"\nTotal files downloaded: {downloaded_count}", force=True)

    scraper.close()


if __name__ == "__main__":
    main()
