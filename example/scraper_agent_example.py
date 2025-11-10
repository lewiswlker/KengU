"""
Test script for Knowledge Base Updater
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import update_knowledge_base

# Test credentials
USER_ID = 1
# EMAIL = input("Enter your HKU email: ")
EMAIL = "u3665467@connect.hku.hk"
# PASSWORD = input("Enter your HKU password: ")
PASSWORD = "Renliubo1891412"

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
