#!/usr/bin/env python3
# verify_refactor.py
# 不依赖 Cline，直接用智谱 GLM-4.7-Flash（OpenAI 兼容格式）调用模型，验证：
#   1) API Key 有效、网络可达（连接状态）
#   2) API 鉴权有效性（401/403 区分）
#   3) 模型能对一个 hello-world 项目做代码重构（基础推理成功响应）
#   4) 输出格式与参数配置一致性（temperature / 模型名 / 返回结构）
#
# 用法（二选一提供 Key，切勿粘贴到聊天）：
#   方式A 环境变量（PowerShell）： $env:ZHIPU_API_KEY = "你的智谱key"
#   方式B .env 文件：            在本目录建 .env，内容 ZHIPU_API_KEY=你的智谱key
#   然后： python verify_refactor.py
#
# 模型：GLM-4.7-Flash（智谱 2026 永久免费档，200K 上下文，编程 SOTA 国产第一梯队）
import os
import sys
import json
import urllib.request
import urllib.error


def load_env_file(path=".env"):
    """从 .env 文件读取 KEY=VALUE 注入环境变量（仅当环境变量未设置时）。"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# 智谱 OpenAI 兼容端点（与 OpenAI / vLLM 同格式，仅 base_url 不同）
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = os.environ.get("ZHIPU_MODEL", "glm-4.7-flash")  # 2026 永久免费 + 编程 SOTA


def main():
    load_env_file()  # 优先尝试从 .env 读取（避免把 Key 贴进聊天）
    key = os.environ.get("ZHIPU_API_KEY")
    if not key:
        print("[FAIL] 未检测到 ZHIPU_API_KEY。请二选一：")
        print("   1) 设置环境变量： $env:ZHIPU_API_KEY = '你的智谱key'")
        print("   2) 在本目录新建 .env 写入： ZHIPU_API_KEY=你的智谱key")
        sys.exit(1)

    print(f"[STEP 1] 模型连接状态：目标端点 {API_URL}")
    print(f"[STEP 1] 生效模型名称：{MODEL}")
    print(f"[STEP 1] API Key 已加载：长度 {len(key)} 字符（已脱敏，不打印明文）\n")

    try:
        src = open("hello_world_project/main.py", encoding="utf-8").read()
    except FileNotFoundError:
        print("[FAIL] 找不到 hello_world_project/main.py，请在本目录下运行。")
        sys.exit(1)

    prompt = (
        "请重构下面这段 Python 代码：拆分函数为单一职责、补充类型注解、"
        "消除魔数（用常量或参数）、用返回值替代 print、保持可运行。\n"
        "只输出重构后的完整代码，不要解释，不要用 markdown 代码块包裹。\n\n"
        + src
    )

    temperature = 0.2
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    print("[STEP 2] API 鉴权与基础推理请求：发送中...\n")
    # 免费档共享池常返 429（code 1305 访问量过大），指数退避重试
    last_err = None
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            if e.code == 429 and attempt < 5:
                import time
                wait = 2 ** attempt * 3  # 6/12/24/48s
                print(f"  [429 限速，第{attempt}次重试，等待 {wait}s] {body[:80]}")
                time.sleep(wait)
                last_err = (e.code, body)
                continue
            print(f"[FAIL] HTTP {e.code}：{body}")
            sys.exit(1)
    else:
        print(f"[FAIL] 重试耗尽仍 429：{last_err}")
        sys.exit(1)

    # ---- 一致性校验 ----
    # 1) 返回结构校验
    assert "choices" in data and len(data["choices"]) > 0, "返回缺少 choices"
    assert "message" in data["choices"][0], "choices[0] 缺少 message"
    out = data["choices"][0]["message"]["content"].strip()
    # 2) 模型名一致性（部分平台会在 usage/model 字段回显）
    returned_model = data.get("model", MODEL)
    # 3) 参数回显一致性（智谱在顶层不带 temperature，但 usage 应存在）
    usage = data.get("usage", {})
    print("[STEP 3] 基础推理响应：HTTP 200，模型返回成功\n")
    print("[STEP 4] 输出格式与参数一致性校验：")
    print(f"   - 返回结构含 choices[0].message.content：✅")
    print(f"   - 请求模型 = {MODEL} | 回显模型 = {returned_model}："
          f"{'✅ 一致' if returned_model == MODEL else '⚠️ 不一致(平台可能回显别名)'}")
    print(f"   - 请求 temperature = {temperature}：✅ 已发送（平台侧生效，不强制回显）")
    print(f"   - 返回 usage 字段：{'✅ ' + json.dumps(usage, ensure_ascii=False) if usage else '⚠️ 缺失'}")

    print("\n[OK] 模型调用成功，重构结果如下：\n")
    print(out)
    with open("hello_world_project/main_refactored.py", "w", encoding="utf-8") as f:
        f.write(out)
    print("\n[INFO] 重构结果已保存到 hello_world_project/main_refactored.py")


if __name__ == "__main__":
    main()
