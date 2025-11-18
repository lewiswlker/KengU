#!/usr/bin/env python3
"""
test_planner_chat.py - Test script for PlannerAgent chat functionality with real DB connection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
settings.DB_PASS = "123456"  # Set DB password as per user

# Ensure DAO config uses the same credentials as core.settings
from dao.config import DatabaseConfig
DatabaseConfig.PASSWORD = settings.DB_PASS

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
    print("\n--- Test 1 ---")
    str="添加一个assignment 叫AA,due date是2025/11/19，它属于课程COMP7103，应该是这样的"
    chat_input = ChatInput(user_id=1, message=str)
    result = agent.chat(chat_input)
    print("User:", chat_input.message)
    print("Agent Reply:", result.reply)

    print("\n--- Tests completed ---")

if __name__ == "__main__":
    test_chat_scenarios()
