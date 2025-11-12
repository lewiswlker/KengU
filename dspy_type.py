import asyncio

from agents import AgentType
from agents.llm import LLM


async def test_route():
    llm = LLM()

    # Test cases with expected agent types
    test_cases = [
        ("帮我规划一下下学期的课程", [AgentType.PLANNER]),  # Should route to planner
        ("从Moodle上抓取我的成绩数据", [AgentType.SCRAPER]),  # Should route to scraper
        ("根据我的笔记回答问题", [AgentType.RAG]),  # Should route to rag
        ("你好，今天天气怎么样", [AgentType.GENERAL]),  # Should route to general
        ("帮我分析这篇论文", [AgentType.RAG]),  # Should route to rag
    ]

    print("Testing LLM route function...")
    print("=" * 50)

    for i, (request, expected) in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Request: {request}")
        print(f"Expected: {expected}")

        try:
            result = await llm.route(request)
            print(f"Actual: {result}")

            # Check if result matches expected
            if result == expected:
                print("✅ PASS")
            else:
                print("❌ FAIL")
        except Exception as e:
            print(f"❌ ERROR: {e}")

        print("-" * 30)


if __name__ == "__main__":
    asyncio.run(test_route())
