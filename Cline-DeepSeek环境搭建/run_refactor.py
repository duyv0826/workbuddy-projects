#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_refactor.py — 智谱 GLM-4.7-Flash 代码重构工具（单文件开箱即用版）
====================================================================

用途：
    调用智谱开放平台 GLM-4.7-Flash（永久免费档）对一段 Python 代码做重构，
    将模型返回的重构结果落盘到指定文件，并输出结构化验证报告。

特性：
    - 从 .env 或环境变量读取 ZHIPU_API_KEY（不硬编码、不进日志明文）
    - OpenAI 兼容格式，端点 https://open.bigmodel.cn/api/paas/v4
    - 429 共享池限速自动指数退避重试（6/12/24/48s，最多 6 次）
    - 鉴权失败（401）/ 权限不足（403）明确提示
    - 返回结构、模型名一致性、usage 字段完整性校验
    - CLI 参数：--source / --output / --model / --temperature

用法：
    # 默认重构 hello_world_project/main.py -> main_refactored.py
    python run_refactor.py

    # 指定源与目标
    python run_refactor.py --source foo.py --output foo_refactored.py

    # 换模型（需账号有权限）
    python run_refactor.py --model glm-4.7-flash

依赖：Python 3.10+，仅用标准库（urllib / json / os / time / argparse / sys）。
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

# ----------------------------- 配置常量（规则层，非选型层） -----------------------------
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DEFAULT_MODEL = "glm-4.7-flash"
DEFAULT_SOURCE = "hello_world_project/main.py"
DEFAULT_OUTPUT = "hello_world_project/main_refactored.py"
TEMPERATURE = 0.2
MAX_RETRIES = 6
RETRY_BASE_WAIT = 6  # 秒，指数退避：6,12,24,48,48,48
REQUEST_TIMEOUT = 90  # 秒

# 重构系统提示：约束模型只输出干净代码，避免 markdown 包裹
REFACTOR_INSTRUCTION = (
    "请重构下面这段 Python 代码，要求：\n"
    "1. 拆分函数为单一职责，命名清晰\n"
    "2. 补充类型注解（typing）\n"
    "3. 消除魔数，提取为具名常量\n"
    "4. 用返回值替代 print，保持可运行\n"
    "5. 添加必要的 docstring 和 __main__ 入口\n"
    "只输出重构后的完整 Python 代码，不要任何解释文字，"
    "不要用 markdown 代码块（```）包裹。\n\n"
)

SYSTEM_PROMPT = "你是一名资深的 Python 代码重构专家，输出必须是可以直接运行的干净代码。"


