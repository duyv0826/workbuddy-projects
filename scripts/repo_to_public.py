#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
私有仓库转公开 SOP 自动化脚本（仓库运维工具）

按 SOP-代码提交与开源发布流程.md 的「私有转公开检查清单」实现可重复、安全的转换流程：
  步骤1  验证仓库存在性与所有权（需 admin 权限）
  步骤2  执行 SOP 预检清单（敏感信息 / 许可证 / README / 第三方版权内容）
  步骤3  备份仓库相关配置（设置 / 分支 / 协作者 / 文件树）到本地
  步骤4  操作确认门禁（默认 dry-run；真实执行需 --execute + 显式确认）
  步骤5  调用平台 API 取消私有属性（visibility=public）
  步骤6  校验可见性并说明访问权限范围
  步骤7  记录操作日志并输出结果状态

安全设计（务必保留）：
  - 默认 dry-run，绝不静默公开；
  - 真实执行需 --execute 且必须显式确认（交互输入 'PUBLISH' 或 --confirm-token PUBLISH）；
  - 预检存在 FAIL 或 BLOCK 项直接中止，不匹配则拒绝发布；
  - 不记录任何凭证，仅依赖已登录的 gh CLI；
  - 幂等：已公开则视为成功并无操作。

用法示例：
  # 仅预检 + 备份（安全，不改变可见性）
  python scripts/repo_to_public.py --repo duyv0826/workbuddy-projects

  # 真实公开（需显式确认；第三方版权图片未处理会被 BLOCK 拦截）
  python scripts/repo_to_public.py --repo duyv0826/workbuddy-projects --execute --confirm-token PUBLISH --confirm-thirdparty
