# Cline + 免费大模型 API 开发环境

本目录是一套**本地开发环境搭建与代码重构验证**的最小可用组合：用 **Cline（VS Code 扩展）+ 智谱 GLM-4.7-Flash（永久免费档）** 跑通「大模型辅助代码重构」工作流，并附两个**零第三方依赖**的命令行验证脚本，让你在不依赖 Cline GUI 的情况下也能独立验证 API 连通性、鉴权与基础推理能力。

## 模块简介

- **目标**：把「免费大模型 API」接入本地编码工具链，用于代码重构、解释、生成等辅助任务。
- **当前生效模型**：智谱 `GLM-4.7-Flash`（OpenAI 兼容格式，2026 永久免费档、200K 上下文、编程 SOTA 国产第一梯队）。
- **为什么选智谱而非 OpenRouter 免费档**：OpenRouter 上 DeepSeek 系列 `:free` 已于 2026-08 撤销，`dots-studio/dots-3-note-preview:free` 也将在 2026-09-30 下线；智谱免费档稳定、无 429 限速、无明确下线风险。
- **两个脚本的定位**：
  - `verify_refactor.py`：端到端验证（连接 + 鉴权 + 推理 + 一致性校验），普通 `urllib` 直连，不依赖 Cline。
  - `run_refactor.py`：可复用的单文件重构工具（CLI 参数驱动，读源 → 调模型 → 校验 → 落盘），同样仅用标准库。

> 注：外部大模型 API 的额度、免费档与可用性随时间变化，请以各平台当前政策为准。本目录配置于 2026-08-24 实测跑通。

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.10+（脚本仅用标准库；已在 3.13 验证）。无需虚拟环境，但建议用 venv 隔离。 |
| 第三方依赖 | **无**。两个脚本均只调用 `urllib` / `json` / `os` / `time` / `argparse` / `sys`，`pip install` 任何包都不是必须的。 |
| 网络 | 可访问 `https://open.bigmodel.cn/api/paas/v4`（智谱 OpenAI 兼容端点）。 |
| 智谱 API Key | 在智谱开放平台（bigmodel.cn）开通并获取 `ZHIPU_API_KEY`（GLM-4.7-Flash 免费档）。 |
| VS Code + Cline | **仅「在 Cline 中使用」时需要**；只跑命令行脚本则不需要。 |

## 目录结构

```
Cline-DeepSeek环境搭建/
├── cline_config.json     # Cline 模型/API 接入配置示例（含已实测生效的模型说明）
├── hello_world_project/  # 用于验证的示例工程
│   └── main.py           # 故意写得"可重构"的购物车计价函数（供模型重构测试）
├── run_refactor.py       # 单文件代码重构工具（CLI 参数驱动，标准库实现）
├── verify_refactor.py    # 端到端连接/鉴权/推理验证脚本（含 429 指数退避重试）
├── .env                  # 本地密钥文件（已被 .gitignore 忽略，切勿提交）
└── README.md             # 本说明
```

## 配置流程（重点：`.env`）

### 1. 创建 `.env` 文件

在本目录（`Cline-DeepSeek环境搭建/`）新建 `.env`，写入所需环境变量。本模块**只需一个必填变量**，一个可选变量：

| 变量名 | 必填 | 说明 | 取值示例 |
|--------|------|------|----------|
| `ZHIPU_API_KEY` | **是** | 智谱开放平台 API Key，用于 Bearer 鉴权。脚本优先读环境变量，其次读 `.env`。 | `ZHIPU_API_KEY=你的智谱key` |
| `ZHIPU_MODEL` | 否 | 模型名。`verify_refactor.py` 会读取此变量（默认 `glm-4.7-flash`）。`run_refactor.py` 不读此变量，模型由 `--model` 参数决定（默认同为 `glm-4.7-flash`）。 | `ZHIPU_MODEL=glm-4.7-flash` |

`.env` 示例内容（**请替换为你的真实 Key，且不要提交**）：

```env
# 智谱开放平台获取的 API Key（GLM-4.7-Flash 免费档）
ZHIPU_API_KEY=在此填入你的真实智谱key

# 可选：验证脚本使用的模型（不填则用默认 glm-4.7-flash）
ZHIPU_MODEL=glm-4.7-flash
```

> 安全：`.env` 已被本目录与根目录的 `.gitignore` 双重忽略，**不会进入版本库**。切勿把真实 Key 粘贴到聊天、Issue 或任何公开场合；如已泄露，请立即到智谱平台重置 Key。

### 2. 提供 Key 的两种方式（二选一）

