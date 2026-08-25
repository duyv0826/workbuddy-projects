# -*- coding: utf-8 -*-
"""
动漫图片批量下载器 (GUI)
技术栈: Python 3.13 + PySide6 + requests + Pillow
许可: PySide6 (LGPLv3) 允许闭源分发

已知限制:
  - pixiv.re 公共代理无 SLA, 可能不稳定或限流
  - 匿名搜索 (无 cookie) 结果数量受限, MVP 仅取搜索前 N 条
  - 无登录态采集, 匿名搜索仍可命中部分 xRestrict!=0 内容 (R18 不再剔除, 默认放行)
  - 可选 Pixiv 登录态 Cookie: 填入后以登录态检索, 扩大 R18 可见范围 (留空=匿名)
  - 仅屏蔽 AI 图 (aiType==1/2 剔除)

遵守团队 P0 规则: 图标全部使用 Qt 内置 QStyle::SP_* 标准图标,
无 emoji, 无紫粉渐变, 无 AI 模板味占位文案。
"""

import os
import sys
import time
import uuid
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional

import requests
from PySide6.QtCore import (
    Qt, QThread, Signal as pyqtSignal, QObject, QSize, QTimer,
)
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QComboBox, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QLabel, QSpinBox,
    QStatusBar, QMessageBox, QStyle, QProgressBar, QAbstractItemView,
    QPlainTextEdit, QCheckBox,
)

# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------
MAX_CONCURRENT = 5          # 最大并发任务数
REQUEST_TIMEOUT = 30        # 单次请求超时 (秒)
MAX_RETRIES = 3             # 失败重试次数
RETRY_BACKOFF = 2.0         # 重试退避基数 (秒)
PIXIV_RATE_SLEEP = 1.2      # pixiv 单发限速间隔 (秒)
APP_MIN_WIDTH = 880

# 深色主题配色 (bg / surface / fg / accent / success / warn / danger)
COLOR_BG = "#0D1117"
COLOR_SURFACE = "#161B22"
COLOR_FG = "#E6EDF3"
COLOR_ACCENT = "#2F81F7"
COLOR_SUCCESS = "#3FB950"
COLOR_WARN = "#D29922"
COLOR_DANGER = "#F85149"
COLOR_BORDER = "#30363D"


# ---------------------------------------------------------------------------
# 数据源枚举
# ---------------------------------------------------------------------------
class Source:
    PIXIV = "Pixiv"
    SAFEBOORU = "Safebooru"


# ---------------------------------------------------------------------------
# 过滤逻辑 (纯函数, 可独立单元测试, 不依赖网络)
# ---------------------------------------------------------------------------
def pixiv_is_allowed(item: Dict, block_ai: bool = True) -> bool:
    """判断单条 pixiv 搜索结果是否允许下载。

    过滤规则:
      - aiType == 1 或 == 2 -> AI 相关; 当 block_ai=True 时剔除 (屏蔽 AI 图)
    注: R18 (xRestrict!=0) 默认放行, 不再剔除。
    其余放行。
    """
    if not isinstance(item, dict):
        return False
    if not item.get("id"):
        return False
    ai_type = item.get("aiType", 0)
    if block_ai and ai_type in (1, 2):
        return False
    return True


