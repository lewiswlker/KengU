#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Agent - Course-specific Question Answering with RAG
Provides intelligent course selection and RAG-based answer generation
"""

import sys
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from dao import CourseDAO, UserCourseDAO
from zai import ZhipuAiClient
from rag.service import RagService


@dataclass
class RetrievalResult:
    """Data structure for single RAG retrieval result"""

    text: str
    source_url: str
    relevance_score: float


class RAGAgent:
    """RAG Agent for course-specific question answering"""

    def __init__(self):
        """Initialize RAG Agent with ZhipuAI client"""
        self.api_key = "c4fc86e26544485a8cec24e621b10dd4.UXMEmCHQWq8M9IlZ"
        self.model = "glm-4.5-air"
        self.client = ZhipuAiClient(api_key=self.api_key)
        self.course_dao = CourseDAO()
        self.user_course_dao = UserCourseDAO()

    def select_relevant_courses(self, query: str, courses_list: List[str]) -> List[str]:
        """
        Use LLM to select relevant courses based on user query

        This method uses ZhipuAI's GLM-4.5-Air model with deep thinking mode
        to intelligently select which course(s) the user's query is related to.

        Args:
            query: User's question
            courses_list: List of course names the user is enrolled in

        Returns:
            List of selected course names that are relevant to the query

        Example:
            query = "Describe the latest contents in my NLP courses."
            courses_list = [
                "COMP7104_DASC7104 Advanced database systems [Section 1A] [2025]",
                "COMP7607 Natural language processing [Section 1B, 2025]",
                "COMP7103 Data mining [Section 1C, 2025]",
                ...
            ]
            Returns: ["COMP7607 Natural language processing [Section 1B, 2025]"]
        """
        if not courses_list:
            return []

        # Construct prompt for course selection
        courses_text = "\n".join(
            [f"{i+1}. {course}" for i, course in enumerate(courses_list)]
        )

        prompt = f"""You are an intelligent course selector. Given a user's query and their course list, identify which course(s) the query is related to.

**Important Rules:**
1. Unless the user explicitly mentions multiple courses or uses plural forms, assume the query relates to ONLY ONE course.
2. Match the query keywords with course names carefully.
3. Return ONLY the exact course code and name(s) from the list, nothing else.
4. If no course matches, return "NONE".
5. Return one course per line.

Here is a example:
query="Describe the latest contents that in my NLP courses."
courses_list=["COMP7104_DASC7104 Advanced database systems [Section 1A] [2025]",
"COMP7607 Natural language processing [Section 1B, 2025]",
"COMP7103 Data mining [Section 1C, 2025]",
"MSC-WKSHT1 Python Workshop for HKU CDS MSc Students [2025]"]
Then, you should answer:
"1. COMP7607 Natural language processing [Section 1B, 2025]"


**User's Query:**
{query}

**User's Course List:**
{courses_text}

