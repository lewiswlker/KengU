#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parallel downloading support for RAG Scraper
Allows downloading from multiple courses simultaneously using multiple browser instances
"""

import os
import time
import threading
from queue import Queue

# Global login lock to prevent concurrent login conflicts
_login_lock = threading.Lock()


class ParallelMoodleDownloader:
    """
    Parallel downloader for Moodle courses
    Creates multiple browser instances to download courses in parallel
    """

    def __init__(self, username, password, headless=True, verbose=False, num_workers=2):
        """
        Initialize parallel downloader

        Args:
            username: HKU email
            password: Password
            headless: Run browsers in headless mode
            verbose: Enable verbose logging
            num_workers: Number of parallel browser instances (default: 2)
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.verbose = verbose
        self.num_workers = num_workers

        # Thread-safe counters
        self.total_downloads = 0
        self.download_lock = threading.Lock()

    def _log(self, message, force=False):
        """Thread-safe logging"""
        if self.verbose or force:
            print(f"[Thread-{threading.current_thread().name}] {message}")

    def _create_authenticated_driver(self):
        """
        Create a new browser instance and authenticate it
        Returns authenticated driver

        Uses global lock to prevent concurrent login conflicts
        """
        from rag_scraper.moodle import HKUMoodleScraper

        # Create a new scraper instance for this thread
        scraper = HKUMoodleScraper(headless=self.headless, verbose=False)

        # Login with lock to avoid conflicts
        with _login_lock:
            self._log("Waiting for login lock...", force=True)
            scraper.connect_moodle(self.username, self.password)
            self._log("Login completed, releasing lock", force=True)
            # Add small delay after login to avoid session conflicts
            time.sleep(2)

        return scraper

    def _download_worker(self, task_queue, results_queue, base_dir):
        """
        Worker function that processes courses from the queue

        Args:
            task_queue: Queue containing (course_name, course_url) tuples
            results_queue: Queue to put results
            base_dir: Base directory for downloads
        """
        worker_id = threading.current_thread().name
        scraper = None
        downloaded_count = 0

        try:
            # Create authenticated browser for this worker
            self._log(f"Worker {worker_id} starting, creating browser...", force=True)
            scraper = self._create_authenticated_driver()
            self._log(f"Worker {worker_id} authenticated successfully", force=True)

            # Process courses from queue
            while not task_queue.empty():
                try:
                    # Get task with timeout to avoid hanging
                    course_name, course_url = task_queue.get(timeout=1)

                    self._log(f"Processing: {course_name}", force=True)

                    # Download this course using the scraper's logic
                    files_downloaded = self._download_single_course(
                        scraper, course_name, course_url, base_dir
                    )

                    downloaded_count += files_downloaded

                    # Mark task as done
                    task_queue.task_done()

                except Exception as e:
                    if "Empty" not in str(e):  # Ignore empty queue errors
                        self._log(f"Error processing course: {str(e)}", force=True)
                        import traceback

                        traceback.print_exc()

        finally:
            # Clean up browser
            if scraper:
                scraper.close()
                self._log(f"Worker {worker_id} closed browser", force=True)

            # Report results
            results_queue.put(downloaded_count)
            self._log(
                f"Worker {worker_id} finished, downloaded {downloaded_count} files",
                force=True,
            )

    def _download_single_course(self, scraper, course_name, course_url, base_dir):
        """
        Download a single course using the scraper's existing logic
        This is extracted from HKUMoodleScraper.download_all_courses()
        """
        from bs4 import BeautifulSoup
        from urllib.parse import unquote
        import requests

        # Special handling for NLP courses
        if "Natural language processing" in course_name or "NLP" in course_name.upper():
            return scraper._download_nlp_course(base_dir, course_name)

        # Create course directory
        safe_course_name = scraper._sanitize_filename(course_name)
        course_dir = os.path.join(base_dir, safe_course_name)

        if not os.path.exists(course_dir):
            os.makedirs(course_dir)

        # Track existing files
        existing_files = set(f.lower() for f in os.listdir(course_dir))
        downloaded_in_this_run = set()

        VALID_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"}

        try:
            # Navigate to course page
            scraper.driver.get(course_url)
            time.sleep(0.5)

            # Get page source
            page_source = scraper.driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            # Get cookies for authenticated requests
            selenium_cookies = scraper.driver.get_cookies()
            session = requests.Session()
            for cookie in selenium_cookies:
                session.cookies.set(cookie["name"], cookie["value"])

            download_links = []

            # Find all resource and folder links
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # Make absolute URL
                if href.startswith("/"):
                    href = f"https://moodle.hku.hk{href}"

                # Case 1: Direct pluginfile.php links
                if "/pluginfile.php" in href:
                    filename = href.split("/")[-1].split("?")[0]
                    filename = unquote(filename)

                    if filename and len(filename) >= 3:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in VALID_EXTENSIONS:
                            self._log(f"    Checking: {text}")
                            self._log(f"      Found direct file: {filename}")
                            download_links.append((filename, href))

                # Case 2: Resource/folder pages - need to fetch and extract
                elif "/mod/resource/" in href or "/mod/folder/" in href:
                    self._log(f"    Checking: {text}")
                    try:
                        response = session.get(href, timeout=5)
                        if response.status_code == 200:
                            sub_soup = BeautifulSoup(response.text, "html.parser")
                            for sub_link in sub_soup.find_all("a", href=True):
                                sub_href = sub_link.get("href", "")
                                if "/pluginfile.php" in sub_href:
                                    if sub_href.startswith("/"):
                                        sub_href = f"https://moodle.hku.hk{sub_href}"

                                    filename = sub_href.split("/")[-1].split("?")[0]
                                    filename = unquote(filename)

                                    if filename and len(filename) >= 3:
                                        ext = os.path.splitext(filename)[1].lower()
                                        if ext in VALID_EXTENSIONS:
                                            self._log(f"      Found: {filename}")
                                            download_links.append((filename, sub_href))
                    except Exception as e:
                        self._log(f"      Error fetching resource page: {str(e)}")

            # Remove duplicates
            unique_links = {}
            for filename, url in download_links:
                if filename.lower() not in unique_links:
                    unique_links[filename.lower()] = (filename, url)

            download_links = list(unique_links.values())

            self._log(f"Found {len(download_links)} downloadable files")

            # Download files
            new_downloads = 0
            for idx, (filename, url) in enumerate(download_links, 1):
                filepath = os.path.join(course_dir, filename)
                filename_lower = filename.lower()

                # Check if already exists
                if (
                    filename_lower in existing_files
                    or filename_lower in downloaded_in_this_run
                ):
                    self._log(
                        f"  [{idx}/{len(download_links)}] {filename} - Already exists"
                    )
                    continue

                # Download
                self._log(f"  [{idx}/{len(download_links)}] Downloading: {filename}")
                try:
                    response = session.get(url, timeout=30)
                    if response.status_code == 200:
                        with open(filepath, "wb") as f:
                            f.write(response.content)
                        self._log(f"      ✓ Downloaded")
                        downloaded_in_this_run.add(filename_lower)
                        new_downloads += 1
                    else:
                        self._log(f"      ✗ Failed: HTTP {response.status_code}")
                except Exception as e:
                    self._log(f"      ✗ Error: {str(e)}")

            self._log(f"  ✓ Completed: {course_name} ({new_downloads} new files)")
            return new_downloads

        except Exception as e:
            self._log(f"  ✗ Error processing {course_name}: {str(e)}")
            import traceback

            traceback.print_exc()
            return 0

    def download_all_courses_parallel(self, course_urls, base_dir="knowledge_base"):
        """
        Download all courses in parallel using multiple browser instances

        Args:
            course_urls: Dict of {course_name: course_url}
            base_dir: Base directory for downloads

        Returns:
            Total number of files downloaded
        """
        print(f"\n{'='*50}")
        print(f"Starting PARALLEL download with {self.num_workers} workers...")
        print(f"{'='*50}\n")

        # Create base directory
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # Create task queue
        task_queue = Queue()
        for course_name, course_url in course_urls.items():
            task_queue.put((course_name, course_url))

        # Create results queue
        results_queue = Queue()

        # Start worker threads
        threads = []
        for i in range(self.num_workers):
            thread = threading.Thread(
                target=self._download_worker,
                args=(task_queue, results_queue, base_dir),
                name=f"Worker-{i+1}",
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)

        # Wait for all tasks to complete
        task_queue.join()

        # Wait for all threads to finish
        for thread in threads:
            thread.join(timeout=5)

        # Collect results
        total_downloads = 0
        while not results_queue.empty():
            total_downloads += results_queue.get()

        print(f"\n{'='*50}")
        print(f"Parallel download completed!")
        print(f"Total files downloaded: {total_downloads}")
        print(f"Saved to: {os.path.abspath(base_dir)}")
        print(f"{'='*50}\n")

        return total_downloads