- **方式 A — `.env` 文件（推荐）**：如上，在本目录建 `.env`。两个脚本会自动加载（仅当同名环境变量未设置时）。
- **方式 B — 环境变量**：不建 `.env`，直接在 shell 中导出：
  - PowerShell：`$env:ZHIPU_API_KEY = "你的智谱key"`
  - Bash / macOS / Linux：`export ZHIPU_API_KEY="你的智谱key"`
  - 然后运行脚本即可。

## 安装步骤（前置依赖）

本模块的命令行脚本**无需安装任何第三方包**。若只跑 `verify_refactor.py` / `run_refactor.py`，跳过本节第 2 步。

1. **准备 Python**：确认 `python --version` 为 3.10+。建议隔离环境：

   ```bash
   cd Cline-DeepSeek环境搭建
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

2. **（可选）在 VS Code 安装 Cline**：扩展市场搜索 `Cline` 安装；后续「在 Cline 中使用」步骤需要它。命令行脚本不依赖此步。

3. **获取智谱 Key**：登录智谱开放平台（bigmodel.cn）→ 控制台 → 创建 API Key → 复制 `ZHIPU_API_KEY` → 填入 `.env`（方式 A）或导出为环境变量（方式 B）。

## 使用方式

### A. 运行 `verify_refactor.py`（端到端验证）

用途：验证 **连接状态 + 鉴权有效 + 基础推理成功 + 输出格式一致性**，并把重构结果写入 `hello_world_project/main_refactored.py`。

```bash
cd Cline-DeepSeek环境搭建
python verify_refactor.py
```

**预期输出（净化示意，脚本实际输出含状态图标）**：

```
[STEP 1] 模型连接状态：目标端点 https://open.bigmodel.cn/api/paas/v4/chat/completions
[STEP 1] 生效模型名称：glm-4.7-flash
[STEP 1] API Key 已加载：长度 NN 字符（已脱敏，不打印明文）

[STEP 2] API 鉴权与基础推理请求：发送中...

[STEP 3] 基础推理响应：HTTP 200，模型返回成功

[STEP 4] 输出格式与参数一致性校验：
   - 返回结构含 choices[0].message.content：[OK]
   - 请求模型 = glm-4.7-flash | 回显模型 = glm-4.7-flash：[一致]
   - 请求 temperature = 0.2：[已发送]
   - 返回 usage 字段：[完整 JSON]

[OK] 模型调用成功，重构结果如下：

<模型返回的重构后代码>

[INFO] 重构结果已保存到 hello_world_project/main_refactored.py
```

**关键行为**：
- Key 加载后只打印长度，**明文永不出现在日志**。
- 免费档共享池常返 `429`（code 1305 访问量过大），脚本内置**指数退避重试**（等待约 6/12/24/48 秒，最多 5 次）；若仍 429 则提示「重试耗尽」并以非 0 退出。
- 成功后把重构代码落盘到 `hello_world_project/main_refactored.py`。

### B. 运行 `run_refactor.py`（可复用重构工具）

用途：对任意 Python 源文件做重构并落盘，支持 CLI 参数。

```bash
# 默认：重构 hello_world_project/main.py -> hello_world_project/main_refactored.py
python run_refactor.py

# 指定源与目标
python run_refactor.py --source foo.py --output foo_refactored.py

# 换模型（需账号有权限）
python run_refactor.py --model glm-4.7-flash

# 调整采样温度
python run_refactor.py --temperature 0.4
```

**参数表**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--source` | `hello_world_project/main.py` | 待重构的源 Python 文件路径 |
| `--output` | `hello_world_project/main_refactored.py` | 重构结果输出路径（父目录自动创建） |
| `--model` | `glm-4.7-flash` | 模型名（需账号有该模型权限） |
| `--temperature` | `0.2` | 采样温度，越低越稳定 |

**预期输出（净化示意）**：

```
================================================================
智谱 GLM-4.7-Flash 代码重构工具
================================================================
[STEP 0] 前置检查：
   - 源文件：hello_world_project/main.py [OK]
   - API Key：[OK] ab12cd...wxyz        （脱敏显示，非明文）
[STEP 1] 已读取源文件（NNN 字符）
[STEP 2] 调用模型 glm-4.7-flash（temperature=0.2）...
[STEP 3] 响应一致性校验：
   - choices[0].message.content 存在：[OK]
   - 请求模型 = glm-4.7-flash | 回显模型 = glm-4.7-flash：[一致]
   - usage 字段：[完整 JSON]
[STEP 4] 重构结果已保存：hello_world_project/main_refactored.py（NNN 字符）

================================================================
[OK] 重构完成，前 600 字符预览：
<模型返回的重构后代码前 600 字符>
================================================================
```

