# SOP：代码提交规范与开源发布流程

本文档规定本仓库的 Git 提交信息规范，以及将**私有仓库转为公开（开源发布）**前的标准操作流程。面向所有贡献者，作为 CONTRIBUTING.md 的配套细则。

---

## 一、提交信息规范（Conventional Commits）

### 1.1 格式

```
<type>(<scope>): <subject>

<可选 body>

<可选 footer>
```

- `type`：类型前缀（必填，见下表）。
- `scope`：影响范围（可选，如子项目名 `gui` / `fpc` / `cline`）。
- `subject`：简洁描述（必填）。
- `body`：说明「为什么」，而不只是「是什么」（可选）。
- `footer`：关联 Issue / 破坏性变更（可选），如 `Closes #12`、`Refs #3`。

### 1.2 类型前缀

| 前缀 | 含义 | 示例 |
|---|---|---|
| `feat` | 新功能 | `feat(gui): 新增 R18 放行开关` |
| `fix` | 修复缺陷 | `fix(gui): 修正 Cookie 空值崩溃` |
| `docs` | 仅文档变更 | `docs: 新增 CONTRIBUTING.md` |
| `style` | 格式调整（不影响逻辑） | `style: 统一缩进为 4 空格` |
| `refactor` | 重构（非新功能 / 非修复） | `refactor(core): 抽离下载逻辑` |
| `perf` | 性能优化 | `perf(gui): 并发上限调整至 5` |
| `test` | 测试相关 | `test: 补 27 项离线单测` |
| `build` | 构建 / 依赖 | `build: 升级 PySide6 至 6.9.3` |
| `ci` | CI 配置 | `ci: 加入 pytest 工作流` |
| `chore` | 杂务 / 其他 | `chore: 更新 .gitignore` |

### 1.3 要求

- `subject` 使用祈使句、简洁、不超过 50 字、不以句号结尾。
- 一个提交只做一类事；混合变更请拆分。
- 关联 Issue 写在 footer：`Closes #12`（关闭）或 `Refs #3`（提及）。
- 禁止在提交信息中写入密钥、Cookie、个人信息。

---

## 二、分支与 PR 流程（摘要）

完整版见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

1. 基于 `main` 切分支：`feat/<描述>` / `fix/<描述>` / `docs/<描述>`。
2. 本地提交遵循本文「一、提交信息规范」。
3. 提交前 `git fetch` + `rebase origin/main`，并跑本地验证（见 CONTRIBUTING 各子项目命令）。
4. 推送分支，开 PR，填写 PR 模板，关联 Issue，附自测结果。
5. 审查通过后合入 `main`，删除临时分支。

---

## 三、私有 → 公开（开源发布）检查清单

在执行 GitHub 的「Change visibility → Public」，或运行

```bash
gh repo edit duyv0826/workbuddy-projects --visibility public
```

**之前**，逐项确认：

### 1. 敏感信息核查
- [ ] `git log -p` 与 `git ls-files` 中无 API Key / Token / Cookie / 密码等**真实值**。
- [ ] `.env`、`*.env`、`.workbuddy/`、`__pycache__/` 未被跟踪（已被 `.gitignore` 忽略）。
- [ ] 确认**历史提交**中无密钥（如有，须用 `git filter-repo` 清理或重建仓库后再公开）。
- [ ] 通知邮箱、个人姓名等个人信息确认可公开。

### 2. 许可证与文档
- [ ] 根目录存在 `LICENSE`（MIT），版权人 / 年份正确。
- [ ] 四份子项目 README + 根总览 README + `CONTRIBUTING.md` 齐备且最新。
- [ ] `Issues / PR 模板`、`CODEOWNERS`、`SECURITY.md` 已就位。
- [ ] 已阅读根 README 顶部「私有仓库提示」，确认无遗漏项。

### 3. 第三方内容授权
- [ ] `动漫图片测试下载/` 样图已获原作者授权，或已移除（MIT **不覆盖**第三方版权图）。
- [ ] 如含其他第三方素材 / 代码片段，确认许可证兼容并已标注出处。

### 4. 忽略与构建配置
- [ ] `.gitignore` 覆盖构建产物、依赖目录、密钥、私有记忆（`.workbuddy/`）。
- [ ] `requirements.txt` / 依赖清单完整，他人可一键复现。

### 5. 发版动作（公开后可选）
- [ ] 创建首个 git tag：`git tag v1.0.0 && git push origin v1.0.0`。
- [ ] 回填 `CHANGELOG.md` 顶部版本比较链接。
- [ ] 在 GitHub 创建 Release 说明，关联 CHANGELOG 对应条目。

---

## 四、紧急情况处置

若公开后才发现密钥泄漏：

1. **立即**将仓库转回私有（`gh repo edit ... --visibility private`）。
2. **就地轮换**所有泄露凭证：作废 Pixiv 登录态、重置 API Key / Token、改密码。
3. 用 `git filter-repo` 从历史彻底清除密钥，或重建干净仓库。
4. 重新评估并走完本文「三、检查清单」后再公开。

---

## 五、版本与变更记录

版本演进见 [CHANGELOG.md](./CHANGELOG.md)。
