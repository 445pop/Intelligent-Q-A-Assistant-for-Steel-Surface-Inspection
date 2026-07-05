已按 `agent.txt` 里的**流程 A（检测 → 事件 → Agent/Skill）**和**流程 B（HTTP 问答 → 意图 → 工具）**搭好可运行的 Python 后端骨架，数据层全部用 **Mock**，不接 MySQL/Milvus/真实向量库。

## 目录结构

- `requirements.txt`：FastAPI、Pydantic、NumPy、Uvicorn  
- `steel_platform/`：主包  
  - `main.py`：HTTP 入口（健康检查、缺陷接入、会话问答、事件分析）  
  - `schemas/`：`DefectSample`、`AnomalyEvent`、`PeriodicDefectAnalysis` 等  
  - `services/`：接入校验、**确定性**周期性规则（间距 CV）、事件窗口 embedding 聚合、**事件规则引擎**  
  - `tools/mock_tools.py`：5 类工具占位（生产统计、目标、告警、Milvus、知识库）  
  - `skills/periodic_defect.py`：**周期性缺陷 Skill**（编排：窗口 → 规则 → 相似案例 Mock → RAG Mock → 结构化结论）  
  - `agent/orchestrator.py`：意图粗分 + 工具调用链（与文中「后端预设主流程 + 模型局部决策」对应，此处无真实 LLM，用模板总结）  
- `scripts/smoke_test.py`：本地冒烟（已把仓库根目录加入 `sys.path`）

## 核心流程（与 `agent.txt` 对齐）

1. **缺陷推送**：`POST /v1/defects/ingest` → 校验核心字段 → 事件规则（连续同类 N 次 / 短时 burst）→ 若触发则跑 **周期性缺陷 Skill**，返回 `analysis`（疑似周期性、风险、依据、相似案例条数、建议检查项、知识片段等）。  
2. **智能问答**：`POST /v1/agent/chat`（`session_id` + `question`）→ 意图（生产状态 / 目标达成 / 周期模式说明 / 排查指导 / 通用）→ 调 Mock 工具 → 文本回答；`GET /v1/sessions/{session_id}` 可看短期会话列表。  
3. **单独跑 Skill**：`POST /v1/events/analyze`， body 为 `AnomalyEvent` JSON，便于联调。

## 本地运行

在仓库根目录 `e:\code_steel` 执行（需先 `pip install -r requirements.txt`）：

```bash
python -m uvicorn steel_platform.main:app --reload --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000/docs` 可调 Swagger。

**触发事件的 ingest 示例要点**：至少 **3 条**同类缺陷，时间递增，`position_mm` 可成等间距（便于规则层给出「强/弱周期」）；字段需含 `defect_class`、`batch_id`、`line_id`、`camera_id`、`timestamp`。

冒烟：

```bash
python scripts\smoke_test.py
```

后续你只需把 `tools/mock_tools.py` 里各函数换成真实 MySQL/Milvus/RAG 调用，并把 `agent/orchestrator.py` 的模板总结换成 LangChain + Qwen 调用，即可在不变流程的前提下接到真实环境。若你希望下一步把「多进程推理队列」或 LangGraph 状态机也落成空壳模块，可以说明优先级我接着补。