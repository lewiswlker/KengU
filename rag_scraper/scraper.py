#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Scraper - Unified interface for downloading HKU course materials
Downloads materials from both Moodle and Exambase
"""

import os
import time
import threading
from .moodle import HKUMoodleScraper
from .exambase import ExambaseScraper
from .logger import get_logger


class RAGScraper:
    """
    Unified scraper for HKU course materials

    Downloads course materials from:
    - Moodle: Course files, assignments, resources
    - Exambase: Past exam papers

    All files are saved to the 'knowledge_base' directory
    """

    def __init__(
        self, email, password, headless=True, verbose=False, parallel_workers=1
    ):
        """
        Initialize RAG Scraper

        Args:
            email (str): HKU email address (e.g., u3665467@connect.hku.hk)
            password (str): Password
            headless (bool): Run browsers in headless mode (default: True)
            verbose (bool): Enable verbose logging (default: False)
            parallel_workers (int): Number of parallel browser instances (default: 1, set to 2+ for parallel mode)
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.verbose = verbose
        self.parallel_workers = parallel_workers

        # Extract username from email
        self.username = email.split("@")[0] if "@" in email else email

        # Statistics
        self.stats = {"moodle": {}, "exambase": {}, "total_time": 0, "success": False}

        # Thread lock for print synchronization
        self._print_lock = threading.Lock()

        # Initialize logger
        self.logger = get_logger(log_file="rag_scraper.log", verbose=verbose)

    def _print(self, message, force=False):
        """Print message if verbose or force (thread-safe with timestamp)"""
        if self.verbose or force:
            self.logger.info(message, force=force)

    def scrape_all(self, moodle_courses=None, exambase_courses=None):
        """
        Main method to scrape all materials from Moodle and Exambase

        Args:
            moodle_courses (list, optional): List of course names to scrape from Moodle. If None, scrape all courses.
            exambase_courses (list, optional): List of course names to scrape from Exambase. If None, scrape all courses.

        Returns:
            dict: Statistics about the download process
        """
        start_time = time.time()

        self._print("=" * 60, force=True)
        self._print("RAG Scraper - HKU Course Materials Downloader", force=True)
        self._print("=" * 60, force=True)
        self._print(f"Email: {self.email}", force=True)
        self._print(f"Headless: {self.headless}", force=True)
        self._print(f"Verbose: {self.verbose}", force=True)
        self._print("-" * 60, force=True)

        try:
            # Run Moodle and Exambase in parallel using threading
            self._print(
                "\n🚀 Starting parallel scraping (Moodle + Exambase simultaneously)...",
                force=True,
            )
            self._print("-" * 60, force=True)

            moodle_stats = {}
            exambase_stats = {}

            def moodle_worker():
                nonlocal moodle_stats
                self._print("\n[MOODLE] Starting...", force=True)
                moodle_stats = self._scrape_moodle(moodle_courses)
                self._print("[MOODLE] Completed!", force=True)

            def exambase_worker():
                nonlocal exambase_stats
                self._print("\n[EXAMBASE] Starting...", force=True)
                exambase_stats = self._scrape_exambase(exambase_courses)
                self._print("[EXAMBASE] Completed!", force=True)

            # Create threads
            moodle_thread = threading.Thread(target=moodle_worker, name="MoodleThread")
            exambase_thread = threading.Thread(
                target=exambase_worker, name="ExambaseThread"
            )

            # Start both threads
            moodle_thread.start()
            exambase_thread.start()

            # Wait for both to complete
            moodle_thread.join()
            exambase_thread.join()

            self.stats["moodle"] = moodle_stats
            self.stats["exambase"] = exambase_stats

            # Calculate total time
            self.stats["total_time"] = time.time() - start_time
            self.stats["success"] = True

            # Print summary
            self._print_summary()

            return self.stats

        except KeyboardInterrupt:
            self._print("\n\n⚠ Interrupted by user", force=True)
            self.stats["success"] = False
            return self.stats
        except Exception as e:
            self._print(f"\n✗ Error: {str(e)}", force=True)
            import traceback

            if self.verbose:
                traceback.print_exc()
            self.stats["success"] = False
            return self.stats

    def _scrape_moodle(self, course_filter=None):
        """
        Scrape course materials from Moodle

        Args:
            course_filter (list, optional): List of course names to scrape.
                                           If None or empty list, skip Moodle scraping entirely.

        Returns:
            dict: Moodle scraping statistics
        """
        # If course_filter is None or empty list, skip Moodle scraping
        if course_filter is None or len(course_filter) == 0:
            self._print("⊘ Skipping Moodle (no courses to update)", force=True)
            return {
                "courses": 0,
                "files_downloaded": 0,
                "login_time": 0,
                "extract_time": 0,
                "download_time": 0,
                "total_time": 0,
                "success": True,
                "skipped": True,
            }

        scraper = None
        try:
            # Check if parallel mode is enabled
            if self.parallel_workers > 1:
                return self._scrape_moodle_parallel(course_filter)

            # Initialize Moodle scraper
            scraper = HKUMoodleScraper(headless=self.headless, verbose=self.verbose)

            # Login to Moodle
            login_time = scraper.connect_moodle(self.email, self.password)

            # Get courses
            courses, extract_time = scraper.get_courses()

            if not courses:
                self._print("✗ No courses found on Moodle", force=True)
                return {
                    "courses": 0,
                    "files_downloaded": 0,
                    "login_time": login_time,
                    "extract_time": extract_time,
                    "download_time": 0,
                    "total_time": login_time + extract_time,
                    "success": False,
                }

            self._print(f"✓ Found {len(courses)} courses on Moodle", force=True)

            # Download all course materials
            download_start = time.time()
            downloaded_files = scraper.download_all_courses(
                base_dir="knowledge_base", course_filter=course_filter
            )
            download_time = time.time() - download_start

            stats = {
                "courses": len(courses),
                "files_downloaded": downloaded_files,
                "login_time": login_time,
                "extract_time": extract_time,
                "download_time": download_time,
                "total_time": login_time + extract_time + download_time,
                "success": True,
            }

            self._print(
                f"✓ Moodle: Downloaded {downloaded_files} files from {len(courses)} courses",
                force=True,
            )

            return stats

        except Exception as e:
            self._print(f"✗ Moodle scraping failed: {str(e)}", force=True)
            if self.verbose:
                import traceback

                traceback.print_exc()
            return {
                "courses": 0,
                "files_downloaded": 0,
                "login_time": 0,
                "extract_time": 0,
                "download_time": 0,
                "total_time": 0,
                "success": False,
                "error": str(e),
            }
        finally:
            if scraper:
                scraper.close()

    def _scrape_moodle_parallel(self, course_filter=None):
        """
        Scrape course materials from Moodle using parallel workers

        Args:
            course_filter (list, optional): List of course names to scrape.
                                           If None or empty list, skip Moodle scraping entirely.

        Returns:
            dict: Moodle scraping statistics
        """
        # If course_filter is None or empty list, skip Moodle scraping
        if course_filter is None or len(course_filter) == 0:
            self._print("⊘ Skipping Moodle (no courses to update)", force=True)
            return {
                "courses": 0,
                "files_downloaded": 0,
                "login_time": 0,
                "extract_time": 0,
                "download_time": 0,
                "total_time": 0,
                "success": True,
                "skipped": True,
            }

        from .parallel import ParallelMoodleDownloader

        try:
            # First, get course list using single browser
            self._print(f"Getting course list...", force=True)
            scraper = HKUMoodleScraper(headless=self.headless, verbose=False)

            login_time = scraper.connect_moodle(self.email, self.password)
            courses, extract_time = scraper.get_courses()

            if not courses:
                scraper.close()
                return {
                    "courses": 0,
                    "files_downloaded": 0,
                    "login_time": login_time,
                    "extract_time": extract_time,
                    "download_time": 0,
                    "total_time": login_time + extract_time,
                    "success": False,
                }

            self._print(f"✓ Found {len(courses)} courses", force=True)

            # Filter courses if specified
            if course_filter:
                course_urls = {
                    name: url
                    for name, url in scraper.course_urls.items()
                    if name in course_filter
                }
                self._print(f"✓ Filtered to {len(course_urls)} courses", force=True)
            else:
                course_urls = scraper.course_urls

            self._print(
                f"✓ Starting parallel download with {self.parallel_workers} workers",
                force=True,
            )

            scraper.close()

            # Use parallel downloader
            download_start = time.time()
            parallel_downloader = ParallelMoodleDownloader(
                self.email,
                self.password,
                headless=self.headless,
                verbose=self.verbose,
                num_workers=self.parallel_workers,
            )

            downloaded_files = parallel_downloader.download_all_courses_parallel(
                course_urls, base_dir="knowledge_base"
            )
            download_time = time.time() - download_start

            stats = {
                "courses": len(course_urls),
                "files_downloaded": downloaded_files,
                "login_time": login_time,
                "extract_time": extract_time,
                "download_time": download_time,
                "total_time": login_time + extract_time + download_time,
                "success": True,
                "parallel_workers": self.parallel_workers,
            }

            self._print(
                f"✓ Moodle (PARALLEL): Downloaded {downloaded_files} files from {len(course_urls)} courses",
                force=True,
            )

            return stats

        except Exception as e:
            self._print(f"✗ Parallel Moodle scraping failed: {str(e)}", force=True)
            if self.verbose:
                import traceback

                traceback.print_exc()
            return {
                "courses": 0,
                "files_downloaded": 0,
                "login_time": 0,
                "extract_time": 0,
                "download_time": 0,
                "total_time": 0,
                "success": False,
                "error": str(e),
            }

    def _scrape_exambase(self, course_filter=None):
        """
        Scrape exam papers from Exambase

        Args:
            course_filter (list, optional): List of full course names to scrape.
                                           If None or empty list, skip Exambase scraping entirely.

        Returns:
            dict: Exambase scraping statistics
        """
        # If course_filter is None or empty list, skip Exambase scraping
        if course_filter is None or len(course_filter) == 0:
            self._print("⊘ Skipping Exambase (no courses to update)", force=True)
            return {
                "courses": 0,
                "courses_with_exams": 0,
                "exams_downloaded": 0,
                "login_time": 0,
                "download_time": 0,
                "total_time": 0,
                "success": True,
                "skipped": True,
            }

        scraper = None
        try:
            # Check if parallel mode is enabled
            if self.parallel_workers > 1:
                return self._scrape_exambase_parallel(course_filter)

            # Initialize Exambase scraper
            scraper = ExambaseScraper(
                username=self.username,
                password=self.password,
                headless=self.headless,
                verbose=self.verbose,
            )

            # Login
            login_start = time.time()
            if not scraper.login():
                self._print("✗ Exambase login failed", force=True)
                return {
                    "courses": 0,
                    "exams_downloaded": 0,
                    "login_time": time.time() - login_start,
                    "download_time": 0,
                    "total_time": time.time() - login_start,
                    "success": False,
                }

            login_time = time.time() - login_start
            self._print(f"✓ Exambase login successful ({login_time:.2f}s)", force=True)

            # Download exam papers
            download_start = time.time()
            stats = scraper.download_all_courses(course_filter=course_filter)
            download_time = time.time() - download_start

            result = {
                "courses": stats.get("total_courses", 0),
                "courses_with_exams": stats.get("courses_with_exams", 0),
                "exams_downloaded": stats.get("total_downloads", 0),
                "login_time": login_time,
                "download_time": download_time,
                "total_time": login_time + download_time,
                "success": True,
            }

            self._print(
                f"✓ Exambase: Downloaded {result['exams_downloaded']} exam papers "
                f"from {result['courses_with_exams']}/{result['courses']} courses",
                force=True,
            )

            return result

        except Exception as e:
            self._print(f"✗ Exambase scraping failed: {str(e)}", force=True)
            if self.verbose:
                import traceback

                traceback.print_exc()
            return {
                "courses": 0,
                "exams_downloaded": 0,
                "login_time": 0,
                "download_time": 0,
                "total_time": 0,
                "success": False,
                "error": str(e),
            }
        finally:
            if scraper:
                scraper.close()

    def _scrape_exambase_parallel(self, course_filter=None):
        """
        Scrape exam papers from Exambase using parallel workers

        Args:
            course_filter (list, optional): List of full course names to scrape.
                                           If None or empty list, skip Exambase scraping entirely.

        Returns:
            dict: Exambase scraping statistics
        """
        # If course_filter is None or empty list, skip Exambase scraping
        if course_filter is None or len(course_filter) == 0:
            self._print("⊘ Skipping Exambase (no courses to update)", force=True)
            return {
                "courses": 0,
                "courses_with_exams": 0,
                "exams_downloaded": 0,
                "login_time": 0,
                "download_time": 0,
                "total_time": 0,
                "success": True,
                "skipped": True,
            }

        from .parallel import ParallelExambaseDownloader
        from collections import defaultdict
        import re

        try:
            # If course_filter is provided, parse course codes directly from it
            if course_filter:
                # Parse course codes and folder names from full course names
                self._print(
                    f"Processing {len(course_filter)} filtered courses...", force=True
                )
                course_list = []
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
                    self._print("✗ No valid courses in filter", force=True)
                    return {
                        "courses": 0,
                        "exams_downloaded": 0,
                        "login_time": 0,
                        "download_time": 0,
                        "total_time": 0,
                        "success": False,
                    }
            else:
                # Get course codes from knowledge_base directory (no login needed!)
                self._print(f"Reading course codes from knowledge_base...", force=True)

                knowledge_base_path = os.path.abspath("knowledge_base")

                if not os.path.exists(knowledge_base_path):
                    self._print("✗ knowledge_base directory not found", force=True)
                    return {
                        "courses": 0,
                        "exams_downloaded": 0,
                        "login_time": 0,
                        "download_time": 0,
                        "total_time": 0,
                        "success": False,
                    }

                # Extract course codes from folder names
                course_list = []
                for folder_name in os.listdir(knowledge_base_path):
                    folder_path = os.path.join(knowledge_base_path, folder_name)
                    if os.path.isdir(folder_path):
                        # Extract course code (e.g., COMP7103 from "COMP7103 Data mining")
                        match = re.match(r"^([A-Z]+\d+)", folder_name)
                        if match:
                            course_code = match.group(1)
                            course_list.append((course_code, folder_name))

                if not course_list:
                    self._print("✗ No courses found in knowledge_base", force=True)
                    return {
                        "courses": 0,
                        "exams_downloaded": 0,
                        "login_time": 0,
                        "download_time": 0,
                        "total_time": 0,
                        "success": False,
                    }

            # Group courses by code
            courses_by_code = defaultdict(list)
            for course_code, folder_name in course_list:
                courses_by_code[course_code].append(folder_name)

            self._print(
                f"✓ Found {len(courses_by_code)} unique course codes", force=True
            )
            self._print(
                f"✓ Starting parallel download with {self.parallel_workers} workers",
                force=True,
            )

            # Use parallel downloader (each worker will login independently)
            download_start = time.time()
            parallel_downloader = ParallelExambaseDownloader(
                self.username,
                self.password,
                headless=self.headless,
                verbose=self.verbose,
                num_workers=self.parallel_workers,
            )

            stats = parallel_downloader.download_all_courses_parallel(courses_by_code)
            download_time = time.time() - download_start

            result = {
                "courses": stats["total_courses"],
                "courses_with_exams": stats["courses_with_exams"],
                "exams_downloaded": stats["total_downloads"],
                "login_time": 0,  # No pre-login needed
                "download_time": download_time,
                "total_time": download_time,
                "success": True,
                "parallel_workers": self.parallel_workers,
            }

            self._print(
                f"✓ Exambase (PARALLEL): Downloaded {result['exams_downloaded']} exam papers "
                f"from {result['courses_with_exams']}/{result['courses']} courses",
                force=True,
            )

            return result

        except Exception as e:
            self._print(f"✗ Parallel Exambase scraping failed: {str(e)}", force=True)
            if self.verbose:
                import traceback

                traceback.print_exc()
            return {
                "courses": 0,
                "exams_downloaded": 0,
                "login_time": 0,
                "download_time": 0,
                "total_time": 0,
                "success": False,
                "error": str(e),
            }

    def _print_summary(self):
        """Print summary of the scraping process"""
        self._print("\n" + "=" * 60, force=True)
        self._print("SUMMARY", force=True)
        self._print("=" * 60, force=True)

        # Moodle stats
        moodle = self.stats.get("moodle", {})
        self._print(f"\nMoodle:", force=True)
        self._print(f"  Courses: {moodle.get('courses', 0)}", force=True)
        self._print(
            f"  Files downloaded: {moodle.get('files_downloaded', 0)}", force=True
        )
        self._print(f"  Time: {moodle.get('total_time', 0):.2f}s", force=True)
        self._print(
            f"  Status: {'✓ Success' if moodle.get('success') else '✗ Failed'}",
            force=True,
        )

        # Exambase stats
        exambase = self.stats.get("exambase", {})
        self._print(f"\nExambase:", force=True)
        self._print(f"  Courses: {exambase.get('courses', 0)}", force=True)
        self._print(
            f"  Courses with exams: {exambase.get('courses_with_exams', 0)}", force=True
        )
        self._print(
            f"  Exam papers downloaded: {exambase.get('exams_downloaded', 0)}",
            force=True,
        )
        self._print(f"  Time: {exambase.get('total_time', 0):.2f}s", force=True)
        self._print(
            f"  Status: {'✓ Success' if exambase.get('success') else '✗ Failed'}",
            force=True,
        )

        # Total
        total_files = moodle.get("files_downloaded", 0) + exambase.get(
            "exams_downloaded", 0
        )
        self._print(f"\nTotal:", force=True)
        self._print(f"  Files downloaded: {total_files}", force=True)
        self._print(f"  Total time: {self.stats.get('total_time', 0):.2f}s", force=True)
        self._print(
            f"  Overall status: {'✓ Success' if self.stats.get('success') else '✗ Failed'}",
            force=True,
        )

        self._print("=" * 60, force=True)
        self._print(
            f"\nAll files saved to: {os.path.abspath('knowledge_base')}", force=True
        )
        self._print("=" * 60, force=True)