def normalize_pixiv_cookie(raw: str) -> str:
    """规整用户输入的 Cookie 文本。

    规则:
      - 空 -> 空 (匿名)
      - 含 '=' 或 ';' (如 "PHPSESSID=xxx" 或整串请求头) -> 原样透传
      - 纯裸值 (无 '=' 无 ';', 即用户只粘了 PHPSESSID 的值本身)
        -> 自动补 "PHPSESSID=" 前缀, 避免手滑导致 cookie 失效
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    if "=" in raw or ";" in raw:
        return raw
    return f"PHPSESSID={raw}"


def pixiv_session_headers(cookie: str = "") -> Dict[str, str]:
    """构造 Pixiv 请求会话头。

    cookie 非空时附加登录态 Cookie (PHPSESSID 等), 用于扩大 R18 检索范围;
    留空则维持匿名会话 (仅能命中部分 R18)。Referer 为 Pixiv 搜索 API 常规要求。
    cookie 文本会先经 normalize_pixiv_cookie 规整。
    """
    cookie = normalize_pixiv_cookie(cookie)
    headers: Dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Referer": "https://www.pixiv.net/",
    }
    if cookie:
        headers["Cookie"] = cookie
    return headers


def parse_safebooru_xml(xml_text: str) -> List[Dict]:
    """解析 Safebooru DAPI 返回的 XML, 提取 post 列表。

    返回结构: [{"file_url", "source", "rating", "tags"}, ...]
    Safebooru 为全年龄站, 无需 R18 过滤。
    """
    results: List[Dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return results
    for post in root.findall("post"):
        file_url = post.get("file_url")
        if not file_url:
            continue
        results.append({
            "file_url": file_url,
            "source": post.get("source", "") or "",
            "rating": post.get("rating", "") or "",
            "tags": post.get("tags", "") or "",
        })
    return results


def safebooru_is_allowed(post: Dict) -> bool:
    """Safebooru 全年龄, 默认全部放行; 保留接口便于扩展。"""
    if not isinstance(post, dict):
        return False
    if not post.get("file_url"):
        return False
    return True


# ---------------------------------------------------------------------------
# 任务模型
# ---------------------------------------------------------------------------
@dataclass
class DownloadTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    source: str = Source.PIXIV
    keyword: str = ""
    count: int = 20
    save_path: str = ""
    cookie: str = ""              # 可选 Pixiv 登录态 Cookie (仅 Pixiv 源用于 R18 检索)
    block_ai: bool = True         # 是否屏蔽 AI 图 (aiType 1/2); False=放行 AI 图
    r18_hits: int = 0             # Pixiv 采集时命中的 R18(xRestrict!=0) 张数 (统计用)
    status: str = "等待中"          # 等待中/采集中/下载中/已暂停/已完成/已取消/出错
    progress: int = 0              # 0-100
    total: int = 0
    done: int = 0
    message: str = ""
    worker: Optional["DownloadWorker"] = None


# ---------------------------------------------------------------------------
# 下载工作线程
# ---------------------------------------------------------------------------
class DownloadWorker(QThread):
    """每个下载任务一个 QThread。

    信号:
      progress_signal(task_id, done, total, percent)
      finished_signal(task_id, ok, message)
      log_signal(task_id, text)
    """

    progress_signal = pyqtSignal(str, int, int, int)
    finished_signal = pyqtSignal(str, bool, str)
    log_signal = pyqtSignal(str, str)

    def __init__(self, task: DownloadTask):
        super().__init__()
        self.task = task
        self._pause_event = threading.Event()
        self._pause_event.set()           # 未暂停
        self._cancel_event = threading.Event()  # 取消标志
        self._session = requests.Session()
        self._session.headers.update(pixiv_session_headers(self.task.cookie))

    # ---- 控制接口 (主线程调用) ----
    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def cancel(self):
        self._cancel_event.set()
        self._pause_event.set()  # 解除暂停阻塞以便尽快退出

    # ---- 内部工具 ----
    def _check_pause(self):
        """阻塞直到恢复或取消。返回 True 表示应取消。"""
        while not self._pause_event.is_set():
            if self._cancel_event.is_set():
                return True
            time.sleep(0.2)
        return self._cancel_event.is_set()

    def _http_get(self, url: str, stream: bool = False, **kwargs):
        """带重试的 HTTP GET。返回 requests.Response 或 None(取消)。"""
        last_err = ""
        for attempt in range(1, MAX_RETRIES + 1):
            if self._cancel_event.is_set():
                return None
            try:
                resp = self._session.get(
                    url, timeout=REQUEST_TIMEOUT, stream=stream, **kwargs
                )
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                last_err = str(e)
                self.log_signal.emit(self.task.task_id, f"请求重试 {attempt}/{MAX_RETRIES}: {e}")
                time.sleep(RETRY_BACKOFF * attempt)
        self.log_signal.emit(self.task.task_id, f"请求最终失败: {last_err}")
        return None

    def _download_one(self, url: str, dest: str) -> bool:
        """下载单张图片并做截断校验。失败返回 False。"""
        resp = self._http_get(url, stream=True)
        if resp is None:
            return False
        tmp = dest + ".part"
        try:
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if self._cancel_event.is_set():
                        return False
                    if chunk:
                        f.write(chunk)
            # 截断校验: 全解码, 捕获异常则删文件
            from PIL import Image
            try:
                with Image.open(tmp) as im:
                    im.load()  # 触发完整解码
            except Exception:
                if os.path.exists(tmp):
                    os.remove(tmp)
                self.log_signal.emit(self.task.task_id, f"图片损坏/截断, 已删除: {os.path.basename(dest)}")
                return False
            os.replace(tmp, dest)
            return True
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            self.log_signal.emit(self.task.task_id, f"下载异常: {e}")
            return False

    # ---- 采集逻辑 ----
    def _collect_pixiv(self) -> List[Dict]:
        """通过 pixiv.re 匿名反向代理采集搜索结果。"""
        items: List[Dict] = []
        tag = self.task.keyword.strip()
        if not tag:
            return items
        api = f"https://pixiv.net/ajax/search/artworks/{tag}"
        params = {"word": tag}
        resp = self._http_get(api, params=params)
        if resp is None:
            return items
        try:
            data = resp.json()
        except ValueError:
            self.log_signal.emit(self.task.task_id, "Pixiv 响应非 JSON")
            return items
        illusts = (
            data.get("body", {})
            .get("illustManga", {})
            .get("data", [])
        )
        r18_count = 0
        for it in illusts:
            if self._cancel_event.is_set():
                break
            if not pixiv_is_allowed(it, self.task.block_ai):
                continue
            pid = it.get("id")
            if not pid:
                continue
            x_restrict = it.get("xRestrict", 0)
            if x_restrict not in (0, None):
                r18_count += 1
            items.append({
                "id": pid,
                "title": it.get("title", str(pid)),
                "user": it.get("userName", "unknown"),
                "url": f"https://pixiv.re/{pid}.png",
            })
            if len(items) >= self.task.count:
                break
        self.task.r18_hits = r18_count
        self.log_signal.emit(
            self.task.task_id, f"Pixiv 检索命中共 {len(items)} 条, 其中 R18(xRestrict!=0): {r18_count} 条"
        )
        return items

    def _collect_safebooru(self) -> List[Dict]:
        """采集 Safebooru, 翻页直到满足数量。"""
        items: List[Dict] = []
        tags = self.task.keyword.strip().replace(" ", "+")
        page = 0
        per_page = min(100, max(1, self.task.count))
        while len(items) < self.task.count:
            if self._cancel_event.is_set():
                break
            api = "https://safebooru.org/index.php"
            params = {
                "page": "dapi",
                "s": "post",
                "q": "index",
                "tags": tags,
                "limit": per_page,
                "pid": page,
            }
            resp = self._http_get(api, params=params)
            if resp is None:
                break
            posts = parse_safebooru_xml(resp.text)
            if not posts:
                break
            for p in posts:
                if self._cancel_event.is_set():
                    break
                if not safebooru_is_allowed(p):
                    continue
                items.append(p)
                if len(items) >= self.task.count:
                    break
            page += 1
            if page >= 10:  # 防御性上限
                break
            time.sleep(0.5)
        return items[: self.task.count]

    # ---- 主运行 ----
    def run(self):
        tid = self.task.task_id
        try:
            self.task.status = "采集中"
            mode = "登录态(Cookie)" if (self.task.source == Source.PIXIV and self.task.cookie) else "匿名"
            ai_mode = ""
            if self.task.source == Source.PIXIV:
                ai_mode = " | 屏蔽AI" if self.task.block_ai else " | 放行AI"
            self.log_signal.emit(tid, f"开始采集 {self.task.source}[{mode}{ai_mode}]: {self.task.keyword}")
            if self.task.source == Source.PIXIV:
                entries = self._collect_pixiv()
            else:
                entries = self._collect_safebooru()

            if self._cancel_event.is_set():
                self.finished_signal.emit(tid, False, "已取消")
                return

            total = len(entries)
            if total == 0:
                self.finished_signal.emit(tid, False, "未获取到任何图片 (可能无结果或已被过滤)")
                return

            self.task.total = total
            self.task.status = "下载中"
            os.makedirs(self.task.save_path, exist_ok=True)

            done = 0
            for idx, entry in enumerate(entries):
                if self._cancel_event.is_set():
                    self.finished_signal.emit(tid, False, "已取消")
                    return
                # 暂停阻塞
                if self._check_pause():
                    self.finished_signal.emit(tid, False, "已取消")
                    return

                if self.task.source == Source.PIXIV:
                    pid = entry["id"]
                    fname = f"{pid}_{idx:04d}.png"
                    url = entry["url"]
                else:
                    furl = entry["file_url"]
                    ext = os.path.splitext(furl.split("?")[0])[1] or ".jpg"
                    safe_tags = self.task.keyword.strip().replace(" ", "_")[:30]
                    fname = f"{safe_tags}_{idx:04d}{ext}"
                    url = furl

                dest = os.path.join(self.task.save_path, fname)
                if os.path.exists(dest):
                    done += 1
                    self._emit_progress(done, total)
                    continue

                ok = self._download_one(url, dest)
                if ok:
                    done += 1
                else:
                    if self._cancel_event.is_set():
                        self.finished_signal.emit(tid, False, "已取消")
                        return
                self._emit_progress(done, total)

                if self.task.source == Source.PIXIV:
                    time.sleep(PIXIV_RATE_SLEEP)  # 单发限速

            self.task.status = "已完成"
            r18_msg = f", R18 {self.task.r18_hits} 张" if self.task.source == Source.PIXIV else ""
            self.finished_signal.emit(tid, True, f"完成 {done}/{total}{r18_msg}")
        except Exception as e:
            self.log_signal.emit(tid, f"致命错误: {e}")
            self.finished_signal.emit(tid, False, f"出错: {e}")

    def _emit_progress(self, done: int, total: int):
        pct = int(done / total * 100) if total else 100
        self.task.done = done
        self.task.total = total
        self.task.progress = pct
        self.progress_signal.emit(self.task.task_id, done, total, pct)


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("动漫图片批量下载器")
        self.setMinimumWidth(APP_MIN_WIDTH)
        self.resize(980, 720)
        self._apply_dark_theme()

        self.tasks: List[DownloadTask] = []
        self._running_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_ui)
        self._timer.start(500)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        root.addWidget(self._build_config_area())
        root.addWidget(self._build_task_area(), stretch=1)
        root.addWidget(self._build_log_area())

        self._build_status_bar()
        self._update_concurrency_buttons()

    # ---- 主题 ----
    def _apply_dark_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {COLOR_BG};
                color: {COLOR_FG};
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
            }}
            QGroupBox {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: {COLOR_FG};
            }}
            QLineEdit, QComboBox, QSpinBox {{
                background-color: {COLOR_BG};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 6px 8px;
                color: {COLOR_FG};
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_FG};
                selection-background-color: {COLOR_ACCENT};
            }}
            QPushButton {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                color: {COLOR_FG};
            }}
            QPushButton:hover {{
                border-color: {COLOR_ACCENT};
            }}
            QPushButton:disabled {{
                color: #6E7681;
            }}
            QTableWidget {{
                background-color: {COLOR_SURFACE};
                gridline-color: {COLOR_BORDER};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                color: {COLOR_FG};
            }}
            QHeaderView::section {{
                background-color: {COLOR_BG};
                border: 1px solid {COLOR_BORDER};
                padding: 6px;
                color: {COLOR_FG};
            }}
            QPlainTextEdit {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                color: {COLOR_FG};
            }}
            QProgressBar {{
                background-color: {COLOR_BG};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                text-align: center;
                color: {COLOR_FG};
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_ACCENT};
                border-radius: 5px;
            }}
            QStatusBar {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_FG};
            }}
        """)

    # ---- 配置区 ----
    def _build_config_area(self) -> QWidget:
        box = QGroupBox("下载配置")
        outer = QVBoxLayout(box)
        outer.setSpacing(10)

        # 第一行: 源 / 关键词 / 数量 / 路径 / 浏览 / 添加
        top = QHBoxLayout()
        top.setSpacing(10)

        # 源
        c_src = QComboBox()
        c_src.addItems([Source.PIXIV, Source.SAFEBOORU])
        c_src.setMinimumWidth(120)
        self.src_combo = c_src

        # 关键词
        kw = QLineEdit()
        kw.setPlaceholderText("输入标签 / 关键词, 例如: 初音ミク")
        kw.setMinimumWidth(180)
        self.keyword_edit = kw

        # 数量
        cnt = QSpinBox()
        cnt.setRange(1, 500)
        cnt.setValue(20)
        self.count_spin = cnt

        # 保存路径
        path = QLineEdit()
        path.setPlaceholderText("选择保存目录")
        path.setMinimumWidth(160)
        self.path_edit = path
        browse = QPushButton(self.style().standardIcon(QStyle.SP_DirOpenIcon), "浏览")
        browse.clicked.connect(self._on_browse)

        # 添加按钮
        add_btn = QPushButton(self.style().standardIcon(QStyle.SP_FileDialogNewFolder), "添加任务")
        add_btn.clicked.connect(self._on_add_task)

        top.addWidget(QLabel("源:"))
        top.addWidget(c_src)
        top.addWidget(QLabel("关键词:"))
        top.addWidget(kw, stretch=1)
        top.addWidget(QLabel("数量:"))
        top.addWidget(cnt)
        top.addWidget(path)
        top.addWidget(browse)
        top.addWidget(add_btn)
        outer.addLayout(top)

        # 第二行: 可选 Pixiv 登录态 Cookie (仅 Pixiv 源生效, 留空=匿名)
        cookie_row = QHBoxLayout()
        cookie_row.setSpacing(10)
        ck = QLineEdit()
        ck.setPlaceholderText(
            "Pixiv 登录态 Cookie (可选, 仅 Pixiv 源生效; 留空=匿名, R18 仅命中部分)"
        )
        ck.setMinimumWidth(300)
        self.cookie_edit = ck
        cookie_row.addWidget(QLabel("Cookie:"))
        cookie_row.addWidget(ck, stretch=1)
        outer.addLayout(cookie_row)

        # 第三行: 选项 (屏蔽 AI 图 开关)
        opt_row = QHBoxLayout()
        opt_row.setSpacing(10)
        block_ai_chk = QCheckBox("屏蔽 AI 图 (aiType 1/2)")
        block_ai_chk.setChecked(True)   # 默认屏蔽, 与历史行为一致
        self.block_ai_check = block_ai_chk
        opt_row.addWidget(block_ai_chk)
        opt_row.addStretch(1)
        outer.addLayout(opt_row)
        return box

    # ---- 任务列表区 ----
    def _build_task_area(self) -> QWidget:
        box = QGroupBox("任务队列")
        v = QVBoxLayout(box)
        v.setSpacing(8)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["任务名", "源", "进度", "状态", "操作", ""]
        )
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 0)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        v.addWidget(self.table)

        # 全局控制条
        ctrl = QHBoxLayout()
        self.start_btn = QPushButton(self.style().standardIcon(QStyle.SP_MediaPlay), "开始")
        self.pause_btn = QPushButton(self.style().standardIcon(QStyle.SP_MediaPause), "全部暂停")
        self.cancel_btn = QPushButton(self.style().standardIcon(QStyle.SP_DialogCancelButton), "全部取消")
        self.start_btn.clicked.connect(self._on_start_all)
        self.pause_btn.clicked.connect(self._on_pause_all)
        self.cancel_btn.clicked.connect(self._on_cancel_all)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        ctrl.addWidget(self.start_btn)
        ctrl.addWidget(self.pause_btn)
        ctrl.addWidget(self.cancel_btn)
        ctrl.addStretch(1)
        self.concurrency_label = QLabel(f"并发: 0/{MAX_CONCURRENT}")
        ctrl.addWidget(self.concurrency_label)
        v.addLayout(ctrl)
        return box

    # ---- 日志区 ----
    def _build_log_area(self) -> QWidget:
        box = QGroupBox("运行日志")
        v = QVBoxLayout(box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        v.addWidget(self.log_view)
        return box

    def _build_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.status_label = QLabel(
            "pixiv.re 公共代理无 SLA | 匿名搜索数量受限 | R18 放行, 仅屏蔽 AI 图 | 可选 Cookie 拉 R18"
        )
        sb.addWidget(self.status_label)

    # ---- 事件 ----
    def _on_browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if d:
            self.path_edit.setText(d)

    def _on_add_task(self):
        src = self.src_combo.currentText()
        kw = self.keyword_edit.text().strip()
        if not kw:
            QMessageBox.warning(self, "提示", "请填写关键词")
            return
        path = self.path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "提示", "请选择保存路径")
            return
        task = DownloadTask(
            name=f"{kw}-{src}",
            source=src,
            keyword=kw,
            count=self.count_spin.value(),
            save_path=path,
            cookie=self.cookie_edit.text().strip(),
            block_ai=self.block_ai_check.isChecked(),
        )
        self.tasks.append(task)
        self._append_table_row(task)
        self._log(f"已添加任务: {task.name}")

    def _append_table_row(self, task: DownloadTask):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(task.name))
        self.table.setItem(row, 1, QTableWidgetItem(task.source))
        pb = QProgressBar()
        pb.setValue(0)
        self.table.setCellWidget(row, 2, pb)
        self.table.setItem(row, 3, QTableWidgetItem(task.status))

        op = QPushButton(self.style().standardIcon(QStyle.SP_MediaPlay), "开始")
        op.clicked.connect(lambda _=False, t=task: self._on_start_one(t))
        self.table.setCellWidget(row, 4, op)
        # 隐藏第 6 列占位 (用于存 task_id 映射)
        self.table.setItem(row, 5, QTableWidgetItem(task.task_id))

    def _row_of_task(self, task_id: str) -> int:
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 5)
            if item and item.text() == task_id:
                return r
        return -1

    def _on_start_one(self, task: DownloadTask):
        if task.worker and task.worker.isRunning():
            return
        if self._running_count >= MAX_CONCURRENT:
            QMessageBox.information(self, "提示", f"并发已达上限 ({MAX_CONCURRENT}), 请等待其他任务完成")
            return
        self._start_worker(task)

    def _on_start_all(self):
        pending = [t for t in self.tasks if t.status in ("等待中", "已暂停", "出错")]
        for t in pending:
            if self._running_count >= MAX_CONCURRENT:
                break
            self._start_worker(t)
        self._update_concurrency_buttons()

    def _start_worker(self, task: DownloadTask):
        worker = DownloadWorker(task)
        task.worker = worker
        worker.progress_signal.connect(self._on_progress)
        worker.finished_signal.connect(self._on_finished)
        worker.log_signal.connect(self._on_log)
        worker.start()
        self._running_count += 1
        task.status = "采集中"
        self._log(f"启动任务: {task.name}")

    def _on_pause_all(self):
        for t in self.tasks:
            if t.worker and t.worker.isRunning() and t.status != "已暂停":
                t.worker.pause()
                t.status = "已暂停"
        self._log("已暂停全部运行中的任务")

    def _on_cancel_all(self):
        for t in self.tasks:
            if t.worker and t.worker.isRunning():
                t.worker.cancel()
        self._log("已发送取消信号给全部任务")

    def _on_progress(self, task_id, done, total, pct):
        row = self._row_of_task(task_id)
        if row < 0:
            return
        pb = self.table.cellWidget(row, 2)
        if isinstance(pb, QProgressBar):
            pb.setValue(pct)
        self.table.setItem(row, 3, QTableWidgetItem(f"下载中 {done}/{total}"))

    def _on_finished(self, task_id, ok, message):
        row = self._row_of_task(task_id)
        task = next((t for t in self.tasks if t.task_id == task_id), None)
        if task:
            task.status = "已完成" if ok else ("已取消" if "取消" in message else "出错")
            self._running_count = max(0, self._running_count - 1)
        if row >= 0:
            pb = self.table.cellWidget(row, 2)
            if isinstance(pb, QProgressBar) and ok:
                pb.setValue(100)
            self.table.setItem(row, 3, QTableWidgetItem(task.status if task else message))
        self._log(f"任务结束 [{task_id[:6]}]: {message}")
        self._update_concurrency_buttons()

    def _on_log(self, task_id, text):
        self._log(f"[{task_id[:6]}] {text}")

    def _log(self, text: str):
        self.log_view.appendPlainText(text)

    def _refresh_ui(self):
        self.concurrency_label.setText(f"并发: {self._running_count}/{MAX_CONCURRENT}")
        self._update_concurrency_buttons()

    def _update_concurrency_buttons(self):
        any_running = any(t.worker and t.worker.isRunning() for t in self.tasks)
        self.pause_btn.setEnabled(any_running)
        self.cancel_btn.setEnabled(any_running)
        self.start_btn.setEnabled(self._running_count < MAX_CONCURRENT)

    def closeEvent(self, event):
        for t in self.tasks:
            if t.worker and t.worker.isRunning():
                t.worker.cancel()
                t.worker.wait(2000)
        event.accept()


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("动漫图片批量下载器")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
