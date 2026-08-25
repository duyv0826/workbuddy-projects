# 贡献指南（CONTRIBUTING）

本文件说明如何向本仓库（`workbuddy-projects`）提交代码与文档。所有子项目彼此独立、无共享构建系统，因此本指南以「通用流程 + 各子项目验证命令」的方式组织，便于快速上手。

## 1. 适用范围

- 本仓库为**个人项目成果集**，当前默认私有（Private）。欢迎洪兄本人以及被授权协作者提交改动。
- 子项目清单：`动漫图片下载器GUI`（Python + PySide6）、`FPC订单结算工具`（单文件 HTML）、`Cline-DeepSeek环境搭建`（Python 脚本）、`动漫图片测试下载`（样例资源）。
- 提交内容应为：缺陷修复、功能改进、文档完善、测试补充。涉及密钥、凭证、个人隐私的内容**禁止提交**（见第 7 节）。

## 2. 环境准备

### 2.1 获取代码

```bash
git clone https://github.com/duyv0826/workbuddy-projects.git
cd workbuddy-projects
```

### 2.2 各子项目运行环境

| 子项目 | 环境准备 | 本地验证命令 |
|--------|----------|--------------|
| 动漫图片下载器GUI | `cd 动漫图片下载器GUI && python -m venv .venv && source .venv/bin/activate`（Windows：`.venv\Scripts\activate`）`&& pip install -r requirements.txt` | `python test_logic.py`（应全部 PASS）；`QT_QPA_PLATFORM=offscreen python -c "import main"`（校验可加载） |
| FPC订单结算工具 | 无需环境；用现代浏览器打开 `index.html` 即可 | 浏览器打开 → 录入若干行 → 点「导出 CSV」核对文件；或 `python -m http.server` 起本地服务后用 `http://` 访问，验证草稿保存 |
| Cline-DeepSeek环境搭建 | 仅标准库，**无需 pip install**；**必须**准备本地 `.env`（含 `ZHIPU_API_KEY`，可选 `ZHIPU_MODEL`），`.env` 不入库 | `python verify_refactor.py`（需有效 API Key，属外部依赖，本地自测；详见子目录 README） |
| 动漫图片测试下载 | 无运行环境，仅存放样例图片 | 人工核对图片可正常打开 |

> Python 版本：建议使用 **3.13**（与开发环境一致）。`requirements.txt` 已锁定 `PySide6==6.9.3`。

## 3. 分支管理规范

- **主分支**：`main`，受保护，仅通过 PR 合入，不直接 `push`（除非是个人紧急修复且已确认）。
- **功能分支命名**（基于最新 `main` 切出）：
  - `feat/<简短描述>`：新功能，如 `feat/anime-cookie-r18`
  - `fix/<简短描述>`：缺陷修复，如 `fix/fpc-csv-bom`
  - `docs/<简短描述>`：文档，如 `docs/contributing`
  - `refactor/<简短描述>` / `test/<简短描述>`：重构 / 测试
- **保持同步**：提交前先 `git fetch origin && git rebase origin/main`，解决冲突后再推。
- **一个分支一个主题**：避免把不相关的修改混在同一分支，便于审查与回滚。

## 4. 代码提交格式要求

提交信息采用 **Conventional Commits** 风格，结构如下：

```
<type>(<scope>): <subject>

<body（可选，说明为什么改、改了什么）>
```

- **type**（必填）：`feat` / `fix` / `docs` / `style` / `refactor` / `test` / `chore` / `perf`。
- **scope**（可选）：受影响的子项目或模块，如 `anime-gui`、`fpc`、`cline`。
- **subject**（必填）：祈使句、简洁、中文或英文均可，不超过 50 字，句末不加句号。
- **body**（可选）：解释动机与要点，尤其是「为什么」而非「做了什么」。

示例：

```
feat(anime-gui): 新增 Pixiv 登录态 Cookie 支持以扩大 R18 可见范围

- 新增可选 Cookie 输入框与 normalize_pixiv_cookie 裸值补前缀逻辑
- 检索日志区分 [匿名] / [登录态(Cookie)]
- Cookie 仅会话内存持有，不落盘
```

