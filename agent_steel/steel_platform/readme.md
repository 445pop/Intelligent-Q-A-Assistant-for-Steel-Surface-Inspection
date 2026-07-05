在仓库根目录 e:\code_steel 执行（需先 pip install -r requirements.txt）：
python -m uvicorn steel_platform.main:app --reload --host 127.0.0.1 --port 8000
浏览器打开 http://127.0.0.1:8000/docs 可调 Swagger。

触发事件的 ingest 示例要点：至少 3 条同类缺陷，时间递增，position_mm 可成等间距（便于规则层给出「强/弱周期」）；字段需含 defect_class、batch_id、line_id、camera_id、timestamp。

冒烟：
python scripts\smoke_test.py
tools/mock_tools.py 是各函数与 MySQL/Milvus/RAG 调用，orchestrator.py 是 LangChain + Qwen 调用