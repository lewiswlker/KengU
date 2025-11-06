"""
Test script for DAO operations
Tests all course and user_course operations as specified
"""

from datetime import datetime
from dao import CourseDAO, UserCourseDAO


def print_section(title):
    """Print section title"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def main():
    # Initialize DAOs
    course_dao = CourseDAO()
    user_course_dao = UserCourseDAO()
    user_id = 1

    # Test data
    courses = [
        "COMP7104_DASC7104 Advanced database systems [Section 1A] [2025]",
        "MSC-WKSHL1_S1 Writing Workshop for HKU CDS MSc Students (Sem 1 - Group F) [2025]",
        "DASC7606 Deep learning [Section 1B, 2025]",
        "TPG-WKSHL3 Academic Presentations - Workshop for HKU CDS TPg students [2025]",
        "COMP7104 Advanced database systems [Section 1A, 2025]",
        "MSC-WKSHT1 Python Workshop for HKU CDS MSc Students [2025]",
        "MSCCS Master of Science in Computer Science - MSc(CompSc) Homepage [2025]",
        "COMP7503 Multimedia technologies [Section 1B, 2025]",
        "COMP7103 Data mining [Section 1C, 2025]",
        "COMP7607 Natural language processing [Section 1B, 2025]",
    ]

    # Step 1: Insert courses
    print_section("Step 1: Batch Insert Courses (insert_names)")
    try:
        course_ids = course_dao.insert_names(courses)
        print(f"✅ Successfully inserted {len(course_ids)} courses")
        print(f"Generated Course ID List: {course_ids}")
        for i, (name, cid) in enumerate(zip(courses, course_ids), 1):
            print(f"  [{i}] ID={cid}: {name[:60]}...")
    except RuntimeError as e:
        print(f"❌ Insertion failed: {e}")
        return

    # Step 2: Find course IDs by names
    print_section("Step 2: Query Course ID by Course Name (find_id_by_name)")
    found_ids = []
    for i, course_name in enumerate(courses, 1):
        try:
            course_id = course_dao.find_id_by_name(course_name)
            found_ids.append(course_id)
            print(f"  [{i}] Course Name: {course_name[:50]}...")
            print(f"       Course ID: {course_id}")
        except RuntimeError as e:
            print(f"  [{i}] ❌ Query failed: {e}")

    if not found_ids or None in found_ids:
        print("❌ Some course IDs failed to query, cannot continue subsequent tests")
        return

    print(f"\n✅ Queried Course ID List: {found_ids}")

    # Step 3: Insert user-course mappings
    print_section("Step 3: Insert User-Course Relationships (insert_user_courses)")
    print(f"User ID: {user_id}")
    success_count = 0
    for i, course_id in enumerate(found_ids, 1):
        try:
            record_id = user_course_dao.insert_user_courses(user_id, course_id)
            print(f"  [{i}] ✅ User {user_id} <-> Course {course_id}: Record ID={record_id}")
            success_count += 1
        except RuntimeError as e:
            print(f"  [{i}] ❌ Insertion failed (User {user_id} <-> Course {course_id}): {e}")

    print(f"\n✅ Successfully inserted {success_count}/{len(found_ids)} user-course relationships")

    # Step 4: Query update times by course ID (before update)
    print_section("Step 4: Query Update Times by Course ID (find_update_time_byid) - Before Update")
    for i, course_id in enumerate(found_ids, 1):
        try:
            moodle_time, exambase_time = course_dao.find_update_time_byid(course_id)
            print(f"  [{i}] Course ID {course_id}:")
            print(f"       Moodle Update Time: {moodle_time}")
            print(f"       Exambase Update Time: {exambase_time}")
        except RuntimeError as e:
            print(f"  [{i}] ❌ Query failed (Course ID {course_id}): {e}")

    # Step 5: Query update times by course name (before update)
    print_section("Step 5: Query Update Times by Course Name (find_update_time_byname) - Before Update")
    for i, course_name in enumerate(courses, 1):
        try:
            moodle_time, exambase_time = course_dao.find_update_time_byname(course_name)
            print(f"  [{i}] Course Name: {course_name[:50]}...")
            print(f"       Moodle Update Time: {moodle_time}")
            print(f"       Exambase Update Time: {exambase_time}")
        except RuntimeError as e:
            print(f"  [{i}] ❌ Query failed: {e}")

    # Step 6: Update all courses' timestamps to now
    print_section("Step 6: Update All Courses' Timestamps to Current Time")
    current_time = datetime.now()
    print(f"Current Time: {current_time}")

    moodle_success = 0
    exambase_success = 0

    for i, course_id in enumerate(found_ids, 1):
        try:
            # Update Moodle time
            if course_dao.update_moodle_time(course_id, current_time):
                moodle_success += 1
                print(f"  [{i}] ✅ Course ID {course_id}: Moodle time updated successfully")
            else:
                print(f"  [{i}] ⚠️ Course ID {course_id}: Moodle time update failed (0 rows affected)")

            # Update Exambase time
            if course_dao.update_exambase_time(course_id, current_time):
                exambase_success += 1
                print(f"       ✅ Course ID {course_id}: Exambase time updated successfully")
            else:
                print(f"       ⚠️ Course ID {course_id}: Exambase time update failed (0 rows affected)")

        except RuntimeError as e:
            print(f"  [{i}] ❌ Update failed (Course ID {course_id}): {e}")

    print(f"\n✅ Moodle Time Updates: {moodle_success}/{len(found_ids)} successful")
    print(f"✅ Exambase Time Updates: {exambase_success}/{len(found_ids)} successful")

    # Step 7: Query update times by course ID (after update)
    print_section("Step 7: Query Update Times by Course ID (find_update_time_byid) - After Update")
    for i, course_id in enumerate(found_ids, 1):
        try:
            moodle_time, exambase_time = course_dao.find_update_time_byid(course_id)
            print(f"  [{i}] Course ID {course_id}:")
            print(f"       Moodle Update Time: {moodle_time}")
            print(f"       Exambase Update Time: {exambase_time}")

            # Verify times match current_time
            if moodle_time and exambase_time:
                # Allow 1 second tolerance
                moodle_diff = abs((moodle_time - current_time).total_seconds())
                exambase_diff = abs((exambase_time - current_time).total_seconds())

                if moodle_diff <= 1 and exambase_diff <= 1:
                    print(f"       ✅ Timestamp verification passed")
                else:
                    print(
                        f"       ⚠️ Timestamp difference: Moodle={moodle_diff:.2f}s, Exambase={exambase_diff:.2f}s"
                    )
        except RuntimeError as e:
            print(f"  [{i}] ❌ Query failed (Course ID {course_id}): {e}")

    # Summary
    print_section("Test Summary")
    print(f"✅ All test steps completed")
    print(f"   - Inserted Courses: {len(course_ids)}")
    print(f"   - Queried Course IDs: {len(found_ids)}")
    print(f"   - Inserted User-Course Relationships: {success_count}")
    print(f"   - Updated Moodle Times: {moodle_success}")
    print(f"   - Updated Exambase Times: {exambase_success}")
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ An error occurred during testing: {e}")
        import traceback

        traceback.print_exc()