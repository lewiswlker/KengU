# KengU

你的香港大学智能学习伙伴。

![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20RAG-green)
![Frontend](https://img.shields.io/badge/frontend-Vue%203-42b883)
![Database](https://img.shields.io/badge/database-MySQL-blue)

[English](README.md) | 简体中文

KengU 是一个面向香港大学学生的智能学习助手，通过多智能体（Multi-Agent）与检索增强生成（RAG）技术，帮你：

- 管理和同步课程资料（Moodle + Exambase）
- 组织作业与学习计划
- 基于课程资料进行问答和复习
- 以聊天形式统一地完成以上操作

## 目录

- [功能特性](#功能特性)
- [整体架构](#整体架构)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [主要接口](#主要接口)
- [RAG 流程](#rag-流程)
- [注意事项](#注意事项)

## 功能特性

- 课程上下文感知聊天助手：根据用户选课、课程资料和历史对话给出回答
- HKU 账号登录与验证：支持通过 HKU Portal（connect.hku.hk / hku.hk）登录并本地保存账号
- Moodle & Exambase 爬取：自动下载课程文件、往年试卷到本地 `knowledge_base/`
- RAG 检索问答：使用向量数据库（Chroma）检索课程资料，再由 LLM 生成答案
- 学习计划 & 作业管理：从 Moodle 日历抓取作业，写入数据库并提供查询/标记完成接口
- 任务进度跟踪：知识库更新、日历爬取等长任务支持后台执行和进度轮询

## 整体架构

整体结构大致分为三层：

- Backend（Python / FastAPI）
  - `services/serve.py` 提供主 REST API 与 SSE 流式接口
  - 使用 MySQL 存储用户、课程、作业与学习记录（`dao/`）
  - 使用 Selenium + WebDriver 抓取 HKU Moodle / Exambase（`rag_scraper/`、`planner_scraper/`）

- Agents & LLM
  - `agents/` 中封装多种智能体：
    - `PlannerAgent`：学习计划与时间管理
    - `RAGAgent`：课程内容检索与问答
    - Scraper agent：触发知识库更新流程
  - 通过 `agents/llm.py` 和 `core/config.py` 使用兼容 OpenAI 的接口（如 Qwen）

- Frontend（Vue 3）
  - 位于 `kengu-fronted/`，使用 Vue 3 + Element Plus + Pinia
  - 提供登录、课程列表、知识库更新、聊天与作业管理 UI

## 快速开始

### 1. 环境依赖

- Python 3.10+
- Node.js 16+，npm
- MySQL 8.x
- Google Chrome（用于 Selenium 爬虫）

### 2. 后端配置

1. 克隆仓库并进入目录：

   ```bash
   git clone https://github.com/lewiswlker/KengU.git
   cd KengU
   ```

2. 创建并激活虚拟环境（推荐）：

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 使用: .venv\Scripts\activate
   ```

3. 安装后端依赖（示例，需要根据实际环境调整）：

   ```bash
   pip install fastapi uvicorn "pydantic>=2" pymysql selenium webdriver-manager \
              chromadb requests openai dspy-ai python-multipart
   ```

4. 配置数据库：

   - 创建数据库：

     ```sql
     CREATE DATABASE kengu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     ```

   - 使用 `sql/create_table.sql` 初始化表结构：

     ```bash
     mysql -u root -p kengu < sql/create_table.sql
     ```

   - 根据本地环境修改：
     - `dao/config.py` 中的 `DatabaseConfig`
     - 或通过环境变量覆盖 `core/config.py` 中的 `DB_*` 设置

5. 配置 LLM 与向量检索（最简方式）：

   - 在 `core/config.py` 中配置 `LLM_API_KEY`、`LLM_API_ENDPOINT`、`LLM_MODEL_NAME`
   - 在环境变量中配置向量服务相关参数（可选）：
     - `EMBEDDING_API_KEY`
     - `EMBEDDING_API_URL`
     - `EMBEDDING_MODEL`
     - `INDEX_DIR`（向量库持久化目录，默认 `./vectorbase`）

6. 启动后端服务（开发模式）：

   ```bash
   python -m services.serve
   ```

   默认监听 `http://127.0.0.1:8009`，并挂载：

   - API 前缀：`/api`
   - 静态课程资料：`/knowledge_base` → 本地 `knowledge_base/` 目录

### 3. 前端配置

1. 进入前端目录并安装依赖：

   ```bash
   cd kengu-fronted
   npm install
   ```

2. 同时启动前端 + 后端（推荐开发脚本）：

   ```bash
   npm run start
   ```

   该脚本等价于并行执行：

   - `npm run backend` → `python -m services.serve`
   - `npm run serve -- --host 0.0.0.0` → Vue 开发服务器

   因此请确保：

   - 已按上文安装好 Python 依赖
   - 当前工作目录为仓库根目录（`npm run backend` 需要能找到 `services/serve.py`）

## 项目结构

核心目录结构（简化）：

```bash
.
├── agents/                # 多智能体：规划、RAG、爬虫等
├── api/                   # 旧版 API（主要以 services/api 为准）
├── auth/                  # HKU Portal 账号验证（Selenium）
├── core/                  # 全局配置（LLM / 数据库等）
├── dao/                   # 数据访问层（用户、课程、作业等）
├── docs/                  # 序列图和流程文档（Mermaid）
├── knowledge_base/        # 课程文件（Moodle / Exambase 下载，需本地生成）
├── rag/                   # RAG 相关：chunking、embedding、向量库、检索
├── rag_scraper/           # Moodle / Exambase 爬虫
├── planner_scraper/       # Moodle 日历爬虫（生成作业）
├── services/              # FastAPI 后端及 REST API
├── kengu-fronted/         # Vue 3 前端项目
├── sql/create_table.sql   # MySQL 表结构
├── vectorbase/            # Chroma 持久化目录（可由 vectorbase.zip 初始化）
└── main.py                # 早期入口（推荐使用 services/serve.py）
```

## 主要接口

这里只列出部分常用接口，完整定义可见 `services/api/`：

- Auth（`services/api/auth_api.py`）
  - `POST /api/hku-auth`：使用 HKU 账号进行登录验证并在本地创建/更新用户

- Course & Knowledge Base（`services/api/course_api.py`）
  - `POST /api/update-data`：后台任务，触发 Moodle + Exambase 爬取并更新知识库
  - `POST /api/update-events`：爬取 Moodle 日历事件并写入 `assignment` 表
  - `POST /api/task-status`：查询后台任务进度

- Chat & RAG（`services/api/chat_api.py`）
  - `POST /api/chat/stream`：SSE 流式聊天接口，内部会根据意图路由到 Planner / RAG / Scraper 等智能体

- Schedule & Assignments（`services/api/schedule_api.py`）
  - 提供作业创建、查询、标记完成/恢复等接口

前端主要通过 `http://127.0.0.1:8009/api/...` 访问这些接口。

## RAG 流程

KengU 的检索增强生成流程大致如下：

1. 通过 `rag_scraper/` 和 `agents/scraper_agent/` 将 Moodle / Exambase 的课程资料下载到 `knowledge_base/`
2. 使用 `VectorEmbeddingsGenerator`（`agents/scraper_agent/embeddings_generator.py`）读取下载日志并：
   - 调用 `RagService.ingest_file()` 对课程文件进行解析与 chunk 切分
   - 调用嵌入服务（`rag/embedder.py`）生成向量
   - 将向量写入 Chroma 向量库（`rag/vector_store.py`）
3. 问答时：
   - `RAGAgent` 根据用户问题和选课信息筛选相关课程
   - `RagService.retrieve()` 在向量库中检索相关片段
   - `ChatAgent` 将检索结果与对话历史一起送入 LLM，生成最终回答

## 注意事项

- 本项目仍处于开发阶段，接口和数据结构可能有变动
- 代码中部分密钥目前是硬编码的，部署到真实环境前请务必：
  - 将密钥移出代码，改用环境变量或配置文件
  - 为生产环境配置独立的数据库和向量库
- 如果你打算在自己的环境里运行：
  - 建议先在本地创建全新的 LLM / Embedding API Key
  - 使用自己的 MySQL 实例和测试账号

欢迎根据自己的使用场景继续完善文档与脚本（如添加 `requirements.txt`、Dockerfile 等）。

