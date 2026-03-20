# ShopMate

ShopMate 是一个面向毕设演示的智能购物助手网站，支持 AI 对话、关键词提取、多源商品聚合、动态维度分析，以及在真实数据源不可用时无感回退到 mock 数据。

## 技术栈

- 前端：Vue 3 + Vite + Pinia + Vue Router + ECharts
- 后端：FastAPI + SQLite
- 数据接入：MCP 适配层 + mock provider
- 模型接入：OpenAI-compatible HTTP API（未配置时自动回退 mock 规划器）

## 目录结构

```text
backend/   FastAPI 服务
frontend/  Vue 3 前端
```

## 后端启动

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

如果你在 Windows + Anaconda 下直接执行 `uvicorn` 遇到 `_ssl` DLL 报错，优先改用：

```bash
cd backend
python -m uvicorn app.main:app --reload
```

仓库里也提供了一个更稳的 Windows 启动脚本：

```bash
cd backend
run_backend.bat
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```