"""
import argparse
import datetime as _dt
import json
import os
import subprocess
import sys

EXIT_OK = 0
EXIT_PREFLIGHT = 10
EXIT_EXECUTE = 20
EXIT_AUTH = 40
EXIT_USAGE = 30

CONFIRM_WORD = "PUBLISH"
# 敏感文件片段：命中即视为应被忽略却已入库
SENSITIVE_PATTERNS = (".env", ".workbuddy", "__pycache__", ".key", "id_rsa",
                      "credentials", "secret", ".pem")
# 第三方版权图片扩展名：公开前须移除或确认授权
THIRDPARTY_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def log(msg, level="INFO"):
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    return line


def run_gh(args, check=True):
    """调用 gh CLI，返回 (returncode, stdout, stderr)。"""
    cmd = ["gh"] + args
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        log("未找到 gh 命令，请先安装 GitHub CLI 并登录（gh auth login）。", "ERROR")
        sys.exit(EXIT_USAGE)
    if check and p.returncode != 0:
        log(f"gh 命令失败: {' '.join(cmd)}\nSTDERR: {p.stderr.strip()}", "ERROR")
    return p.returncode, p.stdout, p.stderr


def gh_api_json(path, method="GET", fields=None):
    args = ["api", "-X", method, path, "--jq", "."] if method != "GET" else ["api", path, "--jq", "."]
    if fields:
        for k, v in fields.items():
            args += ["-f", f"{k}={v}"]
    rc, out, err = run_gh(args, check=False)
    if rc != 0:
        return None, err
    try:
        return json.loads(out), None
    except json.JSONDecodeError:
        return None, f"无法解析 JSON: {out[:200]}"


def get_current_user():
    data, err = gh_api_json("user")
    if not data:
        log(f"获取当前登录用户失败: {err}", "ERROR")
        sys.exit(EXIT_AUTH)
    return data.get("login")


def fetch_repo(repo):
    return gh_api_json(f"repos/{repo}")


def verify_repo(repo):
    log(f"步骤1/7 验证仓库存在性与所有权: {repo}")
    data, err = fetch_repo(repo)
    if not data:
        log(f"仓库不存在或无权访问: {repo}\n{err}", "ERROR")
        sys.exit(EXIT_AUTH)
    owner = data.get("owner", {}).get("login")
    perms = data.get("permissions", {})
    visibility = "private" if data.get("private") else "public"
    log(f"  仓库: {data.get('full_name')}  当前可见性: {visibility}")
    log(f"  owner: {owner}  admin 权限: {perms.get('admin')}")
    return data, owner, visibility, perms


def preflight(repo, repo_info, args):
    log("步骤2/7 执行 SOP 预检清单")
    results = []
    if not repo_info.get("private"):
        results.append(("当前可见性", "PASS", "仓库已为公开，无需转换（幂等）"))
    else:
        results.append(("当前可见性", "PASS", "仓库为私有，符合转换前提"))

    lic = repo_info.get("license")
    results.append(("许可证", "PASS" if lic else "WARN",
                    f"已声明许可证: {lic.get('spdx_id')}" if lic else "未检测到 LICENSE（建议先添加，参见 SOP）"))

    tree, err = gh_api_json(f"repos/{repo}/git/trees/HEAD?recursive=1")
    tracked = []
    if tree and "tree" in tree:
        tracked = [t["path"] for t in tree["tree"] if t.get("type") == "blob"]
    else:
        results.append(("文件树", "WARN", f"无法获取文件树（仅本地校验跳过）: {err}"))

    sens = [p for p in tracked if any(seg in p.lower() for seg in SENSITIVE_PATTERNS)]
    results.append(("敏感文件", "FAIL" if sens else "PASS",
                    ("发现应被忽略的敏感文件已入库: " + ", ".join(sens[:10])) if sens
                    else "未发现 .env/.workbuddy/密钥等敏感文件被跟踪"))

    has_readme = any(p.lower().startswith("readme") for p in tracked)
    results.append(("README", "PASS" if has_readme else "WARN",
                    "存在 README" if has_readme else "未找到 README（建议补充）"))

    third = [p for p in tracked if p.lower().endswith(THIRDPARTY_EXT)]
    if third and not args.confirm_thirdparty:
        results.append(("第三方版权内容", "BLOCK",
                        f"发现 {len(third)} 个图片文件（第三方版权，MIT 不覆盖），公开前须移除或确认授权。例: {third[0]}"))
    elif third and args.confirm_thirdparty:
        results.append(("第三方版权内容", "WARN", f"用户已确认授权/已处理 {len(third)} 个图片文件"))
    else:
        results.append(("第三方版权内容", "PASS", "未发现需特别授权的第三方图片内容"))
    return results


def backup_config(repo, repo_info, backup_dir):
    log(f"步骤3/7 备份仓库配置 -> {backup_dir}")
    os.makedirs(backup_dir, exist_ok=True)
    with open(os.path.join(backup_dir, "repo_settings.json"), "w", encoding="utf-8") as f:
        json.dump(repo_info, f, ensure_ascii=False, indent=2)
    branches, _ = gh_api_json(f"repos/{repo}/branches")
    if branches:
        with open(os.path.join(backup_dir, "branches.json"), "w", encoding="utf-8") as f:
            json.dump([b.get("name") for b in branches], f, ensure_ascii=False, indent=2)
    collab, _ = gh_api_json(f"repos/{repo}/collaborators")
    if collab:
        with open(os.path.join(backup_dir, "collaborators.json"), "w", encoding="utf-8") as f:
            json.dump([{"login": c.get("login"), "permission": c.get("permission")} for c in collab],
                      f, ensure_ascii=False, indent=2)
    tree, _ = gh_api_json(f"repos/{repo}/git/trees/HEAD?recursive=1")
    if tree and "tree" in tree:
        with open(os.path.join(backup_dir, "tracked_files.txt"), "w", encoding="utf-8") as f:
            for t in tree["tree"]:
                f.write(t.get("path", "") + "\n")
    log(f"  备份完成: {os.listdir(backup_dir)}")


def confirm_execute(repo, args):
    if not args.execute:
        log("步骤4/7 确认门禁: 当前为 DRY-RUN（未加 --execute），不执行可见性变更。", "WARN")
        return False
    log("步骤4/7 确认门禁: 即将把仓库设为公开。", "WARN")
    if args.confirm_token == CONFIRM_WORD:
        log("  已通过 --confirm-token 确认。")
        return True
    if sys.stdin.isatty():
        try:
            ans = input(f"  请输入确认词 '{CONFIRM_WORD}' 以继续执行（其他输入取消）: ").strip()
        except EOFError:
            ans = ""
        if ans == CONFIRM_WORD:
            return True
        log("  确认词不匹配，已取消。", "ERROR")
        sys.exit(EXIT_USAGE)
    else:
        log("  非交互环境且未提供 --confirm-token PUBLISH，拒绝执行以避免误公开。", "ERROR")
        sys.exit(EXIT_USAGE)


def flip_visibility(repo):
    log("步骤5/7 调用平台 API 取消私有属性 (visibility=public)")
    _, err = gh_api_json(f"repos/{repo}", method="PATCH", fields={"visibility": "public"})
    if err:
        log(f"  变更可见性失败: {err}", "ERROR")
        sys.exit(EXIT_EXECUTE)
    log("  API 调用返回成功。")


def verify_and_report(repo):
    log("步骤6/7 校验可见性并更新访问权限说明")
    data, err = fetch_repo(repo)
    if data is None:
        log(f"  无法复核仓库状态: {err}", "ERROR")
        sys.exit(EXIT_EXECUTE)
    visibility = "private" if data.get("private") else "public"
    if visibility == "public":
        log("  校验通过: 仓库现已为 PUBLIC。", "OK")
    else:
        log("  校验失败: 仓库仍为 PRIVATE。", "ERROR")
        sys.exit(EXIT_EXECUTE)
    collab, _ = gh_api_json(f"repos/{repo}/collaborators")
    if collab:
        names = ", ".join(c.get("login") for c in collab)
        log(f"  当前协作者({len(collab)}): {names}（公开后代码对所有人可见，协作者权限不受影响）")
    else:
        log("  当前无额外协作者（仅 owner）。")


def write_log_file(backup_dir, lines):
    path = os.path.join(backup_dir, "operation.log")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser(description="私有仓库转公开 SOP 自动化脚本")
    ap.add_argument("--repo", required=True, help="目标仓库标识，格式 OWNER/NAME（必填）")
    ap.add_argument("--execute", action="store_true", help="真实执行可见性变更（默认仅 dry-run 预检+备份）")
    ap.add_argument("--confirm-token", default="", help="非交互确认令牌，须等于 PUBLISH")
    ap.add_argument("--confirm-thirdparty", action="store_true",
                    help="确认已处理/授权第三方版权图片（解除 BLOCK 项）")
    ap.add_argument("--backup-dir", default="./repo_to_public_backup", help="配置备份目录")
    args = ap.parse_args()

    start_ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(args.backup_dir, f"{args.repo.replace('/', '_')}_{start_ts}")
    log_lines = []

    def L(msg, level="INFO"):
        log_lines.append(log(msg, level))

    L(f"=== 私有仓库转公开 SOP 开始 === repo={args.repo} execute={args.execute}")
    current_user = get_current_user()
    L(f"当前登录用户: {current_user}")
    repo_info, owner, visibility, perms = verify_repo(args.repo)
    if current_user != owner and not perms.get("admin"):
        L(f"当前用户 {current_user} 非 owner({owner}) 且无 admin 权限，拒绝操作。", "ERROR")
        sys.exit(EXIT_AUTH)
    L("所有权/权限校验通过。")

    results = preflight(args.repo, repo_info, args)
    for name, status, detail in results:
        L(f"  [{status}] {name}: {detail}")
    statuses = [s for _, s, _ in results]
    if "FAIL" in statuses or "BLOCK" in statuses:
        L("预检存在 FAIL/BLOCK 项，禁止公开。请先解决问题后重试。", "ERROR")
        backup_config(args.repo, repo_info, backup_dir)
        write_log_file(backup_dir, log_lines)
        L(f"已生成预检报告与配置备份: {backup_dir}")
        sys.exit(EXIT_PREFLIGHT)

    backup_config(args.repo, repo_info, backup_dir)

    ok = confirm_execute(args.repo, args)
    if not ok:
        L("DRY-RUN 结束：未改变可见性。配置备份已生成，可安全复查。", "WARN")
        write_log_file(backup_dir, log_lines)
        L(f"备份路径: {backup_dir}")
        sys.exit(EXIT_OK)

    flip_visibility(args.repo)
    verify_and_report(args.repo)
    L("=== 私有仓库转公开 SOP 完成 ===", "OK")
    write_log_file(backup_dir, log_lines)
    L(f"操作日志: {os.path.join(backup_dir, 'operation.log')}")


if __name__ == "__main__":
    main()
