# SteelDefectDetection-magang

基于 YOLOv5/YOLOv8 的钢材表面缺陷实时检测系统。支持多摄像头（7+ 角度）协同推理、像素坐标到世界坐标转换、缺陷聚合拼接、自动评级（警告/报警），并将结果写入 Elasticsearch 与 MySQL。

## 演示视频

![Demo](demo.gif)

> 完整视频（约 6 分钟）见仓库根目录的 `steel_detection.mp4`（约 95 MB），clone 后本地播放。

---

## 目录结构

```
SteelDefectDetection-magang/
├── doc/                        # 文档（部署实录、技术文档）
├── magang_infer/               # 核心推理框架（算法端统一框架）
│   ├── MyAlgorithmRunner.py    #   主入口：多进程启动器
│   ├── runner1224.py           #   核心推理 + 坐标转换 + 缺陷聚合
│   ├── MyObject/               #   核心类（进程、配置、数据模型）
│   ├── UtilObject/             #   工具类（检测器、数据库、拼接、评级）
│   ├── config/                 #   配置文件（模型、评级、相机参数）
│   ├── yolov5/                 #   YOLOv5 推理（Ascend / NVIDIA）
│   ├── yolov8/                 #   YOLOv8 推理（Ascend）
│   ├── Test/                   #   测试脚本与数据
│   └── Maintenance/            #   Supervisor 配置、模型权重目录
├── agent_steel/                # AI Agent 平台（FastAPI + LangChain 风格编排）
│   └── steel_platform/         #   事件接收、异常检测、周期性分析、智能问答
├── TestWrapper/                # C++ 采集端程序（相机同步、PLC 通信）
└── Yolov5_for_Pytorch/         # 模型转换工具（PyTorch → ONNX → Ascend OM）
```

---

## 系统架构

```
┌──────────────┐    HTTP     ┌─────────────────────────────────────┐
│  C++ 采集端   │ ─────────→  │           magang_infer              │
│ (TestWrapper) │   图片+元数据 │                                     │
│              │             │  HttpProcess  →  InferProcess        │
│  7+ 相机角度  │             │    (HTTP接收)     (YOLOv5/v8 推理)    │
│  灰度+深度图  │             │       ↓                              │
└──────────────┘             │  PosTransform  →  EsProcess          │
                              │   (坐标转换)      (ES/MySQL 写入)     │
                              │       ↓                              │
                              │  PeriodicCheck →  Appraise           │
                              │   (批次汇总)      (自动评级)           │
                              │                                     │
                              │  Create3dProcess                     │
                              │   (3D 深度裁剪)                       │
                              └─────────────────────────────────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │    agent_steel         │
                              │  FastAPI AI Agent 平台  │
                              │  · 异常事件检测          │
                              │  · 周期性缺陷分析        │
                              │  · 智能问答              │
                              └───────────────────────┘
```

### 检测缺陷类型（21 类）

| ID | 缺陷 | ID | 缺陷 | ID | 缺陷 |
|----|------|----|------|----|------|
| 0 | 漏清 | 7 | 裂纹 | 14 | 夹渣 |
| 1 | 沟槽 | 8 | 纵向裂纹 | 15 | 点火坑 |
| 2 | 凹坑 | 9 | 横向裂纹 | 16 | 划痕 |
| 3 | 起棱 | 10 | 角部裂纹 | 17 | 凹槽 |
| 4 | 擦伤 | 11 | 熔渣 | 18 | 误检 |
| 5 | 划伤 | 12 | 熔珠 | 19 | 疑似 |
| 6 | 气孔 | 13 | 夹杂 | 20 | 水渍 |

---

## 快速开始

### 环境要求

- **操作系统**：Ubuntu（产线服务器）
- **推理硬件**：华为 Ascend 处理器 或 NVIDIA GPU
- **Python**：3.8+
- **数据库**：Elasticsearch + MySQL
- **进程管理**：Supervisor

### 安装

```bash
cd magang_infer
pip install -r requirements.txt
```

核心依赖：`opencv-python` `elasticsearch` `pymysql` `ultralytics` `numpy` `torch`

### 配置

1. **修改 `magang_infer/config/setting.yaml`**
   - `model_path`：模型权重路径
   - `data_root`：图片存储路径
   - `image_h` / `image_w`：输入图片尺寸
   - `Database`：ES 和 MySQL 连接信息
   - `process_num` / `gpu_count`：进程数与 GPU 数量
   - `typeid_chinese` / `type_trans_a2c`：缺陷类别映射关系

2. **修改评级配置**
   - 编辑 `magang_infer/config/appraise_mg.json`
   - 在 `MyObject/ProjectConfig.py` 中指定正确的评级文件路径

3. **启动服务**

```bash
supervisord -c magang_infer/Maintenance/supervisor/supervisord.conf
```

### 测试

```bash
# 使用模拟数据测试
python magang_infer/Test/http_send_mainid.py
```

### AI Agent 平台（可选）

```bash
cd agent_steel
pip install -r requirements.txt
cd steel_platform
uvicorn main:app --host 0.0.0.0 --port 8400
```

提供三个核心端点：`/ingest`（缺陷接收）、`/chat`（智能问答）、`/analyze`（周期性分析）。

---

## 模型训练与转换

训练使用浪潮服务器（PyTorch），转换路径：

```
PyTorch (.pt) → ONNX → Ascend OM 格式
```

转换脚本位于 `Yolov5_for_Pytorch/`，支持 v2.0 ~ v6.1 多个 Ascend 版本。详见 `Yolov5_for_Pytorch/Yolov5_for_Pytorch/README.md`。

---

## 文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 算法部署实录 | `doc/算法部署实录.md` | 环境部署、模型训练、配置、运维全流程 |
| 技术文档 | `doc/技术文档.docx` | Word 格式完整技术文档 |
| Agent 平台说明 | `agent_steel/steel_platform/readme.md` | FastAPI 平台快速启动指南 |
| Agent 架构 | `agent_steel/steel_platform/test.md` | Agent 平台架构设计 |
| C++ 采集端 | `TestWrapper/ReadMe.txt` | 相机采集与 PLC 通信说明 |

---

## 技术栈

- **检测模型**：YOLOv5 / YOLOv8
- **推理框架**：华为 Ascend ACL / NVIDIA CUDA
- **后端语言**：Python 3（推理与控制）、C++（图像采集）
- **数据库**：Elasticsearch（缺陷检索）+ MySQL（批次/评级）
- **API 层**：FastAPI（Agent 平台）+ 自定义 HTTP Server（采集对接）
- **进程管理**：Supervisor
- **AI Agent**：LangChain 风格编排 + 工具调用（支持接入 LLM）

---

## License

Internal use — 马钢产线专用。
