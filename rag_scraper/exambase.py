#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exambase Scraper for HKU
Downloads exam papers from HKU Exambase system for all courses in knowledge_base
"""

import os
import time
import re
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests

from rag_scraper.moodle import CONNECT_TIME_OUT
from .logger import get_logger

CONNECT_TIME_OUT = 5  # seconds

class ExambaseScraper:
    def __init__(self, username, password, headless=False, verbose=False):
        """
        Initialize the Exambase scraper

        Args:
            username: HKU Portal UID (without @connect.hku.hk)
            password: Password
            headless: Run browser in headless mode
            verbose: Enable verbose logging
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.verbose = verbose
        self.logger = get_logger(log_file="rag_scraper.log", verbose=verbose)
        self.exambase_url = (
            "https://exambase-lib-hku-hk.eproxy.lib.hku.hk/exhibits/show/exam/home"
        )

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

        # Disable download dialog
        prefs = {
            "download.default_directory": os.path.abspath("knowledge_base"),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, CONNECT_TIME_OUT)

    def _log(self, message):
        """Print message if verbose mode is enabled"""
        if self.verbose:
            self.logger.info(message, force=True)

    def login(self):
        """Login to HKU Library authentication system with retry logic"""
        max_retries = 3

        for attempt in range(1, max_retries + 1):
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

                self._log(f"Accessing Exambase... (Attempt {attempt}/{max_retries})")

                # Set page load timeout
                self.driver.set_page_load_timeout(CONNECT_TIME_OUT)
                try:
                    self.driver.get(self.exambase_url)
                except TimeoutException:
                    raise TimeoutException("Page load timeout: Exambase")
                time.sleep(1)

                # Check if redirected to login page with timeout
                current_url = self.driver.current_url
                self._log(f"Current URL: {current_url}")

                if "authenticate" in current_url or "lib.hku.hk" in current_url:
                    self._log("Detected library authentication page")
                    time.sleep(1)

                    # Enter UID with timeout
                    self._log("Entering UID...")
                    uid_input = None
                    try:
                        uid_input = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                            EC.presence_of_element_located((By.NAME, "userid"))
                        )
                    except TimeoutException:
                        try:
                            uid_input = self.driver.find_element(By.ID, "user_id")
                        except:
                            try:
                                uid_input = self.driver.find_element(
                                    By.CSS_SELECTOR, "input[type='text']"
                                )
                            except:
                                raise TimeoutException("Could not find UID input field")

                    if uid_input:
                        uid_input.clear()
                        uid_input.send_keys(self.username)
                        self._log(f"Entered UID: {self.username}")
                    else:
                        raise Exception("UID input field not found")

                    # Enter password with timeout
                    self._log("Entering password...")
                    pin_input = None
                    try:
                        pin_input = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                            EC.presence_of_element_located((By.ID, "password"))
                        )
                    except TimeoutException:
                        try:
                            pin_input = self.driver.find_element(By.NAME, "password")
                        except:
                            try:
                                pin_input = self.driver.find_element(
                                    By.CSS_SELECTOR, "input[type='password']"
                                )
                            except:
                                raise TimeoutException(
                                    "Could not find password input field"
                                )

                    if pin_input:
                        pin_input.clear()
                        pin_input.send_keys(self.password)
                        self._log("Entered password")
                    else:
                        raise Exception("Password input field not found")

                    # Click submit button with timeout
                    self._log("Clicking submit...")
                    submit_btn = None
                    try:
                        submit_btn = WebDriverWait(self.driver, CONNECT_TIME_OUT).until(
                            EC.element_to_be_clickable((By.NAME, "submit"))
                        )
                    except TimeoutException:
                        try:
                            submit_btn = self.driver.find_element(
                                By.CSS_SELECTOR, "input[type='submit']"
                            )
                        except:
                            try:
                                submit_btn = self.driver.find_element(
                                    By.XPATH, "//button[@type='submit']"
                                )
                            except:
                                raise TimeoutException("Could not find submit button")

                    if submit_btn:
                        submit_btn.click()
                        self._log("Clicked submit button")
                    else:
                        raise Exception("Submit button not found")

                    # Wait for redirect to Exambase with timeout
                    time.sleep(1)
                    max_wait = 5
                    wait_count = 0
                    while wait_count < max_wait:
                        current_url = self.driver.current_url
                        if "exambase" in current_url:
                            self._log("✓ Successfully logged in to Exambase")
                            self.logger.info("✅ Exambase login successful", force=True)
                            return True
                        time.sleep(1)
                        wait_count += 1

                    raise TimeoutException(
                        f"Timeout: Failed to redirect to Exambase. Current URL: {self.driver.current_url}"
                    )

                else:
                    # Already on Exambase, no login needed
                    self._log("✓ Already on Exambase, no login needed")
                    self.logger.info("✅ Exambase access successful", force=True)
                    return True

            except (TimeoutException, WebDriverException, Exception) as e:
                error_msg = str(e)
                self.logger.warning(
                    f"⚠️ Login attempt {attempt}/{max_retries} failed: {error_msg}"
                )

                if attempt >= max_retries:
                    self.logger.error(
                        f"❌ Exambase login failed after {max_retries} attempts. Please check your network and credentials."
                    )
                    return False

                # Wait before retry
                time.sleep(2)

        return False

    def get_course_codes_from_knowledge_base(self):
        """
        Extract course codes from knowledge_base directory names

        Returns:
            list: List of tuples (course_code, full_folder_name)
        """
        course_list = []
        knowledge_base_path = os.path.abspath("knowledge_base")

        if not os.path.exists(knowledge_base_path):
            self._log("✗ knowledge_base directory not found")
            return course_list

        for folder_name in os.listdir(knowledge_base_path):
            folder_path = os.path.join(knowledge_base_path, folder_name)
            if os.path.isdir(folder_path):
                # Extract course code (e.g., COMP7103 from "COMP7103 Data mining [Section 1C, 2025]")
                match = re.match(r"^([A-Z]+\d+)", folder_name)
                if match:
                    course_code = match.group(1)
                    course_list.append((course_code, folder_name))
                    self._log(f"Found course: {course_code} -> {folder_name}")

        return course_list

    def search_course_exams(self, course_code):
        """
        Search for exam papers of a specific course

        Args:
            course_code: Course code like "COMP7103"

        Returns:
            list: List of exam paper links
        """
        try:
            self._log(f"\n[Searching] {course_code}")

            # Go to Exambase home
            self.driver.get(self.exambase_url)
            time.sleep(1)

            # Select "Course number / Course Code" radio button
            self._log("  Selecting 'Course number / Course Code' option...")
            try:
                course_code_radio = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input[value='crs']")
                    )
                )
                self.driver.execute_script("arguments[0].click();", course_code_radio)
                time.sleep(0.5)
            except:
                # Try alternative method
                try:
                    course_code_radio = self.driver.find_element(
                        By.XPATH, "//input[@value='crs']"
                    )
                    self.driver.execute_script(
                        "arguments[0].click();", course_code_radio
                    )
                    time.sleep(0.5)
                except:
                    self._log("  ✗ Could not select course code radio button")
                    return []

            # Enter course code in search box
            self._log(f"  Entering course code: {course_code}")
            search_input = self.driver.find_element(By.NAME, "the_key")
            search_input.clear()
            search_input.send_keys(course_code)

            # Click search button
            self._log("  Clicking search...")
            search_btn = None
            try:
                # The search is actually a link with javascript:check_form();
                search_btn = self.driver.find_element(
                    By.CSS_SELECTOR, "a[href*='check_form']"
                )
                search_btn.click()
            except:
                try:
                    # Try to find the image within the link
                    search_img = self.driver.find_element(
                        By.CSS_SELECTOR, "img[src*='searchbutton']"
                    )
                    # Get the parent <a> tag
                    search_btn = search_img.find_element(By.XPATH, "..")
                    search_btn.click()
                except:
                    try:
                        # Fallback: try any submit button
                        search_btn = self.driver.find_element(
                            By.CSS_SELECTOR, "input[type='submit']"
                        )
                        search_btn.click()
                    except:
                        # Try executing JavaScript directly
                        self._log("  Trying to submit form via JavaScript...")
                        self.driver.execute_script("check_form();")

            # Wait for results page
            time.sleep(1)

            # Check if any results found
            page_source = self.driver.page_source

            if (
                "Total number of hits is 0" in page_source
                or "no hits" in page_source.lower()
            ):
                self._log(f"  ✗ No exam papers found for {course_code}")
                return []

            # Extract exam paper links
            exam_links = []

            try:
                # Find all exam paper links - they are in <td> with class evenResultDetail or oddResultDetail
                result_tds = self.driver.find_elements(
                    By.CSS_SELECTOR, "td.evenResultDetail, td.oddResultDetail"
                )

                for td in result_tds:
                    try:
                        # Find the link within the td
                        link_elem = td.find_element(By.TAG_NAME, "a")
                        link_href = link_elem.get_attribute("href")
                        link_text = link_elem.text.strip()

                        # Check if it's a PDF link (downloadable)
                        if link_href and (
                            "/archive/files/" in link_href
                            or ".pdf" in link_href.lower()
                        ):
                            # Get full text for context
                            td_text = td.text

                            exam_info = {
                                "title": link_text,
                                "url": link_href,
                                "full_text": td_text,
                            }
                            exam_links.append(exam_info)
                            self._log(f"    Found: {link_text}")
                    except:
                        continue

            except Exception as e:
                self._log(f"  ✗ Error extracting exam links: {str(e)}")

            self._log(f"  Total found: {len(exam_links)} exam papers")
            return exam_links

        except Exception as e:
            self._log(f"  ✗ Error searching for {course_code}: {str(e)}")
            return []

    def download_exam_papers(self, course_code, course_folder_name, exam_links):
        """
        Download exam papers for a course

        Args:
            course_code: Course code like "COMP7103"
            course_folder_name: Full folder name in knowledge_base
            exam_links: List of exam paper info dicts

        Returns:
            int: Number of files downloaded
        """
        if not exam_links:
            return 0

        download_count = 0
        course_path = os.path.join("knowledge_base", course_folder_name)

        # Create course directory if it doesn't exist
        if not os.path.exists(course_path):
            os.makedirs(course_path)
            self._log(f"Created directory: {course_path}")

        # Get existing files
        existing_files = set()
        if os.path.exists(course_path):
            for filename in os.listdir(course_path):
                existing_files.add(filename.lower())

        self._log(f"\n[Downloading] {course_code} ({len(exam_links)} papers)")

        # Get cookies from Selenium for authenticated requests
        selenium_cookies = self.driver.get_cookies()
        session = requests.Session()
        for cookie in selenium_cookies:
            session.cookies.set(cookie["name"], cookie["value"])

        for idx, exam_info in enumerate(exam_links, 1):
            try:
                title = exam_info["title"]
                url = exam_info["url"]
                full_text = exam_info.get("full_text", "")

                # Extract exam date from full_text (format: d-m-yyyy)
                exam_date = ""
                date_match = re.search(
                    r"Exam date.*?(\d{1,2}-\d{1,2}-\d{4})", full_text
                )
                if date_match:
                    exam_date = date_match.group(1)
                    # Convert to YYYY-MM-DD format for better sorting
                    try:
                        d, m, y = exam_date.split("-")
                        exam_date = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                    except:
                        pass

                # Extract remark (subclass info) if exists
                remark = ""
                remark_match = re.search(r"Remark:\s*([^<\n]+)", full_text)
                if remark_match:
                    remark_text = remark_match.group(1).strip()
                    if "subclass" in remark_text.lower():
                        # First, match the section after "subclass" or "subclasses"(e.g., "A, B, C")
                        subclass_section = re.search(
                            r"subclass(?:es)?\s*:\s*(.*)|subclass(?:es)?\s+(.*)",
                            remark_text,
                            re.IGNORECASE,
                        )
                        if subclass_section:
                            # Extract the target part after "subclass" or "subclasses"(concatenate both groups to avoid missing matches)
                            target_part = subclass_section.group(
                                1
                            ) or subclass_section.group(2)
                            if target_part:
                                # Second step: extract all uppercase letters from the target part (regardless of whether they are separated by commas, "and", or spaces)
                                subclass_matches = re.findall(r"[A-Z]", target_part)
                                if subclass_matches:
                                    unique_subclasses = list(
                                        dict.fromkeys(subclass_matches)
                                    )  # 保持顺序去重
                                    remark = "_subclass_" + "_".join(unique_subclasses)

                # Generate filename from title
                # Example: "Data mining" -> "Data_mining_exam.pdf"
                filename = re.sub(r"[^\w\s-]", "", title)
                filename = re.sub(r"\s+", "_", filename)

                # Add course code prefix if not present
                if not filename.startswith(course_code):
                    filename = f"{course_code}_{filename}"

                # Add exam date and remark to make filename unique
                if exam_date:
                    filename = f"{filename}_{exam_date}{remark}"
                elif remark:
                    filename = f"{filename}{remark}"

                # Ensure .pdf extension
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"

                # Check if already downloaded
                if filename.lower() in existing_files:
                    self._log(
                        f"  [{idx}/{len(exam_links)}] ⊘ Already exists: {filename}"
                    )
                    continue

                self._log(f"  [{idx}/{len(exam_links)}] Downloading: {filename}")

                # The URL is already a direct PDF link, no need to navigate
                pdf_url = url

                # Download with requests
                try:
                    response = session.get(pdf_url, timeout=30, stream=True)
                    response.raise_for_status()

                    # Save file
                    file_path = os.path.join(course_path, filename)
                    with open(file_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    file_size = os.path.getsize(file_path)
                    if file_size > 0:
                        self._log(f"      ✓ Downloaded ({file_size:,} bytes)")
                        download_count += 1
                    else:
                        self._log("      ✗ Downloaded but file is empty")
                        os.remove(file_path)
                except Exception as e:
                    self._log(f"      ✗ Download failed: {str(e)}")

            except Exception as e:
                self._log(f"  [{idx}/{len(exam_links)}] ✗ Error: {str(e)}")
                continue

        return download_count

    def download_all_courses(self, course_filter=None):
        """
        Main method to download exam papers for all courses

        Args:
            course_filter (list, optional): List of full course names to download.
                                           If None, get courses from knowledge_base folders.
                                           If provided, parse course codes and search directly.

        Returns:
            dict: Statistics about downloads
        """
        self._log("\n" + "=" * 50)
        self._log("Starting Exambase download...")
        self._log("=" * 50)

        # If course_filter is provided, parse course codes directly from it
        if course_filter:
            self._log(f"Processing {len(course_filter)} filtered courses")
            course_list = []
            from .moodle import HKUMoodleScraper

            for course_name in course_filter:
                # Extract course code (e.g., COMP7103 from "COMP7103 Data mining [Section 1C, 2025]")
                match = re.match(r"^([A-Z]+\d+)", course_name)
                if match:
                    course_code = match.group(1)
                    # Use sanitized course name as folder name
                    scraper_temp = HKUMoodleScraper(headless=True, verbose=False)
                    folder_name = scraper_temp._sanitize_filename(course_name)
                    course_list.append((course_code, folder_name))

            if not course_list:
                self._log("✗ No valid courses in filter")
                return {"total_courses": 0, "total_downloads": 0}
        else:
            # Get course codes from knowledge_base
            course_list = self.get_course_codes_from_knowledge_base()

            if not course_list:
                self._log("✗ No courses found in knowledge_base")
                return {"total_courses": 0, "total_downloads": 0}

        self._log(f"\nFound {len(course_list)} courses to process\n")

        stats = {
            "total_courses": len(course_list),
            "processed_courses": 0,
            "total_downloads": 0,
            "courses_with_exams": 0,
        }

        # Group courses by course code to search only once per code
        from collections import defaultdict

        courses_by_code = defaultdict(list)
        for course_code, folder_name in course_list:
            courses_by_code[course_code].append(folder_name)

        for course_code, folder_names in courses_by_code.items():
            # Search for exam papers (only once per course code)
            exam_links = self.search_course_exams(course_code)

            if exam_links:
                stats["courses_with_exams"] += 1
                # Download exam papers to all folders with this course code
                for folder_name in folder_names:
                    download_count = self.download_exam_papers(
                        course_code, folder_name, exam_links
                    )
                    stats["total_downloads"] += download_count
                    stats["processed_courses"] += 1
            else:
                # No exams found, just count the processed courses
                stats["processed_courses"] += len(folder_names)

            # Small delay between courses
            time.sleep(1)

        return stats

    def _search_and_download_course(self, course_code, course_dirs):
        """
        Search and download exams for a single course code
        This is extracted for parallel downloading support

        Args:
            course_code: Course code to search (e.g., "COMP7103")
            course_dirs: List of directory paths for this course

        Returns:
            int: Number of files downloaded
        """
        # Search for exam papers
        exam_links = self.search_course_exams(course_code)

        if not exam_links:
            return 0

        total_downloads = 0
        # Download to all matching directories
        for folder_name in course_dirs:
            download_count = self.download_exam_papers(
                course_code, folder_name, exam_links
            )
            total_downloads += download_count

        time.sleep(0.5)  # Small delay
        return total_downloads

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()


def main():
    parser = argparse.ArgumentParser(
        description="Download exam papers from HKU Exambase for courses in knowledge_base"
    )
    parser.add_argument(
        "-u",
        "--username",
        required=True,
        help="HKU Portal UID (without @connect.hku.hk or @hku.hk)",
    )
    parser.add_argument("-p", "--password", required=True, help="Password")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no browser window)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Remove email suffix if present
    username = args.username.split("@")[0]

    from .logger import get_logger

    logger = get_logger(log_file="rag_scraper.log", verbose=True)

    logger.info(f"Exambase Scraper for HKU", force=True)
    logger.info(f"Username: {username}", force=True)
    logger.info(f"Verbose: {args.verbose}", force=True)
    logger.info(f"Headless: {args.headless}", force=True)
    logger.info("-" * 50, force=True)

    scraper = None
    if "@" in args.username:
        logger.info(
            "Warning: Username should not contain '@'. It has been removed.", force=True
        )
        username = username.split("@")[0]

    try:
        # Initialize scraper
        scraper = ExambaseScraper(
            username=username,
            password=args.password,
            headless=args.headless,
            verbose=args.verbose,
        )

        # Login
        start_time = time.time()
        if not scraper.login():
            logger.error("\n✗ Login failed. Please check your credentials.")
            return

        login_time = time.time() - start_time
        logger.info(f"\n✓ Login successful ({login_time:.2f}s)", force=True)

        # Download exam papers
        download_start = time.time()
        stats = scraper.download_all_courses()
        download_time = time.time() - download_start

        # Print summary
        logger.info("\n" + "=" * 50, force=True)
        logger.info("SUMMARY", force=True)
        logger.info("=" * 50, force=True)
        logger.info(f"Total courses: {stats['total_courses']}", force=True)
        logger.info(f"Processed courses: {stats['processed_courses']}", force=True)
        logger.info(f"Courses with exams: {stats['courses_with_exams']}", force=True)
        logger.info(f"Total downloads: {stats['total_downloads']}", force=True)
        logger.info(f"Login time: {login_time:.2f}s", force=True)
        logger.info(f"Download time: {download_time:.2f}s", force=True)
        logger.info(f"Total time: {login_time + download_time:.2f}s", force=True)
        logger.info("=" * 50, force=True)

    except KeyboardInterrupt:
        logger.info("\n\n⚠ Interrupted by user", force=True)
    except Exception as e:
        logger.error(f"\n✗ Error: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()
