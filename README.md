# WorkBuddy 项目成果集

本仓库汇总了在 WorkBuddy 中完成的多个独立小工具与实验性项目，按子目录组织，彼此无依赖。

## 目录结构

| 子目录 | 说明 | 技术栈 | 运行方式 |
|---|---|---|---|
| [`动漫图片下载器GUI`](./动漫图片下载器GUI) | 本地动漫图片批量下载器（Pixiv + Safebooru 双源，支持登录态 Cookie 拉取 R18） | Python 3.13 + PySide6 + requests + Pillow | `python main.py` |
| [`FPC订单结算工具`](./FPC订单结算工具) | FPC 柔性板订单结算网页小工具（税率/运费/汇总/打印/CSV 导出） | 单文件 HTML + 原生 JS | 浏览器直接打开 `index.html` |
| [`Cline-DeepSeek环境搭建`](./Cline-DeepSeek环境搭建) | Cline + 免费大模型 API 的本地开发环境搭建与代码重构验证脚本 | Python 3.13 + OpenAI 兼容 SDK | 见子目录 README |
| [`动漫图片测试下载`](./动漫图片测试下载) | 下载器端到端实测的样例图片产出 | — | — |

## 各项目亮点

### 动漫图片下载器 GUI
- 双数据源：Pixiv（含可选登录态 Cookie 扩大 R18 可见范围）、Safebooru（全年龄）。
- R18 默认放行（不再剔除）；AI 图过滤为**可切换开关**（默认屏蔽 `aiType 1/2`，可一键放行）。
- Cookie 仅会话内存持有、不落盘；裸值自动补 `PHPSESSID=` 前缀。
- 并发 ≤5、暂停/取消、Pillow 截断校验、Qt 内置图标（无 emoji）、深色主题。
- 离线单测 27 项全 PASS（`test_logic.py`）。

### FPC 订单结算工具
- 纯前端单文件，离线可用；税率默认 13% 可调、实时汇总、浏览器打印 A4、CSV 导出（UTF-8 BOM）、草稿 localStorage。

## 安全说明
- 所有 API Key 仅通过环境变量 / `.env` 读取，`.env` 已加入 `.gitignore`，**不会进入版本库**。
- WorkBuddy 私有记忆目录 `.workbuddy/` 已忽略。

## 环境要求
- Python 3.13+（GUI 项目依赖见各子目录 `requirements.txt`）。
- 现代浏览器（FPC 工具）。
