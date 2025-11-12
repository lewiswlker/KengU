#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test parallel scraping - Moodle and Exambase run simultaneously
"""

from rag_scraper import scrape
import time

# Test credentials
EMAIL = "u3665467@connect.hku.hk"
PASSWORD = "Renliubo1891412"

# Test with small course lists
moodle_courses = [
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

exambase_courses = [
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

print("=" * 70)
print("Testing TRUE PARALLEL Scraping (Moodle + Exambase simultaneously)")
print("=" * 70)
print(f"\nMoodle courses: {len(moodle_courses)}")
for course in moodle_courses:
    print(f"  - {course}")

print(f"\nExambase courses: {len(exambase_courses)}")
for course in exambase_courses:
    print(f"  - {course}")

print("\n" + "=" * 70)
print("Starting parallel scraper...")
print("Both Moodle and Exambase will run at the same time!")
print("=" * 70)

start_time = time.time()

# Initialize scraper

stats = scrape(
    email=EMAIL,
    password=PASSWORD,
    headless=True,
    verbose=True,
    parallel_workers=1,
    moodle_courses=moodle_courses,
    exambase_courses=exambase_courses,
)

elapsed = time.time() - start_time

print("\n" + "=" * 70)
print("RESULTS - Parallel Scraping")
print("=" * 70)
print(f"\n📚 Moodle:")
print(f"   Courses: {stats['moodle'].get('courses', 0)}")
print(f"   Files: {stats['moodle'].get('files_downloaded', 0)}")
print(f"   Time: {stats['moodle'].get('total_time', 0):.2f}s")
print(f"   Success: {'✅' if stats['moodle'].get('success') else '❌'}")

print(f"\n📝 Exambase:")
print(f"   Courses: {stats['exambase'].get('courses', 0)}")
print(f"   With exams: {stats['exambase'].get('courses_with_exams', 0)}")
print(f"   Exams: {stats['exambase'].get('exams_downloaded', 0)}")
print(f"   Time: {stats['exambase'].get('total_time', 0):.2f}s")
print(f"   Success: {'✅' if stats['exambase'].get('success') else '❌'}")

print(f"\n⏱️  Total wall time: {elapsed:.2f}s")
print(
    f"   Individual sum: {stats['moodle'].get('total_time', 0) + stats['exambase'].get('total_time', 0):.2f}s"
)
print(
    f"   Time saved: {(stats['moodle'].get('total_time', 0) + stats['exambase'].get('total_time', 0) - elapsed):.2f}s"
)
print(f"\n🎯 Overall: {'✅ SUCCESS' if stats.get('success') else '❌ FAILED'}")
print("=" * 70)
