#!/usr/bin/env python3
"""
test_calendar_crawler.py - Test script to verify planner_scraper/calendar.py can crawl assignments from Moodle and save to database
"""

import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from planner_scraper.calendar import MoodleCalendarCrawler
from dao import AssignmentDAO, CourseDAO
from core.config import settings
import json
from datetime import datetime

def crawl_and_save_assignments(username, password, start_date, end_date, user_id=1):
    """Crawl calendar events and save to assignment table"""
    print("Starting real crawl from Moodle...")

    # Create scraper instance
    scraper = MoodleCalendarCrawler(headless=True, verbose=False)
    try:
        # Login to Moodle
        if not scraper.connect_moodle(username, password):
            print("Failed to login to Moodle")
            return False

        # Clear existing assignments for testing
        assignment_dao = AssignmentDAO()
        try:
            with assignment_dao.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM assignment WHERE user_id = %s", (user_id,))
                conn.commit()
            print(f"Cleared existing assignments for user {user_id}")
        except Exception as e:
            print(f"Error clearing assignments: {e}")

        # Get course IDs from database
        course_ids = scraper.get_course_ids_from_db(user_id)
        if not course_ids:
            print("No courses found in database")
            return False

        print(f"Found {len(course_ids)} courses in DB: {course_ids}")

        # Use ThreadPoolExecutor for concurrent crawling
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        all_events = []
        lock = threading.Lock()  # To safely append to all_events

        def crawl_course(course_info):
            """Crawl events for a single course"""
            course_id = course_info['course_id']
            course_name = course_info['course_name']
            print(f"Starting thread for course {course_id} ({course_name})...")
            # Note: Since login is done once, we can reuse the scraper, but for simplicity, create new ones
            course_scraper = MoodleCalendarCrawler(headless=True, verbose=False)
            try:
                if not course_scraper.connect_moodle(username, password):
                    print(f"Failed to login for course {course_id} ({course_name})")
                    return []
                events = course_scraper.get_calendar_events(start_date, end_date, course_id=str(course_id))
                print(f"Course {course_id} ({course_name}): Got {len(events)} events")
                return events
            finally:
                course_scraper.close()

        # Concurrent execution
        with ThreadPoolExecutor(max_workers=min(len(course_ids), 4)) as executor:  # Limit to 4 concurrent threads
            future_to_course = {executor.submit(crawl_course, course): course for course in course_ids}
            for future in as_completed(future_to_course):
                course = future_to_course[future]
                try:
                    events = future.result()
                    with lock:
                        all_events.extend(events)
                except Exception as e:
                    print(f"Course {course['course_id']} ({course['course_name']}) generated an exception: {e}")

        print(f"Total events crawled: {len(all_events)}")

        # Initialize DAO
        assignment_dao = AssignmentDAO()

        # Convert and save assignments
        saved_count = 0
        for event in all_events:
            if event.get('event_type') == 'due' and event.get('component') in ['mod_assign', 'mod_turnitintooltwo']:
                assignment = convert_event_to_assignment(event, user_id)
                if assignment:
                    # Check if already exists (though we cleared, just in case)
                    existing = assignment_dao.get_assignments_by_date_range(user_id, assignment['due_date'], assignment['due_date'])
                    exists = any(a['title'] == assignment['title'] for a in existing)
                    if not exists:
                        success = assignment_dao.insert_assignment(assignment)
                        if success:
                            print(f"Inserted assignment: ID {event.get('event_id')} - '{assignment['title']}' (Course: {event.get('course')})")
                            saved_count += 1
                        else:
                            print(f"Failed to insert: ID {event.get('event_id')} - '{assignment['title']}'")
                    else:
                        print(f"Assignment already exists: ID {event.get('event_id')} - '{assignment['title']}'")

        print(f"Inserted {saved_count} new assignments.")

        return saved_count > 0
    finally:
        scraper.close()

def convert_event_to_assignment(event, user_id=1):
    """Convert calendar event to assignment dict"""
    try:
        # Parse date
        due_date = datetime.strptime(event["date"], "%Y-%m-%d") if event.get("date") else None

        # Determine assignment type based on title/description
        title = event.get("title", "")
        description = event.get("description", "")
        assignment_type = "homework"  # default

        if "exam" in title.lower() or "exam" in description.lower():
            assignment_type = "exam"
        elif "quiz" in title.lower() or "quiz" in description.lower():
            assignment_type = "quiz"
        elif "project" in title.lower() or "project" in description.lower():
            assignment_type = "project"

        # Extract course_id from event
        course_id = int(event.get("course_id", 0)) if event.get("course_id") else None

        assignment = {
            "title": title,
            "description": description,
            "course_id": course_id,
            "user_id": user_id,
            "due_date": due_date,
            "status": "pending",  # Default status
            "assignment_type": assignment_type,
            "max_score": None,
            "instructions": description,
            "attachment_path": event.get("submit_link", "")
        }
        return assignment
    except Exception as e:
        print(f"Error converting event {event}: {e}")
        return None

if __name__ == "__main__":
    print("Starting test_calendar_crawler.py")
    try:
        parser = argparse.ArgumentParser(description="Test calendar crawler")
        parser.add_argument("--username", default="u3665686@connect.hku.hk", help="Moodle username")
        parser.add_argument("--password", default="yupei626513", help="Moodle password")
        parser.add_argument("--start-date", default="2025-11-16", help="Start date (YYYY-MM-DD)")
        parser.add_argument("--end-date", default="2025-11-22", help="End date (YYYY-MM-DD)")
        parser.add_argument("--user-id", type=int, default=1, help="User ID")

        args = parser.parse_args()

        success = crawl_and_save_assignments(args.username, args.password, args.start_date, args.end_date, args.user_id)

        if success:
            print("✅ Test passed: Assignments crawled and saved successfully.")
        else:
            print("❌ Test failed: Unable to crawl and save assignments.")
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
