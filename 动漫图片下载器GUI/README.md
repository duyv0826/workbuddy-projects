# 动漫图片批量下载器 (GUI)

基于 **Python 3.13 + PySide6** 的桌面端动漫图片批量下载工具。支持 **Pixiv**（经 `pixiv.re` 公共反向代理，可匿名或选填登录态 Cookie）与 **Safebooru**（全年龄图站）两个来源，内置 AI 图过滤开关、R18 放行、暂停/取消、下载截断校验。

## 功能简介

- **双来源采集**：Pixiv（标签搜索 + 原图下载）、Safebooru（标签搜索 + 原图下载）。
- **R18 放行**：Pixiv 检索结果中 `xRestrict != 0` 的内容默认不再剔除，可正常进入下载队列。
- **AI 图过滤开关**：可切换是否屏蔽 `aiType == 1/2` 的 AI 相关作品，默认开启（屏蔽）。
- **可选登录态 Cookie**：Pixiv 源可填入 Cookie 以登录态检索，扩大 R18 可见范围；留空则为匿名会话。
- **并发控制**：最大并发任务数 5，超出时提示等待，不抢占。
- **健壮性**：
  - 单次请求超时 30 秒，失败自动重试 3 次（指数退避，基数 2 秒）。
  - 下载后用 Pillow 全解码校验截断；截断文件删除，下次运行可重下。
  - 已成功下载的文件在下次运行同一任务时跳过（轻量级断点续传）。
- **暂停/取消**：基于 `threading.Event` 协作式退出，每个任务独立 `QThread`，主线程仅更新 UI。
- **深色界面**：bg `#0D1117` / surface `#161B22` / fg `#E6EDF3` / accent `#2F81F7`；图标全部使用 Qt 内置 `QStyle::SP_*` 标准图标（无 emoji）。

## 工作原理

### Pixiv 源

1. **检索**：调用 Pixiv 搜索 API `https://pixiv.net/ajax/search/artworks/{tag}?word={tag}`，取搜索前 N 条作品。
2. **下载**：原图经 `pixiv.re` 公共反向代理获取，链接形如 `https://pixiv.re/{id}.png`，单发 + 限速睡眠以避免限流。
3. **鉴权（可选）**：Cookie 非空时，`pixiv_session_headers()` 会附加登录态 Cookie（PHPSESSID 等），用于扩大 R18 检索范围；留空维持匿名会话。

### Safebooru 源

1. **检索**：调用 `https://safebooru.org/index.php?page=dapi&s=post&q=index&tags={tags}&limit={n}&pid={page}`，返回 XML 解析 `<post file_url source rating tags>`。
2. **翻页**：直到满足设定数量或翻满 10 页（防御性上限）为止。
3. Safebooru 为全年龄站，不做 R18 过滤。

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.13（已在 3.13.14 验证） |
| 操作系统 | Windows / macOS / Linux（PySide6 跨平台，LGPLv3 允许闭源分发） |
| 内存/磁盘 | 常规桌面配置即可；下载目录需足够空闲空间 |
| 网络 | 可访问 `pixiv.net`、`pixiv.re`、`safebooru.org`（Pixiv 源依赖其可用性） |
| 显示 | GUI 应用，需本地桌面环境；无显示的服务端需自行配置 Xvfb 等虚拟显示 |

## 安装步骤

方式一：克隆整个仓库后进入子目录

```bash
git clone https://github.com/duyv0826/workbuddy-projects.git
cd workbuddy-projects/动漫图片下载器GUI
pip install -r requirements.txt
```

方式二：仅取本子目录

将 `动漫图片下载器GUI/` 整个文件夹复制到本地，然后：

```bash
cd 动漫图片下载器GUI
pip install -r requirements.txt
```

依赖清单（`requirements.txt`）：

- `PySide6==6.9.3`（GUI 框架）
- `requests>=2.31`（HTTP 客户端）
- `Pillow>=10.2`（图片截断校验）

