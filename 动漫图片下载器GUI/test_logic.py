# -*- coding: utf-8 -*-
"""离线单元测试: 验证 Pixiv 过滤逻辑与 Safebooru XML 解析 (不依赖网络)。"""
import sys
import os

# 将主模块所在目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import pixiv_is_allowed, parse_safebooru_xml, safebooru_is_allowed, pixiv_session_headers, normalize_pixiv_cookie


def test_pixiv_filter():
    cases = [
        ({"id": "1", "title": "t", "userName": "u", "xRestrict": 0, "aiType": 0}, True, "普通图放行"),
        ({"id": "2", "xRestrict": 1, "aiType": 0}, True, "R18 放行 (禁止屏蔽R18)"),
        ({"id": "3", "xRestrict": 2, "aiType": 0}, True, "R18 变体放行"),
        ({"id": "4", "xRestrict": 0, "aiType": 1}, False, "AI 疑似剔除"),
        ({"id": "5", "xRestrict": 0, "aiType": 2}, False, "AI 标注剔除"),
        ({"id": "6", "xRestrict": None, "aiType": 0}, True, "xRestrict 缺失按放行"),
        ({}, False, "无 id 不合法"),
    ]
    ok = True
    for item, expect, desc in cases:
        got = pixiv_is_allowed(item)
        mark = "PASS" if got == expect else "FAIL"
        if got != expect:
            ok = False
        print(f"  [Pixiv] {mark}: {desc} (expect={expect}, got={got})")
    return ok


def test_safebooru_parse():
    xml = """<?xml version="1.0"?>
<posts count="3" offset="0">
  <post id="10" file_url="https://safebooru.org/images/10.jpg" source="src1" rating="s" tags="cat red"/>
  <post id="11" file_url="https://safebooru.org/images/11.png" source="" rating="s" tags="dog blue"/>
  <post id="12" source="x" rating="s" tags="no_url"/>
</posts>"""
    posts = parse_safebooru_xml(xml)
    ok = True
    checks = [
        (len(posts) == 2, f"过滤无 file_url 后数量=2 (got={len(posts)})"),
        (posts[0]["file_url"].endswith("10.jpg"), "首条 file_url 正确"),
        (posts[0]["tags"] == "cat red", "tags 解析正确"),
        (safebooru_is_allowed(posts[0]) is True, "合法 post 放行"),
        (safebooru_is_allowed({"file_url": ""}) is False, "空 file_url 拦截"),
    ]
    for cond, desc in checks:
        mark = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"  [Safebooru] {mark}: {desc}")
    return ok


def test_safebooru_bad_xml():
    posts = parse_safebooru_xml("<<<not xml")
    ok = posts == []
    print(f"  [Safebooru] {'PASS' if ok else 'FAIL'}: 坏 XML 返回空列表 (got={posts})")
    return ok


def test_pixiv_filter_allow_ai():
    """block_ai=False 时, AI 图 (aiType 1/2) 应放行; R18 始终放行。"""
    cases = [
        ({"id": "1", "xRestrict": 0, "aiType": 1}, True, "AI 疑似放行"),
        ({"id": "2", "xRestrict": 0, "aiType": 2}, True, "AI 标注放行"),
        ({"id": "3", "xRestrict": 1, "aiType": 1}, True, "R18+AI 均放行"),
        ({"id": "4", "xRestrict": 0, "aiType": 0}, True, "普通图放行"),
        ({}, False, "无 id 不合法"),
    ]
    ok = True
    for item, expect, desc in cases:
        got = pixiv_is_allowed(item, block_ai=False)
        mark = "PASS" if got == expect else "FAIL"
        if got != expect:
            ok = False
        print(f"  [Pixiv-AI放行] {mark}: {desc} (expect={expect}, got={got})")
    return ok


def test_normalize_cookie():
    cases = [
        ("", "", "空值保持空"),
        ("PHPSESSID=abc123", "PHPSESSID=abc123", "已带前缀原样透传"),
        ("PHPSESSID=abc123; other=x", "PHPSESSID=abc123; other=x", "整串 cookie 原样透传"),
        ("abc123", "PHPSESSID=abc123", "裸值自动补前缀"),
        ("  abc123  ", "PHPSESSID=abc123", "裸值含空白先 strip 再补前缀"),
    ]
    ok = True
    for raw, expect, desc in cases:
        got = normalize_pixiv_cookie(raw)
        mark = "PASS" if got == expect else "FAIL"
        if got != expect:
            ok = False
        print(f"  [Cookie] {mark}: {desc} (expect={expect!r}, got={got!r})")
    return ok


def test_pixiv_headers():
    h1 = pixiv_session_headers()
    checks = [
        (h1.get("Referer") == "https://www.pixiv.net/", "默认带 Referer"),
        ("User-Agent" in h1, "带 UA"),
        ("Cookie" not in h1, "无 cookie 时不带 Cookie 头"),
    ]
    h2 = pixiv_session_headers("PHPSESSID=abc123; other=x")
    checks.append(("Cookie" in h2 and "abc123" in h2["Cookie"], "有 cookie 时附加 Cookie 头"))
    ok = True
    for cond, desc in checks:
        mark = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"  [Headers] {mark}: {desc}")
    return ok


if __name__ == "__main__":
    print("== 离线逻辑验证 ==")
    r1 = test_pixiv_filter()
    r2 = test_safebooru_parse()
    r3 = test_safebooru_bad_xml()
    r4 = test_pixiv_headers()
    r5 = test_normalize_cookie()
    r6 = test_pixiv_filter_allow_ai()
    all_ok = r1 and r2 and r3 and r4 and r5 and r6
    print(f"== 结论: {'全部通过' if all_ok else '存在失败'} ==")
    sys.exit(0 if all_ok else 1)
