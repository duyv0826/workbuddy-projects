# 动漫图片批量下载器 (GUI)

基于 Python 3.13 + PySide6 的桌面端动漫图片批量下载工具。支持 Pixiv (经 pixiv.re 匿名反向代理) 与 Safebooru 两个来源，内置 SFW 过滤、AI 图屏蔽、断点续传式暂停/取消、下载截断校验。

## 运行环境

- Python 3.13
- Windows / macOS / Linux (PySide6 跨平台, LGPLv3 允许闭源分发)

## 安装与运行

```bash
pip install -r requirements.txt
python main.py
```

依赖:

- PySide6==6.9.3 (GUI 框架)
- requests>=2.31 (HTTP 客户端)
- Pillow>=10.2 (图片截断校验)

## 功能说明

### 1. 多源配置
- 源下拉框: Pixiv / Safebooru
- 关键词输入: 标签名 (如 `初音ミク`)
- 数量: 单次任务需要采集的图片数量 (1-500)
- 保存路径: 点击"浏览"选择本地目录

### 2. 任务队列
- 表格展示: 任务名 / 源 / 进度条 / 状态 / 操作
- 操作列"开始"可单独启动某个任务
- 底部全局控制: 开始 / 全部暂停 / 全部取消
- 并发上限 5, 超出时提示等待

### 3. 采集与过滤
- Pixiv:
  - 经 pixiv.re 公共代理直连, 无需 cookie
  - 搜索 API: `https://pixiv.net/ajax/search/artworks/{tag}?word={tag}`
  - 原图下载: `https://pixiv.re/{id}.png` (单发 + sleep 限速避免限流)
  - 过滤: `xRestrict != 0` 剔除 (R18); `aiType == 1` 或 `== 2` 剔除 (AI 图)
- Safebooru:
  - API: `https://safebooru.org/index.php?page=dapi&s=post&q=index&tags={tags}&limit={n}&pid={page}`
  - 返回 XML, 解析 `<post file_url source rating tags>`
  - 全年龄站, 无需 R18 过滤

### 4. 健壮性
- 请求超时 30 秒, 失败自动重试 3 次 (指数退避)
- 截断校验: 下载后用 Pillow 全解码, 捕获异常则删文件 (下次运行可重下, 已存在文件跳过)
- 暂停/取消: 基于 `threading.Event`, 主线程发信号, Worker 协作退出
- 每个任务独立 QThread, 通过 pyqtSignal 回传进度/完成/日志, 主线程仅更新 UI

### 5. 界面
- 深色主题 (bg #0D1117 / surface #161B22 / fg #E6EDF3 / accent #2F81F7)
- 上配置区 + 下任务队列 + 日志区
- 图标全部使用 Qt 内置 `QStyle::SP_*` 标准图标 (无 emoji)
- 最小宽度 880px

## 已知限制

- **pixiv.re 公共代理无 SLA**: 服务稳定性与可用性不由本项目控制, 可能间歇性不可用或限流。
- **匿名搜索数量受限**: 未携带 cookie, Pixiv 搜索返回条数有限, MVP 仅取搜索前 N 条, 不保证精确达到设定数量。
- **无登录态采集**: 无法访问需登录的 R18 内容 (已通过 `xRestrict` 过滤剔除)。
- **断点续传为轻量级**: 已成功下载的文件在下次运行同一任务时跳过; 正在下载中被取消的部分文件 (.part 临时文件) 会被清理, 需重下。
- **Safebooru 翻页上限**: 防御性限制最多翻 10 页, 防止异常循环。

## 目录结构

```
动漫图片下载器GUI/
├── main.py            # 完整可运行 PySide6 应用 (单文件)
├── requirements.txt   # 依赖锁定
└── README.md          # 本说明
```
