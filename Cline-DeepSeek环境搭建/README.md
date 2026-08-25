# Cline + 免费大模型 API 开发环境

本目录为「Cline（VS Code 扩展）+ 免费大模型 API」本地开发环境搭建与代码重构验证脚本。

## 文件说明
- `cline_config.json` — Cline 的模型/API 接入配置示例。
- `hello_world_project/` — 用于验证流程的示例工程。
- `run_refactor.py` — 单文件代码重构工具（CLI 参数驱动，读取源码经大模型重构后落盘）。
- `verify_refactor.py` — 连接大模型 API 的端到端验证脚本（含 429 限速指数退避重试）。
- `.env` — **本地密钥文件，已被 `.gitignore` 忽略，请勿提交**（存放 `ZHIPU_API_KEY` / `OPENROUTER_API_KEY`）。

## 使用
1. 复制 `.env` 模板并填入你的 API Key（参考 `verify_refactor.py` 顶部注释）。
2. 在支持 Cline 的 VS Code 中导入 `cline_config.json`。
3. 运行 `python verify_refactor.py` 验证连通性与鉴权。

> 注：外部大模型 API 额度与可用性随时间变化，请以各平台当前免费档为准。
