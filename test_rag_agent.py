#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for RAG Agent
Demonstrates course selection and RAG-based question answering
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.rag_agent import answer_with_rag, RetrievalResult
from agents.rag_agent.rag_agent import RAGAgent


def test_course_selection():
    """Test the LLM-based course selection"""
    print("=" * 80)
    print("Test 1: Course Selection with LLM")
    print("=" * 80)

    agent = RAGAgent()

    # Example query and courses
    query = "Describe the latest contents in my NLP courses."
    courses_list = [
        "COMP7104_DASC7104 Advanced database systems [Section 1A] [2025]",
        "COMP7607 Natural language processing [Section 1B, 2025]",
        "COMP7103 Data mining [Section 1C, 2025]",
        "MSCCS Master of Science in Computer Science - MSc(CompSc) Homepage [2025]",
        "MSC-WKSHT1 Python Workshop for HKU CDS MSc Students [2025]",
        "COMP7104 Advanced database systems [Section 1A, 2025]",
        "TPG-WKSHL3 Academic Presentations - Workshop for HKU CDS TPg students [2025]",
        "DASC7606 Deep learning [Section 1B, 2025]",
        "MSC-WKSHL1_S1 Writing Workshop for HKU CDS MSc Students (Sem 1 - Group F) [2025]",
        "COMP7503 Multimedia technologies [Section 1B, 2025]",
    ]

    print(f"\nQuery: {query}")
    print(f"\nAvailable courses: {len(courses_list)}")
    for i, course in enumerate(courses_list, 1):
        print(f"  {i}. {course}")

    print("\nCalling LLM to select relevant courses...")
    selected_courses = agent.select_relevant_courses(query, courses_list)

    print(f"\n✅ Selected courses: {len(selected_courses)}")
    for course in selected_courses:
        print(f"{course}")

    # Expected: ["COMP7607 Natural language processing [Section 1B, 2025]"]
    expected = "COMP7607 Natural language processing"
    if selected_courses and expected in selected_courses[0]:
        print("\n✅ Test PASSED: Correctly selected NLP course")
    else:
        print("\n⚠️  Test FAILED: Expected NLP course, got:", selected_courses)


def test_multiple_queries():
    """Test course selection with multiple different queries"""
    print("\n\n" + "=" * 80)
    print("Test 2: Multiple Query Types")
    print("=" * 80)

    agent = RAGAgent()

    courses_list = [
        "COMP7104_DASC7104 Advanced database systems [Section 1A] [2025]",
        "COMP7607 Natural language processing [Section 1B, 2025]",
        "COMP7103 Data mining [Section 1C, 2025]",
        "DASC7606 Deep learning [Section 1B, 2025]",
        "COMP7503 Multimedia technologies [Section 1B, 2025]",
    ]

    test_cases = [
        ("What are the main topics in database course?", "Advanced database systems"),
        ("Tell me about deep learning assignments", "Deep learning"),
        ("How to do data mining projects?", "Data mining"),
        ("Explain the multimedia concepts", "Multimedia technologies"),
    ]

    for query, expected_keyword in test_cases:
        print(f"\nQuery: {query}")
        selected = agent.select_relevant_courses(query, courses_list)
        print(f"Selected: {selected}")

def test_answer_with_rag():
    """Test the full RAG answer pipeline"""
    print("\n\n" + "=" * 80)
    print("Test 3: Full RAG Answer Pipeline")
    print("=" * 80)

    # Test with a user_id (you need to use a valid user_id from your database)
    user_id = 1  # Replace with actual user_id
    query = "What are the recent topics covered in NLP course?"

    print(f"\nUser ID: {user_id}")
    print(f"Query: {query}")
    print("\nCalling answer_with_rag()...")

    result = answer_with_rag(query, user_id)

    print(f"\n{'='*60}")
    print("Results:")
    print(f"{'='*60}")

    if result["error"]:
        print(f"\n❌ Error: {result['error']}")
    else:
        print(f"\n✅ Answer:")
        print(result["answer"])

        print(f"\n📚 Retrieval Results: {len(result['retrieval_results'])}")
        for i, res in enumerate(result["retrieval_results"], 1):
            print(f"\n  Result {i}:")
            print(f"    Text: {res.text[:100]}...")
            print(f"    Source: {res.source_url}")
            print(f"    Score: {res.relevance_score}")


def test_mock_answer():
    """Test with mock courses (no database required)"""
    print("\n\n" + "=" * 80)
    print("Test 4: Mock Answer (No Database)")
    print("=" * 80)

    agent = RAGAgent()

    query = "Explain transformer architecture in NLP"
    courses = ["COMP7607 Natural language processing [Section 1B, 2025]"]

    print(f"\nQuery: {query}")
    print(f"Courses: {courses}")

    # Directly call the mock answer function
    from agents.rag_agent.rag_agent import _mock_rag_answer

    result = _mock_rag_answer(query, courses)

    print(f"\n✅ Mock Answer:")
    print(result["answer"])

    print(f"\n📚 Mock Retrieval Results: {len(result['retrieval_results'])}")
    for i, res in enumerate(result["retrieval_results"], 1):
        print(f"\n  Result {i}:")
        print(f"    Text: {res.text}")
        print(f"    Source: {res.source_url}")
        print(f"    Score: {res.relevance_score}")


if __name__ == "__main__":
    print("\n🚀 RAG Agent Test Suite\n")

    # Run tests
    try:
        # Test 1: Course selection (requires API key)
        print("Note: Test 1 requires valid ZhipuAI API key")
        print("If you see import errors, run: pip install zai-sdk\n")

        test_course_selection()
        test_multiple_queries()

    except Exception as e:
        print(f"\n⚠️  Course selection tests skipped due to: {e}")
        print("Make sure to install: pip install zai-sdk")

    # Test 3: Full pipeline (requires database)
    try:
        test_answer_with_rag()
    except Exception as e:
        print(f"\n⚠️  Full pipeline test skipped due to: {e}")
        print("This test requires a valid user_id in the database")

    # Test 4: Mock answer (always works)
    test_mock_answer()

    print("\n\n" + "=" * 80)
    print("✅ Test Suite Completed")
    print("=" * 80)