> 建议使用虚拟环境：`python -m venv .venv && source .venv/bin/activate`（Windows 为 `.venv\Scripts\activate`），再执行 `pip install -r requirements.txt`。

## 运行方式

```bash
python main.py
```

启动后弹出主窗口：上方为配置区，下方为任务队列与日志区。

- **无图形界面环境**：本工具是 GUI 程序，需在带显示的桌面运行。若在 CI/服务器跑，仅用于校验代码可加载（例如 `QT_QPA_PLATFORM=offscreen python -c "import main"`），不能实际采集。
- **运行单元测试**：

```bash
python test_logic.py
```

应输出「全部 PASS」（当前 27 项离线逻辑测试，覆盖 Cookie 规整、Pixiv/Safebooru 过滤、坏 XML 解析等）。

## 配置说明

主窗口配置区自上而下三行：

| 控件 | 说明 | 默认值 / 约束 |
|------|------|----------------|
| 源（下拉框） | 选择 `Pixiv` 或 `Safebooru` | 必选 |
| 关键词 | 标签名，如 `初音ミク`、`hatsune_miku` | 必填 |
| 数量 | 单次任务需采集的图片数 | 1–500 |
| 保存路径 | 点击「浏览」选择本地目录 | 必选；留空无法开始 |
| Cookie（第二行，仅 Pixiv 源生效） | 可选 Pixiv 登录态 Cookie 整串；留空 = 匿名（R18 仅命中部分） | 留空 |
| 屏蔽 AI 图 (aiType 1/2)（第三行复选框） | 勾选 = 屏蔽 AI 图；取消 = 放行 AI 图 | **默认勾选（屏蔽）** |

补充行为：

- **并发上限 5**：同时运行任务超过 5 个时，新增任务会提示「并发已达上限，请等待其他任务完成」。
- **Cookie 规整**：输入纯裸值（如 `abc123`）会自动补 `PHPSESSID=` 前缀；含 `=` 或 `;` 的整串（如从浏览器复制的 `PHPSESSID=...; device_token=...; cf_clearance=...`）原样透传。
- **Cookie 不落盘**：Cookie 仅存在于本次运行的进程内存中，关闭程序即清除，不会写入任何文件。

## 常见操作示例

### 示例 1：匿名下载 Pixiv 标签

1. 源选择 `Pixiv`。
2. 关键词填 `初音ミク`。
3. 数量填 `20`。
4. 保存路径选一个本地空文件夹。
5. Cookie 留空，保持「屏蔽 AI 图」勾选（如需 AI 图则取消勾选）。
6. 点「添加任务」，再点该任务行的「开始」（或底部「开始」）。
7. 日志出现 `开始采集 Pixiv[匿名 | 屏蔽AI]: 初音ミク` 即正常启动。

### 示例 2：下载 Safebooru 全年龄图

1. 源选择 `Safebooru`。
2. 关键词填 `cat` 或 `original`。
3. 数量填 `30`，保存路径选好。
4. Cookie 与 AI 过滤对 Safebooru 不生效（全年龄站，无需 R18/AI 过滤）。
5. 添加任务并开始后，日志出现 `开始采集 Safebooru[匿名]: cat`。

### 示例 3：以登录态拉取更多 R18

1. 在浏览器登录 Pixiv（右上角确认显示用户名）。
2. 打开 DevTools（F12）→ Network → 刷新页面 → 点任意一个发往 `pixiv.net` 的请求 → 查看 Request Headers 里的 `Cookie:` 整行。
3. 复制整串（含 `PHPSESSID=...; device_token=...; cf_clearance=...`）粘贴到 GUI 的 Cookie 框。
4. 源选 `Pixiv`，关键词填 R18 标签，数量按需。
5. 添加任务并开始后，日志应出现 `开始采集 Pixiv[登录态(Cookie) | 屏蔽AI]: ...`，表示登录态已生效。
6. 采集结束日志附 `R18 N 张`，可在保存目录核对实际落盘数。

### 示例 4：暂停与取消

