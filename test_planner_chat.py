#!/usr/bin/env python3
"""
test_planner_chat.py - Test script for PlannerAgent chat functionality with real DB connection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
settings.DB_PASS = "123456"  # Set DB password as per user

from agents.planner_agent.planner_agent import PlannerAgent, LLMConfig
from models import ChatInput

def test_chat_scenarios():
    # Initialize agent with local LLM config
    llm_config = LLMConfig.local_ollama(model="deepseek-r1:1.5b")
    agent = PlannerAgent(llm_config=llm_config)

    # Reset all assignments to pending for consistent testing
    print("Resetting all assignments to pending status...")
    reset_count = agent.assignment_dao.reset_all_to_pending()
    print(f"Reset {reset_count} assignments to pending.")

    print("Starting PlannerAgent chat tests with real DB connection...")

    # Test 1: Mark assignment complete
    print("\n--- Test 1: Mark Assignment Complete ---")
    chat_input = ChatInput(user_id=1, message="我完成了作业 Assignment 1: Data Mining Basics")
    result = agent.chat(chat_input)
    print("User:", chat_input.message)
    print("Agent Reply:", result.reply)

    # Follow-up: User says yes
    chat_input = ChatInput(user_id=1, message="xxx课程")
    result = agent.chat(chat_input)
    print("User:", chat_input.message)
    print("Agent Reply:", result.reply)

    # Check DB after Test 1
    print("\n--- DB Check after Test 1 ---")
    import subprocess
    result = subprocess.run(['mysql', '-u', 'root', '-p123456', '-e', 'SELECT id, title, status FROM kengu.assignment WHERE title LIKE "%Assignment 1%";'], capture_output=True, text=True)
    print("Assignment status:")
    print(result.stdout)

    # Test 2: Log study session
    print("\n--- Test 2: Log Study Session ---")
    chat_input = ChatInput(user_id=1, message="我复习了作业 Project: Database Design 花了2小时")
    result = agent.chat(chat_input)
    print("User:", chat_input.message)
    print("Agent Reply:", result.reply)

    # Check DB after Test 2
    print("\n--- DB Check after Test 2 ---")
    result = subprocess.run(['mysql', '-u', 'root', '-p123456', '-e', 'SELECT session_id, assignment_id, duration_minutes FROM kengu.study_sessions;'], capture_output=True, text=True)
    print("Study sessions:")
    print(result.stdout)

    # Test 3: List pending assignments
    print("\n--- Test 3: List Pending Assignments ---")
    chat_input = ChatInput(user_id=1, message="告诉我还需要完成的作业")
    result = agent.chat(chat_input)
    print("User:", chat_input.message)
    print("Agent Reply:", result.reply)

    # Test 4: Multi-turn conversation for new task
    print("\n--- Test 4: Multi-turn Conversation for New Task ---")
    chat_input = ChatInput(user_id=1, message="后天需要提交一份poster报告")
    result = agent.chat(chat_input)
    print("User:", chat_input.message)
    print("Agent Reply:", result.reply)

    # Simulate user providing more info
    chat_input = ChatInput(user_id=1, message="这是COMP7103 Data Mining的poster报告")
    result = agent.chat(chat_input)
    print("User:", chat_input.message)
    print("Agent Reply:", result.reply)

    # Test 5: Generate monthly plan
    print("\n--- Test 5: Generate Monthly Plan ---")
    chat_input = ChatInput(user_id=1, message="11月份的时间安排计划")
    result = agent.chat(chat_input)
    print("User:", chat_input.message)
    print("Agent Reply:", result.reply[:500] + "..." if len(result.reply) > 500 else result.reply)

    print("\n--- Tests completed ---")

if __name__ == "__main__":
    test_chat_scenarios()
