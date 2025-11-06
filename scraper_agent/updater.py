"""
Knowledge Base Updater
Manages course material updates from Moodle and Exambase
"""

from datetime import datetime, timedelta
import stat
import time
from typing import List, Dict, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dao import CourseDAO, UserCourseDAO
from rag_scraper import HKUMoodleScraper, scrape
from rag_scraper.logger import get_logger


# Update thresholds
MOODLE_UPDATE_THRESHOLD = timedelta(hours=24)  # 24 hours
EXAMBASE_UPDATE_THRESHOLD = timedelta(days=30)  # 1 month


class KnowledgeBaseUpdater:
    """Manages knowledge base updates for user courses"""

    def __init__(self):
        self.course_dao = CourseDAO()
        self.user_course_dao = UserCourseDAO()
        self.logger = get_logger(log_file="rag_scraper.log", verbose=True)

    def _get_user_courses(
        self, user_id: int, user_email: str, user_password: str
    ) -> List[Dict]:
        """
        Get user's selected courses, either from database or by logging into Moodle

        Args:
            user_id: User ID
            user_email: User email for Moodle login
            user_password: User password for Moodle login

        Returns:
            List of course dictionaries with 'id' and 'name'
        """
        # Step 1: Check if user has courses in database
        user_course_records = self.user_course_dao.find_user_courses_by_userid(user_id)

        if user_course_records:
            # User has courses in database
            self.logger.info(
                f"✅ Found {len(user_course_records)} courses in database for user {user_id}",
                force=True,
            )

            courses = []
            for record in user_course_records:
                course_id = record["course_id"]
                course_name = self.course_dao.find_name_by_id(course_id)
                if course_name:
                    courses.append({"id": course_id, "name": course_name})

            return courses

        # Step 2: No courses in database, need to login to Moodle
        self.logger.info(
            f"⚠️  No courses found in database for user {user_id}", force=True
        )
        self.logger.info(f"🔐 Logging into Moodle to fetch course list...", force=True)

        # Login to Moodle and get courses
        moodle_scraper = HKUMoodleScraper(headless=True, verbose=True)
        try:
            moodle_scraper.connect_moodle(user_email, user_password)
            course_list, _ = moodle_scraper.get_courses()

            if not course_list:
                self.logger.error("❌ Failed to fetch courses from Moodle")
                return []

            self.logger.info(
                f"✅ Fetched {len(course_list)} courses from Moodle", force=True
            )

            # Step 3: Insert courses into database and create user-course mappings
            courses = []
            for course_name in course_list:
                # Check if course exists in database
                course_id = self.course_dao.find_id_by_name(course_name)

                if course_id is None:
                    # Course doesn't exist, insert it
                    try:
                        course_id = self.course_dao.insert_name(course_name)
                        self.logger.info(
                            f"  ➕ Inserted new course: {course_name[:60]}... (ID: {course_id})",
                            force=True,
                        )
                    except RuntimeError as e:
                        self.logger.error(f"  ❌ Failed to insert course: {e}")
                        continue

                # Insert user-course mapping
                try:
                    self.user_course_dao.insert_user_courses(user_id, course_id)
                    courses.append({"id": course_id, "name": course_name})
                except RuntimeError as e:
                    # Might be duplicate, that's ok
                    self.logger.warning(
                        f"  ⚠️  User-course mapping exists or error: {e}"
                    )
                    courses.append({"id": course_id, "name": course_name})

            self.logger.info(f"✅ Saved {len(courses)} courses to database", force=True)
            return courses

        finally:
            moodle_scraper.close()

    def _get_courses_need_update(
        self, courses: List[Dict]
    ) -> Tuple[List[str], List[str]]:
        """
        Determine which courses need to be updated from Moodle and Exambase

        Args:
            courses: List of course dictionaries with 'id' and 'name'

        Returns:
            Tuple of (moodle_courses, exambase_courses) - lists of course names
        """
        moodle_courses = []
        exambase_courses = []
        current_time = datetime.now()

        self.logger.info(
            f"\n📊 Checking update requirements for {len(courses)} courses...",
            force=True,
        )
        self.logger.info(f"   Current time: {current_time}", force=True)
        self.logger.info(f"   Moodle threshold: {MOODLE_UPDATE_THRESHOLD}", force=True)
        self.logger.info(
            f"   Exambase threshold: {EXAMBASE_UPDATE_THRESHOLD}", force=True
        )

        for course in courses:
            course_id = course["id"]
            course_name = course["name"]

            # Get update times from database
            moodle_time, exambase_time = self.course_dao.find_update_time_byid(
                course_id
            )

            # Check if Moodle needs update
            needs_moodle_update = False
            if moodle_time is None:
                needs_moodle_update = True
                reason = "never updated"
            else:
                time_since_update = current_time - moodle_time
                if time_since_update > MOODLE_UPDATE_THRESHOLD:
                    needs_moodle_update = True
                    reason = f"{time_since_update.total_seconds() / 3600:.1f}h ago"
                else:
                    reason = (
                        f"{time_since_update.total_seconds() / 3600:.1f}h ago (skip)"
                    )

            if needs_moodle_update:
                moodle_courses.append(course_name)
                self.logger.info(
                    f"  📚 Moodle: {course_name[:50]}... - {reason} ✅", force=True
                )
            else:
                self.logger.info(
                    f"  📚 Moodle: {course_name[:50]}... - {reason}", force=True
                )

            # Check if Exambase needs update
            needs_exambase_update = False
            if exambase_time is None:
                needs_exambase_update = True
                reason = "never updated"
            else:
                time_since_update = current_time - exambase_time
                if time_since_update > EXAMBASE_UPDATE_THRESHOLD:
                    needs_exambase_update = True
                    reason = f"{time_since_update.days}d ago"
                else:
                    reason = f"{time_since_update.days}d ago (skip)"

            if needs_exambase_update:
                exambase_courses.append(course_name)
                self.logger.info(
                    f"  📝 Exambase: {course_name[:50]}... - {reason} ✅", force=True
                )
            else:
                self.logger.info(
                    f"  📝 Exambase: {course_name[:50]}... - {reason}", force=True
                )

        self.logger.info(f"\n📋 Update Summary:", force=True)
        self.logger.info(
            f"   Moodle: {len(moodle_courses)}/{len(courses)} courses need update",
            force=True,
        )
        self.logger.info(
            f"   Exambase: {len(exambase_courses)}/{len(courses)} courses need update",
            force=True,
        )

        return moodle_courses, exambase_courses

    def _update_timestamps(
        self,
        courses: List[Dict],
        moodle_courses: List[str],
        exambase_courses: List[str],
    ):
        """
        Update timestamps in database after successful scraping

        Args:
            courses: List of all course dictionaries with 'id' and 'name'
            moodle_courses: List of course names that were updated in Moodle
            exambase_courses: List of course names that were updated in Exambase
        """
        current_time = datetime.now()

        # Create name to id mapping
        name_to_id = {course["name"]: course["id"] for course in courses}

        # Update Moodle timestamps
        for course_name in moodle_courses:
            if course_name in name_to_id:
                course_id = name_to_id[course_name]
                try:
                    self.course_dao.update_moodle_time(course_id, current_time)
                    self.logger.info(
                        f"  ✅ Updated Moodle timestamp for: {course_name[:50]}...",
                        force=True,
                    )
                except RuntimeError as e:
                    self.logger.error(f"  ❌ Failed to update Moodle timestamp: {e}")

        # Update Exambase timestamps
        for course_name in exambase_courses:
            if course_name in name_to_id:
                course_id = name_to_id[course_name]
                try:
                    self.course_dao.update_exambase_time(course_id, current_time)
                    self.logger.info(
                        f"  ✅ Updated Exambase timestamp for: {course_name[:50]}...",
                        force=True,
                    )
                except RuntimeError as e:
                    self.logger.error(f"  ❌ Failed to update Exambase timestamp: {e}")


