"""
Test script for Knowledge Base Updater
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper_agent import update_knowledge_base

# Test credentials
USER_ID = 1
EMAIL = input("Enter your HKU email: ")
PASSWORD = input("Enter your HKU password: ")


def main():
    # Run the update
    stats = update_knowledge_base(
        user_id=USER_ID,
        user_email=EMAIL,
        user_password=PASSWORD,
        headless=True,
        verbose=True,
    )

    print("\n" + "=" * 60)
    print(stats)

if __name__ == "__main__":
    main()
