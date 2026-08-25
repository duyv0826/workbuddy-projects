# 更新日志（Changelog）

本文件记录本仓库每次可发布版本的变更。

- 条目格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。
- 版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)（`<MAJOR>.<MINOR>.<PATCH>`）：
  - **MAJOR**：不兼容的变更或重大重构；
  - **MINOR**：向后兼容的新功能；
  - **PATCH**：向后兼容的问题修复。
- 每条变更归入以下分类之一：**新增（Added）** / **变更（Changed）** / **修复（Fixed）** / **移除（Removed）** / **安全（Security）**。
- 发版时请为对应版本创建 git tag（如 `v1.0.0`），并将本文件底部的版本比较链接回填为真实地址（首版可直接指向 Release 页）。

## [Unreleased]

（尚未打标签的变更暂记此处）

## [1.0.0] - 2026-08-25

首个公开准备基线：完成全部代码成果入库，以及完整的文档与开源合规护栏搭建。

### 新增（Added）
- **动漫图片下载器 GUI**：PySide6 多线程下载器，支持 Pixiv 匿名 / 登录态 Cookie、R18 放行、AI 图过滤可切换开关，含 27 项离线单测。
- **FPC 订单结算工具**：单文件 HTML 优惠券组合结算器（税率 / 运费 / 汇总 / 打印 / CSV 导出 / 草稿）。
- **Cline-DeepSeek 环境搭建**：智谱 GLM-4.7-Flash 配置与验证脚本（密钥走 `.env`，已忽略；脚本仅用标准库，无需 `pip install`）。
- **动漫图片测试下载**：Safebooru 真实样例（SFW，仅用于功能验证）。
- **根总览 README**：目录结构 / 子项目文档导航 / 安全说明 / 许可证 / 贡献章节。
- **四份子项目同规格详细 README**：动漫图片下载器 GUI、FPC 订单结算工具、Cline-DeepSeek 环境搭建、动漫图片测试下载。
- **CONTRIBUTING.md**：环境准备 / 分支管理 / 提交格式 / PR 流程 / 审查标准 / 本地验证清单。
- **Issues / PR 模板**（`.github/`）：缺陷报告、功能建议、PR 提交模板（含 P0 视觉规范与检查清单）。
- **LICENSE**（MIT）：为未来转开源做准备。
- **SECURITY.md** 与 **.github/CODEOWNERS**：转公开的漏洞上报通道与审查责任人护栏。
- **根 README 顶部私有仓库提示**：防误触一键公开导致样图外泄。
- **docs/本地一键复现速查.md**：各子项目本地环境复现速查（环境准备 / 依赖安装 / 启动命令 / 验证步骤）。

### 变更（Changed）
- （本版无）

### 修复（Fixed）
- （本版无）

### 移除（Removed）
- （本版无）

### 安全（Security）
- 全仓库密钥 / 凭据（`.env`、Pixiv Cookie、API Key、GitHub Token）不入库；`.workbuddy/` 已忽略。
- 第三方版权样图（`动漫图片测试下载/`）不受 MIT 覆盖，转公开前须确认授权或移除。

[Unreleased]: https://github.com/duyv0826/workbuddy-projects/compare/main...HEAD
[1.0.0]: https://github.com/duyv0826/workbuddy-projects/releases/tag/v1.0.0