class ParallelExambaseDownloader:
    """
    Parallel downloader for Exambase
    Creates multiple browser instances to search and download exams in parallel
    """

    def __init__(
        self, username, password, headless=False, verbose=False, num_workers=2
    ):
        """
        Initialize parallel Exambase downloader

        Args:
            username: HKU UID (without @domain)
            password: Password
            headless: Run browsers in headless mode
            verbose: Enable verbose logging
            num_workers: Number of parallel browser instances (default: 2)
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.verbose = verbose
        self.num_workers = num_workers

    def _log(self, message, force=False):
        """Thread-safe logging"""
        if self.verbose or force:
            print(f"[Thread-{threading.current_thread().name}] {message}")

    def _create_authenticated_driver(self):
        """
        Create and authenticate a new browser instance
        Uses global lock to prevent concurrent login conflicts
        """
        from rag_scraper.exambase import ExambaseScraper

        scraper = ExambaseScraper(
            self.username, self.password, headless=self.headless, verbose=False
        )

        # Login with lock to avoid conflicts
        with _login_lock:
            self._log("Waiting for login lock...", force=True)
            if not scraper.login():
                raise Exception("Failed to login to Exambase")
            self._log("Login completed, releasing lock", force=True)
            # Add small delay after login to avoid session conflicts
            time.sleep(2)

        return scraper

    def _download_worker(self, task_queue, results_queue, course_mapping):
        """
        Worker function that processes course codes from the queue

        Args:
            task_queue: Queue containing course codes
            results_queue: Queue to put results
            course_mapping: Dict mapping course codes to course directories
        """
        worker_id = threading.current_thread().name
        scraper = None
        total_downloads = 0

        try:
            # Create authenticated browser
            self._log(f"Worker {worker_id} creating browser...", force=True)
            scraper = self._create_authenticated_driver()
            self._log(f"Worker {worker_id} authenticated", force=True)

            # Process courses
            while not task_queue.empty():
                try:
                    course_code = task_queue.get(timeout=1)
                    course_dirs = course_mapping[course_code]

                    self._log(f"[Searching] {course_code}", force=True)

                    # Use scraper's existing logic to download
                    downloads = scraper._search_and_download_course(
                        course_code, course_dirs
                    )
                    total_downloads += downloads

                    task_queue.task_done()

                except Exception as e:
                    if "Empty" not in str(e):
                        self._log(f"Error: {str(e)}", force=True)

        finally:
            if scraper:
                scraper.close()
                self._log(f"Worker {worker_id} closed", force=True)

            results_queue.put(total_downloads)
            self._log(
                f"Worker {worker_id} downloaded {total_downloads} papers", force=True
            )

    def download_all_courses_parallel(self, course_mapping):
        """
        Download exams for all courses in parallel

        Args:
            course_mapping: Dict mapping course codes to list of directories

        Returns:
            Dict with download statistics
        """
        print(f"\n{'='*50}")
        print(f"Starting PARALLEL Exambase download with {self.num_workers} workers...")
        print(f"{'='*50}\n")

        # Create task queue
        task_queue = Queue()
        for course_code in course_mapping.keys():
            task_queue.put(course_code)

        # Create results queue
        results_queue = Queue()

        # Start workers
        threads = []
        for i in range(self.num_workers):
            thread = threading.Thread(
                target=self._download_worker,
                args=(task_queue, results_queue, course_mapping),
                name=f"ExamWorker-{i+1}",
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)

        # Wait for completion
        task_queue.join()

        for thread in threads:
            thread.join(timeout=5)

        # Collect results
        total_downloads = 0
        while not results_queue.empty():
            total_downloads += results_queue.get()

        return {
            "total_downloads": total_downloads,
            "total_courses": len(course_mapping),
            "courses_with_exams": len([c for c in course_mapping if course_mapping[c]]),
        }