def update_knowledge_base(
    user_id: int,
    user_email: str,
    user_password: str,
    headless: bool = True,
    verbose: bool = True,
) -> Dict:
    """
    Update knowledge base for a specific user

    This function:
    1. Checks if user has courses in database, or fetches from Moodle if not
    2. Determines which courses need updating based on timestamps and thresholds
    3. Downloads materials from Moodle (24h threshold) and Exambase (30d threshold)
    4. Updates timestamps in database after successful downloads

    Args:
        user_id: User ID in database
        user_email: User's HKU email address
        user_password: User's password for Moodle/Exambase
        headless: Run browsers in headless mode (default: True)
        verbose: Enable verbose logging (default: False)

    Returns:
        Dictionary with update statistics and success status
    """
    start = time.time()

    # Ensure log file exists before starting
    log_file = "rag_scraper.log"
    if not os.path.exists(log_file):
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("")  # Create empty file

    logger = get_logger(log_file=log_file, verbose=True)

    logger.info("=" * 80, force=True)
    logger.info("  Knowledge Base Update Manager", force=True)
    logger.info("=" * 80, force=True)
    logger.info(f"User ID: {user_id}", force=True)
    logger.info(f"Email: {user_email}", force=True)
    logger.info(f"Headless: {headless}", force=True)
    logger.info(f"Verbose: {verbose}", force=True)
    logger.info("=" * 80, force=True)

    updater = KnowledgeBaseUpdater()

    try:
        # Step 1: Get user's courses (from DB or Moodle)
        logger.info("\n[Step 1/4] Fetching user courses...", force=True)
        courses = updater._get_user_courses(user_id, user_email, user_password)

        if not courses:
            logger.error("❌ No courses found for user")
            return {
                "success": False,
                "error": "No courses found",
                "moodle": {"courses": 0, "files_downloaded": 0},
                "exambase": {"courses": 0, "exams_downloaded": 0},
            }

        logger.info(f"✅ Found {len(courses)} courses for user {user_id}", force=True)

        # Step 2: Determine which courses need updating
        logger.info("\n[Step 2/4] Checking which courses need update...", force=True)
        moodle_courses, exambase_courses = updater._get_courses_need_update(courses)

        if not moodle_courses and not exambase_courses:
            logger.info("\n✅ All courses are up to date!", force=True)
            return {
                "success": True,
                "message": "All courses up to date",
                "moodle": {
                    "courses": 0,
                    "files_downloaded": 0,
                    "skipped": len(courses),
                },
                "exambase": {
                    "courses": 0,
                    "exams_downloaded": 0,
                    "skipped": len(courses),
                },
            }

        # Step 3: Scrape materials
        logger.info("\n[Step 3/4] Downloading course materials...", force=True)
        logger.info(f"  📚 Moodle: {len(moodle_courses)} courses", force=True)
        logger.info(f"  📝 Exambase: {len(exambase_courses)} courses", force=True)

        stats = scrape(
            email=user_email,
            password=user_password,
            headless=headless,
            verbose=verbose,
            parallel_workers=1,
            moodle_courses=moodle_courses if moodle_courses else None,
            exambase_courses=exambase_courses if exambase_courses else None,
        )

        # Step 4: Update timestamps in database
        if stats.get("success"):
            logger.info("\n[Step 4/4] Updating timestamps in database...", force=True)
            updater._update_timestamps(courses, moodle_courses, exambase_courses)
            logger.info("✅ Timestamps updated", force=True)
        else:
            logger.warning(
                "\n⚠️  Scraping completed with errors, skipping timestamp update"
            )

        logger.info("\n" + "=" * 80, force=True)
        logger.info("  Update Complete", force=True)
        logger.info("=" * 80, force=True)
        logger.info(
            f"Status: {'✅ SUCCESS' if stats.get('success') else '❌ FAILED'}",
            force=True,
        )
        logger.info(
            f"Moodle: {stats['moodle'].get('files_downloaded', 0)} files from {len(moodle_courses)} courses",
            force=True,
        )
        logger.info(
            f"Exambase: {stats['exambase'].get('exams_downloaded', 0)} exams from {len(exambase_courses)} courses",
            force=True,
        )
        logger.info("=" * 80, force=True)
        end = time.time()
        stats["total_time"] = end - start
        return stats

    except Exception as e:
        logger.error(f"\n❌ Error during knowledge base update: {e}")
        import traceback

        traceback.print_exc()
        end = time.time()
        return {
            "success": False,
            "error": str(e),
            "moodle": {"courses": 0, "files_downloaded": 0},
            "exambase": {"courses": 0, "exams_downloaded": 0},
            "total_time": end - start,
        }