def load_env_file(path=".env"):
    """从 .env 文件加载键值到 os.environ（不覆盖已存在的环境变量）。"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def get_api_key():
    """优先环境变量，其次 .env；返回脱敏状态用于日志。"""
    key = os.environ.get("ZHIPU_API_KEY")
    if not key:
        load_env_file(".env")
        key = os.environ.get("ZHIPU_API_KEY")
    return key


def mask_key(key):
    """脱敏显示 Key，避免明文泄漏。"""
    if not key:
        return "(EMPTY)"
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:6]}...{key[-4:]}"


def send_request(payload, api_key):
    """
    发送一次请求，返回 (data, None) 或 (None, error_dict)。
    error_dict: {"type": "http"|"other", "code": int, "body": str, "exc": str}
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(
        API_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.load(resp), None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        return None, {"type": "http", "code": e.code, "body": body, "exc": str(e)}
    except Exception as e:  # 网络异常、超时等
        return None, {"type": "other", "code": 0, "body": "", "exc": str(e)}


def call_with_retry(payload, api_key):
    """带 429 指数退避重试的调用循环，返回 (data, error)。"""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        data, err = send_request(payload, api_key)
        if data is not None:
            return data, None
        last_err = err
        if err["type"] == "http" and err["code"] == 429 and attempt < MAX_RETRIES:
            wait = min(RETRY_BASE_WAIT * (2 ** (attempt - 1)), 48)
            print(f"  [429] 免费档限速，第 {attempt} 次重试，等待 {wait}s ...", flush=True)
            time.sleep(wait)
            continue
        # 非 429 或重试耗尽，直接返回错误
        return None, err
    return None, last_err


def refactor(source_path, output_path, model, temperature):
    """主流程：读源 -> 调模型 -> 校验 -> 落盘 -> 报告。"""
    print("=" * 64)
    print("智谱 GLM-4.7-Flash 代码重构工具")
    print("=" * 64)

    # STEP 0: 前置检查
    if not os.path.exists(source_path):
        print(f"[FAIL] 源文件不存在：{source_path}")
        sys.exit(1)
    api_key = get_api_key()
    print(f"[STEP 0] 前置检查：")
    print(f"   - 源文件：{source_path} ✅")
    print(f"   - API Key：{'✅ ' + mask_key(api_key) if api_key else '❌ 未检测到（请设置 ZHIPU_API_KEY 或写 .env）'}")
    if not api_key:
        sys.exit(1)

    # STEP 1: 读取源
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            source_code = f.read()
    except Exception as e:
        print(f"[FAIL] 读取源文件失败：{e}")
        sys.exit(1)
    print(f"[STEP 1] 已读取源文件（{len(source_code)} 字符）")

    # STEP 2: 发起请求
    print(f"[STEP 2] 调用模型 {model}（temperature={temperature}）...")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": REFACTOR_INSTRUCTION + source_code},
        ],
        "temperature": temperature,
    }
    data, err = call_with_retry(payload, api_key)
    if err is not None:
        code = err["code"]
        body = err["body"]
        print(f"[FAIL] 调用失败（HTTP {code}）：{body[:300]}")
        if code == 401:
            print("   -> 鉴权失败：Key 无效或过期，检查 ZHIPU_API_KEY。")
        elif code == 403:
            print("   -> 权限不足：该 Key 无此模型调用权限。")
        elif code == 429:
            print("   -> 免费档持续限速，请稍后重试或更换时段。")
        sys.exit(1)

    # STEP 3: 一致性校验
    print("[STEP 3] 响应一致性校验：")
    out = None
    try:
        assert "choices" in data and len(data["choices"]) > 0, "返回缺少 choices"
        assert "message" in data["choices"][0], "choices[0] 缺少 message"
        out = data["choices"][0]["message"]["content"].strip()
        assert out, "模型返回内容为空"
    except AssertionError as e:
        print(f"[FAIL] 结构校验未通过：{e}")
        sys.exit(1)

    returned_model = data.get("model", model)
    usage = data.get("usage", {})
    print(f"   - choices[0].message.content 存在：✅")
    print(f"   - 请求模型 = {model} | 回显模型 = {returned_model}："
          f"{'✅ 一致' if returned_model == model else '⚠️ 不一致（平台回显别名）'}")
    print(f"   - usage 字段：{'✅ ' + json.dumps(usage, ensure_ascii=False) if usage else '⚠️ 缺失'}")

    # STEP 4: 落盘
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"[STEP 4] 重构结果已保存：{output_path}（{len(out)} 字符）")
    except Exception as e:
        print(f"[FAIL] 写入失败：{e}")
        sys.exit(1)

    print("\n" + "=" * 64)
    print("[OK] 重构完成，前 600 字符预览：")
    print("-" * 64)
    print(out[:600])
    print("=" * 64)
    return out


def main():
    parser = argparse.ArgumentParser(
        description="智谱 GLM-4.7-Flash 代码重构工具（单文件开箱即用）"
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="源 Python 文件路径")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="重构结果输出路径")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名（默认 glm-4.7-flash）")
    parser.add_argument("--temperature", type=float, default=TEMPERATURE, help="采样温度")
    args = parser.parse_args()

    refactor(args.source, args.output, args.model, args.temperature)


if __name__ == "__main__":
    main()