**Your Task:**
Analyze the query and return the relevant course name(s) from the list above. Return only the course name(s), one per line.
"""
        MAX_RETRY_TIMES = 3
        retry_times = 0
        while retry_times < MAX_RETRY_TIMES:
            try:
                # Call ZhipuAI API with thinking mode enabled
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    thinking={
                        "type": "enabled",
                    },
                    temperature=0.3,  # Lower temperature for more focused selection
                )

                # Parse response
                answer = response.choices[0].message.content.strip()

                # Extract course names from response
                selected_courses = []
                for line in answer.split("\n"):
                    line = line.strip()
                    if line and line != "NONE":
                        # Remove numbering if present (e.g., "1. COMP7607..." -> "COMP7607...")
                        if line[0].isdigit() and ". " in line:
                            line = line.split(".", 1)[1].strip()

                        # Verify the course is in the original list
                        if line in courses_list:
                            selected_courses.append(line)
                if selected_courses is None or selected_courses == []:
                    retry_times += 1
                    print(f"Selected courses: {selected_courses}. Retrying course selection... Attempt {retry_times}")
                    continue
                else:
                    return selected_courses

            except Exception as e:
                retry_times += 1
                print(f"Error in course selection: {e}")
                # Fallback: simple keyword matching
        
        return self._fallback_course_selection(query, courses_list)

    def _fallback_course_selection(
        self, query: str, courses_list: List[str]
    ) -> List[str]:
        """
        Fallback course selection using simple keyword matching

        Args:
            query: User's question
            courses_list: List of course names

        Returns:
            List of matched course names
        """
        query_lower = query.lower()
        matched_courses = []

        # Extract potential course codes and keywords from query
        keywords = [
            "nlp",
            "natural language processing",
            "database",
            "db",
            "data mining",
            "mining",
            "deep learning",
            "dl",
            "multimedia",
            "machine learning",
            "ml",
            "computer science",
            "cs",
        ]

        for course in courses_list:
            course_lower = course.lower()

            # Check for exact course code match (e.g., COMP7607)
            course_code = course.split()[0] if " " in course else course.split("_")[0]
            if course_code.lower() in query_lower:
                matched_courses.append(course)
                continue

            # Check for keyword matches
            for keyword in keywords:
                if keyword in query_lower and keyword in course_lower:
                    matched_courses.append(course)
                    break

        # Return first match if found, otherwise empty list
        return matched_courses[:1] if matched_courses else []

    def get_user_courses(self, user_id: int) -> List[str]:
        """
        Retrieve user's enrolled courses from database

        Args:
            user_id: User ID in database

        Returns:
            List of course names (full course titles)
        """
        try:
            # Get user's course relationships from user_course table
            # Returns: List[Dict[str, int]] with keys: 'id', 'user_id', 'course_id'
            user_courses = self.user_course_dao.find_user_courses_by_userid(user_id)

            if not user_courses:
                return []

            # Extract course IDs and fetch full course information
            course_names = []
            for uc in user_courses:
                # Access dict keys, not object attributes
                course_id = uc["course_id"]
                # find_name_by_id returns Optional[str], not an object
                course_name = self.course_dao.find_name_by_id(course_id)
                if course_name:
                    course_names.append(course_name)

            return course_names

        except Exception as e:
            print(f"Error fetching user courses: {e}")
            import traceback

            traceback.print_exc()
            return []


def answer_with_rag(
    query: str, user_id: int
) -> Dict[str, Optional[List[RetrievalResult] | str]]:
    """
    Generate answer combined with RAG retrieval results for user's query

    This function:
    1. Retrieves user's enrolled courses from database via user_id
    2. Uses LLM to select relevant courses based on the query
    3. Searches relevant text chunks from RAG knowledge base based on query and selected courses
    4. Associates each retrieved text with its source information (URL, course, platform)
    5. Generates coherent answer by integrating query intent and retrieval results
    6. Returns final answer, retrieval details and source links

    Args:
        query: User's question or query content
        user_id: User ID in database (used to filter course-specific resources)

    Returns:
        Dictionary containing three core parts:
            - "answer": Generated response combining query and RAG results (str, None if failed)
            - "retrieval_results": List of RetrievalResult objects (include text and source info, empty list if no matches)
            - "error": Error message if execution fails (str, None if successful)
    """
    try:
        # Initialize RAG Agent
        agent = RAGAgent()

        # Step 1: Get user's enrolled courses from database
        user_courses = agent.get_user_courses(user_id)

        if not user_courses:
            return {
                "answer": None,
                "retrieval_results": [],
                "error": f"No courses found for user_id {user_id}",
            }

        # Step 2: Use LLM to select relevant courses based on query
        selected_courses = agent.select_relevant_courses(query, user_courses)

        if not selected_courses:
            return {
                "answer": "I couldn't identify which course your question is related to. Could you please specify the course name?",
                "retrieval_results": [],
                "error": None,
            }

        print(f"Selected courses for query '{query}': {selected_courses}")
        # Step 3: Retrieve and generate answer via RAG service
        rag = RagService()
        retrieved = rag.retrieve(query, selected_courses, top_k=6)

        # Map to RetrievalResult dataclass
        results: List[RetrievalResult] = []
        for r in retrieved:
            results.append(
                RetrievalResult(
                    text=r.get("text", ""),
                    source_url=r.get("url", ""),
                    relevance_score=r.get("relevance", 0.0),
                )
            )

        # Step 5: Return results with answer
        return {
            "retrieval_results": results,
            "error": None
        }

    except Exception as e:
        import traceback

        error_msg = f"Error in answer_with_rag: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)

        return {"retrieval_results": [], "error": error_msg}


def _mock_rag_answer(query: str, selected_courses: List[str]) -> Dict[str, any]:
    """
    Mock RAG answer function (to be replaced by actual implementation)

    This is a placeholder that will be replaced when integrating with
    the actual RAG retrieval system developed by other team members.

    Args:
        query: User's question
        selected_courses: List of selected course names

    Returns:
        Dictionary with answer and retrieval_results
    """
    # Mock retrieval results
    mock_results = [
        RetrievalResult(
            text=f"This is a mock retrieval result for the query: '{query}' in course: {selected_courses[0]}. "
            f"The actual RAG system will retrieve relevant course materials here.",
            source_url=f"https://moodle.hku.hk/course/view.php?id=12345",
            relevance_score=0.95,
        ),
        RetrievalResult(
            text=f"Another mock result showing related content from {selected_courses[0]}. "
            f"This will be replaced with real course material snippets.",
            source_url=f"https://moodle.hku.hk/mod/resource/view.php?id=67890",
            relevance_score=0.87,
        ),
    ]

    mock_answer = (
        f"[MOCK ANSWER] Based on the course '{selected_courses[0]}', here's what I found:\n\n"
        f"Your query '{query}' relates to the following topics in this course. "
        f"The actual implementation will provide detailed answers based on RAG retrieval.\n\n"
        f"Selected courses: {', '.join(selected_courses)}\n"
        f"Retrieved {len(mock_results)} relevant materials."
    )

    return {"answer": mock_answer, "retrieval_results": mock_results}