- 底部「全部暂停」：对所有运行中的任务发送暂停信号，已下载文件保留。
- 底部「全部取消」：终止所有任务，清理未完成的临时文件，需重下。
- 单个任务行的「开始」可单独启动某任务。

## 日志与状态解读

| 日志片段 | 含义 |
|----------|------|
| `开始采集 Pixiv[匿名 | 屏蔽AI]: 关键词` | 匿名会话 + 屏蔽 AI 图 |
| `开始采集 Pixiv[登录态(Cookie) | 放行AI]: 关键词` | 登录态 + 放行 AI 图 |
| `Pixiv 检索命中共 N 条, 其中 R18(xRestrict!=0): M 条` | 本次检索命中总数与 R18 张数 |
| `完成 ... R18 N 张` | 任务结束，Pixiv 源附 R18 实际采集张数 |
| `请求重试 2/3: ...` | 第 2 次重试（共 3 次） |

状态栏常驻提示：`pixiv.re 公共代理无 SLA | 匿名搜索数量受限 | R18 放行, 仅屏蔽 AI 图 | 可选 Cookie 拉 R18`。

## 注意事项

### 安全与隐私

- **Cookie 切勿粘贴到聊天/公开场合**：Cookie 等同账号凭证，泄露后他人可冒用你的 Pixiv 会话。如已粘贴，请立即到 Pixiv 退出登录使其失效。
- **Cookie 仅内存持有**：程序不会把 Cookie 写入文件或上传，关闭即清除。
- **跨 IP 重放限制**：Pixiv 的 `cf_clearance` 等挑战令牌按 IP+浏览器指纹绑定，从与浏览器不同 IP 的环境（如远程服务器）重放会被降级为匿名视图。因此登录态是否真正生效，**以你本机运行日志出现 `登录态(Cookie)` 为准**，远程沙盒测试不能作为判据。

### 功能边界与已知限制

- **pixiv.re 公共代理无 SLA**：服务稳定性与可用性不由本项目控制，可能间歇性不可用或限流。
- **匿名搜索数量受限**：未携带 Cookie 时，Pixiv 搜索返回条数有限，不保证精确达到设定数量。
- **R18 实际可得量取决于会话**：匿名仅能命中部分 R18；登录态可见范围更大，但仍受 Pixiv 内容策略与账号设置约束。
- **AI 图占比可能极高**：部分热门 R18 标签 60 条里 59 条为 AI 图，若保持「屏蔽 AI 图」勾选，实际可下载数可能很少——此时取消勾选即可放行。
- **断点续传为轻量级**：已成功下载的文件下次运行同一任务跳过；下载中被取消的部分文件会被清理，需重下。
- **Safebooru 翻页上限 10 页**：防御性限制，防止异常循环。

### 合规

- 本工具为个人学习/收藏用途，请遵守各图站服务条款与所在地法律法规，勿用于批量商业化抓取或侵权传播。
- PySide6 基于 LGPLv3，闭源分发需保留相应版权与许可声明。

## 目录结构

```
动漫图片下载器GUI/
├── main.py            # 完整可运行 PySide6 应用 (单文件)
├── test_logic.py      # 离线逻辑单元测试 (27 项)
├── requirements.txt   # 依赖锁定
└── README.md          # 本说明
```

## 常见问题

**Q：点开始后一直 0 下载 / 数量远少于设定？**
A：多为匿名搜索受限或该标签 AI 图占比过高。先取消「屏蔽 AI 图」勾选重试；若拉 R18 仍少，按示例 3 填入登录态 Cookie。

**Q：日志显示 `匿名` 但我明明填了 Cookie？**
A：Cookie 整串可能来自未真正登录的浏览器会话，或跨 IP 被 Cloudflare 降级。请确认浏览器 Pixiv 右上角显示用户名后重新复制整串。

**Q：能跑在服务器/CI 上吗？**
A：仅能用于「代码可加载」校验（headless 导入），实际采集需要图形界面与可访问 Pixiv 的网络。
