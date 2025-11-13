# test.py
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.agents.planner import ScheduleInput,ProgressQuery
from agents.planner_agent.planner_agent import PlannerAgent, LLMConfig

# sample task titles (strings expected by current ScheduleInput.tasks)
sample_tasks = [
    "Assignment 10: Mark complete and review (assignment_id=10)",
    "Read Chapter 3: concepts and examples",
    "Practice problems set 2",
    "Prepare slides for weekly review"
]

# dict variant (can be passed directly if schedule accepts dict)
sample_input_dict = {
    "user_id": 1,
    "tasks": sample_tasks,
    "date_range": "2025-11-01 to 2025-12-31"
}

# Pydantic model instance variant
sample_input_obj = ScheduleInput(**sample_input_dict)


# progress 测试的输入数据
progress_input_dict = {
    "user_id": 1
}

progress_input_obj = ProgressQuery(**progress_input_dict)

if __name__ == "__main__":
    # 在创建对象时指定本地Ollama配置
    llm_config = LLMConfig.local_ollama(
        base_url="http://localhost:11434",
        model="deepseek-r1:1.5b"
    )

    planner_agent = PlannerAgent(llm_config=llm_config)

    print("🤖 PlannerAgent 创建成功")
    print(f"🔧 LLM配置: {planner_agent.get_llm_config()}")

    # 测试schedule方法
    print("\n🚀 开始测试智能日程规划...")
    res = planner_agent.schedule(sample_input_obj)
    print("📅 规划结果:")
    print(res)

    # 测试progress方法
    print("\n" + "=" * 50)
    print("🚀 开始测试进度查询...")
    print("=" * 50)
    progress_res = planner_agent.progress(progress_input_obj)
    print("📊 进度查询结果:")
    print(f"已完成: {progress_res.completed}")
    print(f"待办: {progress_res.pending}")
    print(f"总计: {progress_res.total}")

    # 显示详细信息
    if progress_res.details:
        print("\n📝 详细信息:")
        for detail in progress_res.details:
            detail_type = detail.get('type', 'unknown')
            print(f"  - {detail_type}: {detail}")