**关键行为**：
- 退避重试：429 时等待 `6 / 12 / 24 / 48 / 48 / 48` 秒（最多 6 次）。
- 鉴权失败（401）/ 权限不足（403）会给出明确提示并退出。
- 返回结构、模型名一致性、usage 字段完整性均做断言校验。

### C. 在 VS Code + Cline 中使用

1. 在 VS Code 安装 `Cline` 扩展。
2. 打开 Cline 设置 → 提供商选 **OpenAI Compatible**。
3. `baseUrl` 填 `https://open.bigmodel.cn/api/paas/v4`。
4. `apiKey` 粘贴你的 `ZHIPU_API_KEY`（或留空、改由 `.env` 提供，视 Cline 版本而定）。
5. 模型填 `glm-4.7-flash`。
6. 可参考本目录 `cline_config.json`（含已实测生效的模型说明与已弃用模型记录）。

## 故障排查

| 现象 | 可能原因 | 排查与解决 |
|------|----------|------------|
| `[FAIL] 未检测到 ZHIPU_API_KEY` | 既没设环境变量也没建 `.env`，或 `.env` 路径/拼写错 | 确认在本目录运行；`.env` 存在且含 `ZHIPU_API_KEY=...`；或用方式 B 导出环境变量 |
| `[FAIL] HTTP 401` | Key 无效或过期 | 到智谱平台重置 Key，更新 `.env` |
| `[FAIL] HTTP 403` | 该 Key 无此模型调用权限 | 确认账号已开通 GLM-4.7-Flash 免费档；或换 `--model` 为有权限的模型 |
| 反复 `[429]` 后「重试耗尽」 | 免费档共享池限速 | 稍后重试 / 换时段；脚本已自动指数退避，无需手动 |
| `[FAIL] 找不到 hello_world_project/main.py` | 不在本目录运行 | `cd` 到 `Cline-DeepSeek环境搭建/` 再运行 |
| 请求长时间无响应 / 超时 | 网络不可达或端点变更 | 确认能访问 `open.bigmodel.cn`；检查代理/防火墙；超时阈值为 90 秒 |
| 重构结果像原文、未真正重构 | 模型返回被截断或格式异常 | 查看落盘文件；可重跑或调低 `--temperature` |

## 安全与隐私

- **Key 不入库**：`.env` 已被 `.gitignore` 忽略；脚本日志只打印 Key 长度与脱敏片段（`ab12cd...wxyz`），**绝不打印明文**。
- **Key 不进聊天**：任何情况下不要把真实 Key 粘贴到聊天、Issue、PR 或截图。
- **重置习惯**：怀疑泄露时第一时间到智谱平台重置 Key。

## 已知限制与模型说明

- **免费档额度**：GLM-4.7-Flash 为免费档，可用性、速率与上下文上限以智谱平台当期政策为准。
- **OpenRouter 免费档已弃用**：本目录 `cline_config.json` 的 `openrouter_archive` 记录了已撤销/将下线的免费模型，仅供追溯，不要再接入。
- **DeepSeek 官方通道**：`cline_config.json` 的 `alt_official_deepseek` 给出官方 baseUrl（`https://api.deepseek.com/v1`，模型 `deepseek-chat`），但需充值/赠送额度，非完全免费。
- **脚本非生产级**：两个脚本为本地验证与一次性重构设计，未做并发、批量队列或错误恢复之外的工程化封装。

## 常见问题

**Q：必须装 `openai` / `python-dotenv` 吗？**
A：不需要。两个脚本只用 Python 标准库，直接 `python verify_refactor.py` / `python run_refactor.py` 即可。

**Q：只想验证 API 能不能通，跑哪个？**
A：跑 `verify_refactor.py`，它覆盖连接、鉴权、推理、一致性四项检查，最省事。

**Q：`run_refactor.py` 怎么换模型？**
A：用 `--model` 参数，如 `python run_refactor.py --model glm-4.7-flash`；注意目标模型需你的账号有权限。

**Q：为什么日志里 Key 只显示一半？**
A：脚本做了脱敏（`前6...后4`），既证明 Key 已加载，又避免明文泄露。

**Q：在 Cline 里用和在命令行跑脚本，有什么区别？**
A：命令行脚本是「直连验证 + 一次性重构」，不依赖 VS Code；Cline 是把同款模型接入编辑器内做交互式辅助编码。两者共用同一个 `ZHIPU_API_KEY` 与同一端点。
