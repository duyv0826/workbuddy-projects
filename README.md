# WorkBuddy 项目成果集

> **私有仓库提示**：本项目当前为 **私有（Private）** 状态。计划转为公开（Public）前，请务必先确认 `动漫图片测试下载/` 目录中的样图已获原作者授权或已移除——这些第三方版权图片**不受**本仓库 MIT 许可证覆盖，误触一键公开可能导致外泄。转公开前请先阅读 [SECURITY.md](./SECURITY.md) 与 `动漫图片测试下载/README.md` 的「使用注意事项」。

本仓库汇总了在 WorkBuddy 中完成的多个独立小工具与实验性项目，按子目录组织，彼此无依赖。

## 目录结构

| 子目录 | 说明 | 技术栈 | 运行方式 |
|---|---|---|---|
| [`动漫图片下载器GUI`](./动漫图片下载器GUI) | 本地动漫图片批量下载器（Pixiv + Safebooru 双源，支持登录态 Cookie 拉取 R18） | Python 3.13 + PySide6 + requests + Pillow | `python main.py` |
| [`FPC订单结算工具`](./FPC订单结算工具) | FPC 柔性板订单结算网页小工具（税率/运费/汇总/打印/CSV 导出） | 单文件 HTML + 原生 JS | 浏览器直接打开 `index.html` |
| [`Cline-DeepSeek环境搭建`](./Cline-DeepSeek环境搭建) | Cline + 免费大模型 API 的本地开发环境搭建与代码重构验证脚本 | Python 3.13 + OpenAI 兼容 SDK | 见子目录 README |
| [`动漫图片测试下载`](./动漫图片测试下载/README.md) | 下载器端到端实测的样例图片产出 | — | — |

## 子项目文档导航

新协作者可按下表快速定位各子项目的详细文档与一句话定位：

| 子项目 | README | 一句话定位 |
|---|---|---|
| 动漫图片下载器 GUI | [README.md](./动漫图片下载器GUI/README.md) | 本地动漫图片批量下载器（Pixiv + Safebooru 双源，支持登录态 Cookie 拉取 R18、AI 图过滤可切换），含 27 项离线单测。 |
| FPC 订单结算工具 | [README.md](./FPC订单结算工具/README.md) | 纯前端单文件 FPC 柔性板订单结算小工具（税率/运费/汇总/打印/CSV 导出/草稿保存）。 |
| Cline-DeepSeek 环境搭建 | [README.md](./Cline-DeepSeek环境搭建/README.md) | Cline + 免费大模型 API 的本地开发环境配置与代码重构验证脚本（.env 配置 / 脚本运行 / 故障排查）。 |
| 动漫图片测试下载 | [README.md](./动漫图片测试下载/README.md) | 下载器端到端实测的真实样例图片产出，可对照验证抓取链路。 |

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

## 许可证

本仓库的代码与文档以 **MIT 许可证** 发布，详见 [LICENSE](./LICENSE) 文件。

注意：仓库内 `动漫图片测试下载/` 目录中的样图系从公开图站抓取的**第三方作品**，版权归原作者所有，**不**受本仓库 MIT 许可证覆盖，仅用于下载器功能验证，请勿商业使用或再分发（详见该子目录 README 的「使用注意事项」）。

## 环境要求
- Python 3.13+（GUI 项目依赖见各子目录 `requirements.txt`）。
- 现代浏览器（FPC 工具）。

## 贡献与问题反馈

本仓库通过 GitHub 内置模板规范反馈与提交流程：

- **报告缺陷**：使用 [Bug 报告模板](./.github/ISSUE_TEMPLATE/bug_report.md)，附环境信息与脱敏日志。
- **提出功能建议**：使用 [功能建议模板](./.github/ISSUE_TEMPLATE/feature_request.md)。
- **提交代码**：PR 请遵循 [Pull Request 模板](./.github/PULL_REQUEST_TEMPLATE.md)，含自测结果与检查清单（不提交密钥、不用 emoji 作图标、不写紫粉渐变主视觉与 AI 模板味空话）。

提交前请确保：分支基于最新 `main`；密钥/凭证（`.env`、Cookie、API Key）不入库；必要文档已同步更新。

更完整的开发协作规范（环境准备、分支管理、提交格式、PR 流程、审查标准、本地验证）见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

相关文档：
- **版本与变更记录**：见 [CHANGELOG.md](./CHANGELOG.md)（语义化版本 + Keep a Changelog 格式）。
- **提交规范与开源发布 SOP**：见 [SOP-代码提交与开源发布流程.md](./SOP-代码提交与开源发布流程.md)（含私有转公开前检查清单）。
- **本地一键复现速查**：见 [docs/本地一键复现速查.md](./docs/本地一键复现速查.md)（各子项目环境准备 / 依赖 / 启动 / 验证）。