```
docs(fpc): 重写 README 补充参数与输入输出格式章节
```

## 5. Pull Request 提交流程

1. 在功能分支完成修改并通过本地验证（见第 2.2 节）。
2. 推送到远程：`git push -u origin feat/xxx`。
3. 在 GitHub 发起 PR，目标分支选 `main`，**必须使用 [PR 模板](./.github/PULL_REQUEST_TEMPLATE.md)**。
4. PR 描述应包含：
   - 关联 Issue（如有）：`Closes #12` 或 `Related to #12`。
   - 变更类型（feat/fix/docs/...）。
   - 本地验证结果（测试输出、截图或结论）。
   - 检查清单逐项确认。
5. 等待审查（见第 6 节）；审查通过且 CI（如有）绿灯后由维护者合入。
6. 合入后删除功能分支（GitHub 提供「Delete branch」按钮，或本地 `git branch -d feat/xxx`）。

## 6. 代码审查标准

审查由维护者（洪兄 / 被授权协作者）执行，关注以下维度：

- **正确性**：逻辑无误，边界条件（空值、负数、除零、超长输入）有处理。
- **安全性（红线）**：不引入任何密钥、Cookie、API Key；不新增对外网络上传；`.env` 与 `.workbuddy/` 未被误加。
- **最小变更**：改动聚焦主题，不夹带无关格式化或无关文件。
- **文档同步**：用户可见行为变化时，对应 README / 模板已更新。
- **视觉规范（前端 / GUI）**：
  - 不使用 emoji 作为界面图标或文档装饰（用 Qt 内置图标 / 内联 SVG）。
  - 不使用紫粉渐变作为主视觉。
  - 不写「AI 模板味」空话（如堆砌形容词、无实质的占位段）。
- **可测试性**：纯逻辑改动尽量配有可离线运行的单测（`test_logic.py` 风格），GUI / 前端改动至少给出本地验证步骤。

审查结论：通过 / 需修改 / 拒绝。需修改时请在 PR 中回复具体意见，作者推送补丁后重新审查。

## 7. 安全红线（强制）

以下内容**绝对禁止**进入版本库：

- `.env` 文件、任何含 `API_KEY` / `SECRET` / `TOKEN` / `PASSWORD` 的明文凭证。
- Pixiv 或其他站点的 Cookie 整串（仅允许在运行态内存中使用，见 anime-gui README）。
- 个人私有记忆目录 `.workbuddy/`。
- `__pycache__/`、`*.pyc`、IDE 配置（`.vscode/`、`.idea/`）、虚拟环境（`venv/`、`.venv/`）等已纳入 `.gitignore` 的内容。

提交前自查：

```bash
git add -A
git diff --cached --name-only | grep -E "(\.env|\.workbuddy|__pycache__)" && echo "!!! 疑似敏感文件已暂存，请取消" || echo "OK: 无敏感文件"
```

如不慎提交，立即 `git reset HEAD~` 撤销，并轮换已泄露的凭证（改密码 / 重新生成 Key）。

## 8. 测试与本地验证步骤（汇总清单）

在发起 PR 前，请逐项确认：

- [ ] 已基于最新 `main` 切出功能分支并完成修改。
- [ ] 受影响子项目已按第 2.2 节命令本地验证通过（如 anime-gui 的 `test_logic.py` 全 PASS）。
- [ ] 新增/修改的纯逻辑已有对应单测或验证脚本。
- [ ] GUI / 前端改动已实际运行确认（非仅代码审查）。
- [ ] 文档（README / 模板）与行为保持一致。
- [ ] 暂存区不含任何敏感文件或忽略项（见第 7 节自查命令）。
- [ ] 提交信息符合第 4 节格式。
- [ ] PR 已填写模板、关联 Issue、附验证结果。

## 9. 问题反馈

- 发现缺陷：使用 [Bug 报告模板](./.github/ISSUE_TEMPLATE/bug_report.md)。
- 提出功能建议：使用 [功能建议模板](./.github/ISSUE_TEMPLATE/feature_request.md)。
- 反馈前请先搜索现有 Issue，避免重复。
