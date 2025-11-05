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
    print_section("Step 1: 批量插入课程 (insert_names)")
    try:
        course_ids = course_dao.insert_names(courses)
        print(f"✅ 成功插入 {len(course_ids)} 门课程")
        print(f"生成的课程ID列表: {course_ids}")
        for i, (name, cid) in enumerate(zip(courses, course_ids), 1):
            print(f"  [{i}] ID={cid}: {name[:60]}...")
    except RuntimeError as e:
        print(f"❌ 插入失败: {e}")
        return

    # Step 2: Find course IDs by names
    print_section("Step 2: 根据课程名查询课程ID (find_id_by_name)")
    found_ids = []
    for i, course_name in enumerate(courses, 1):
        try:
            course_id = course_dao.find_id_by_name(course_name)
            found_ids.append(course_id)
            print(f"  [{i}] 课程名: {course_name[:50]}...")
            print(f"       课程ID: {course_id}")
        except RuntimeError as e:
            print(f"  [{i}] ❌ 查询失败: {e}")

    if not found_ids or None in found_ids:
        print("❌ 部分课程ID查询失败，无法继续后续测试")
        return

    print(f"\n✅ 查询到的课程ID列表: {found_ids}")

    # Step 3: Insert user-course mappings
    print_section("Step 3: 插入用户-课程关系 (insert_user_courses)")
    print(f"用户ID: {user_id}")
    success_count = 0
    for i, course_id in enumerate(found_ids, 1):
        try:
            record_id = user_course_dao.insert_user_courses(user_id, course_id)
            print(f"  [{i}] ✅ 用户 {user_id} <-> 课程 {course_id}: 记录ID={record_id}")
            success_count += 1
        except RuntimeError as e:
            print(f"  [{i}] ❌ 插入失败 (用户 {user_id} <-> 课程 {course_id}): {e}")

    print(f"\n✅ 成功插入 {success_count}/{len(found_ids)} 条用户-课程关系")

    # Step 4: Query update times by course ID (before update)
    print_section("Step 4: 根据课程ID查询更新时间 (find_update_time_byid) - 更新前")
    for i, course_id in enumerate(found_ids, 1):
        try:
            moodle_time, exambase_time = course_dao.find_update_time_byid(course_id)
            print(f"  [{i}] 课程ID {course_id}:")
            print(f"       Moodle更新时间: {moodle_time}")
            print(f"       Exambase更新时间: {exambase_time}")
        except RuntimeError as e:
            print(f"  [{i}] ❌ 查询失败 (课程ID {course_id}): {e}")

    # Step 5: Query update times by course name (before update)
    print_section("Step 5: 根据课程名查询更新时间 (find_update_time_byname) - 更新前")
    for i, course_name in enumerate(courses, 1):
        try:
            moodle_time, exambase_time = course_dao.find_update_time_byname(course_name)
            print(f"  [{i}] 课程名: {course_name[:50]}...")
            print(f"       Moodle更新时间: {moodle_time}")
            print(f"       Exambase更新时间: {exambase_time}")
        except RuntimeError as e:
            print(f"  [{i}] ❌ 查询失败: {e}")

    # Step 6: Update all courses' timestamps to now
    print_section("Step 6: 更新所有课程的时间戳为当前时间")
    current_time = datetime.now()
    print(f"当前时间: {current_time}")

    moodle_success = 0
    exambase_success = 0

    for i, course_id in enumerate(found_ids, 1):
        try:
            # Update Moodle time
            if course_dao.update_moodle_time(course_id, current_time):
                moodle_success += 1
                print(f"  [{i}] ✅ 课程ID {course_id}: Moodle时间已更新")
            else:
                print(f"  [{i}] ⚠️ 课程ID {course_id}: Moodle时间更新失败(0行受影响)")

            # Update Exambase time
            if course_dao.update_exambase_time(course_id, current_time):
                exambase_success += 1
                print(f"       ✅ 课程ID {course_id}: Exambase时间已更新")
            else:
                print(f"       ⚠️ 课程ID {course_id}: Exambase时间更新失败(0行受影响)")

        except RuntimeError as e:
            print(f"  [{i}] ❌ 更新失败 (课程ID {course_id}): {e}")

    print(f"\n✅ Moodle时间: {moodle_success}/{len(found_ids)} 成功")
    print(f"✅ Exambase时间: {exambase_success}/{len(found_ids)} 成功")

    # Step 7: Query update times by course ID (after update)
    print_section("Step 7: 根据课程ID查询更新时间 (find_update_time_byid) - 更新后")
    for i, course_id in enumerate(found_ids, 1):
        try:
            moodle_time, exambase_time = course_dao.find_update_time_byid(course_id)
            print(f"  [{i}] 课程ID {course_id}:")
            print(f"       Moodle更新时间: {moodle_time}")
            print(f"       Exambase更新时间: {exambase_time}")

            # Verify times match current_time
            if moodle_time and exambase_time:
                # Allow 1 second tolerance
                moodle_diff = abs((moodle_time - current_time).total_seconds())
                exambase_diff = abs((exambase_time - current_time).total_seconds())

                if moodle_diff <= 1 and exambase_diff <= 1:
                    print(f"       ✅ 时间戳验证通过")
                else:
                    print(
                        f"       ⚠️ 时间戳差异: Moodle={moodle_diff:.2f}s, Exambase={exambase_diff:.2f}s"
                    )
        except RuntimeError as e:
            print(f"  [{i}] ❌ 查询失败 (课程ID {course_id}): {e}")

    # Summary
    print_section("测试总结")
    print(f"✅ 所有测试步骤已完成")
    print(f"   - 插入课程数: {len(course_ids)}")
    print(f"   - 查询课程ID数: {len(found_ids)}")
    print(f"   - 插入用户-课程关系数: {success_count}")
    print(f"   - 更新Moodle时间数: {moodle_success}")
    print(f"   - 更新Exambase时间数: {exambase_success}")
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()