# Convenience function for quick usage
def scrape(
    email,
    password,
    headless=True,
    verbose=False,
    parallel_workers=1,
    moodle_courses=None,
    exambase_courses=None,
):
    """
    Convenience function to scrape all materials

    Args:
        email (str): HKU email address
        password (str): Password
        headless (bool): Run in headless mode (default: True)
        verbose (bool): Enable verbose logging (default: False)
        parallel_workers (int): Number of parallel browser instances (default: 1)
        moodle_courses (list, optional): List of course names to scrape from Moodle. If None, scrape all courses.
        exambase_courses (list, optional): List of course names to scrape from Exambase. If None, scrape all courses.

    Returns:
        dict: Scraping statistics

    Example:
        >>> from rag_scraper import scrape
        >>> stats = scrape('u3665467@connect.hku.hk', 'password')
        >>> print(f"Downloaded {stats['moodle']['files_downloaded']} Moodle files")

        >>> # Use parallel mode with 2 workers
        >>> stats = scrape('u3665467@connect.hku.hk', 'password', parallel_workers=2)

        >>> # Scrape specific courses
        >>> moodle_list = ["COMP7103 Data mining [Section 1C, 2025]"]
        >>> exambase_list = ["COMP7103 Data mining [Section 1C, 2025]"]
        >>> stats = scrape('u3665467@connect.hku.hk', 'password',
        ...                moodle_courses=moodle_list, exambase_courses=exambase_list)
    """
    scraper = RAGScraper(
        email,
        password,
        headless=headless,
        verbose=verbose,
        parallel_workers=parallel_workers,
    )
    return scraper.scrape_all(
        moodle_courses=moodle_courses, exambase_courses=exambase_courses
    )
