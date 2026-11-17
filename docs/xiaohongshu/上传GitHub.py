# -*- coding: utf-8 -*-
"""一次性脚本：把小红书宣传物料 + 脱敏截图推到 GitHub（单次 commit）。

用法：
  set GH_TOKEN=<你的 token>   (PowerShell: $env:GH_TOKEN="...")
  python 上传GitHub.py

走 Git Data API：create blobs -> tree -> commit -> update ref。
token 从环境变量读取，不落盘。
"""
import base64
import json
import os
import sys
import urllib.request

REPO_API = "https://api.github.com/repos/jm17647-dna/phone-VibeKey"
BRANCH = "main"
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 项目根

# (仓库内路径, 本地绝对路径)
FILES = [
    ("docs/xiaohongshu/01-封面.png", "docs/xiaohongshu/01-封面.png"),
    ("docs/xiaohongshu/02-痛点.png", "docs/xiaohongshu/02-痛点.png"),
    ("docs/xiaohongshu/03-原理.png", "docs/xiaohongshu/03-原理.png"),
    ("docs/xiaohongshu/04-语音中.png", "docs/xiaohongshu/04-语音中.png"),
    ("docs/xiaohongshu/05-Agent.png", "docs/xiaohongshu/05-Agent.png"),
    ("docs/xiaohongshu/06-适用.png", "docs/xiaohongshu/06-适用.png"),
    ("docs/xiaohongshu/07-上手.png", "docs/xiaohongshu/07-上手.png"),
    ("docs/xiaohongshu/08-隐私.png", "docs/xiaohongshu/08-隐私.png"),
    ("docs/xiaohongshu/09-收尾.png", "docs/xiaohongshu/09-收尾.png"),
    ("docs/xiaohongshu/小红书文案.md", "docs/xiaohongshu/小红书文案.md"),
    ("docs/xiaohongshu/生成图片.py", "docs/xiaohongshu/生成图片.py"),
    ("docs/screenshots/01-phone.png", "docs/screenshots/01-phone.png"),  # 脱敏版
    ("docs/screenshots/README.md", "docs/screenshots/README.md"),
    ("README.md", "README.md"),
]

COMMIT_MSG = (
    "docs: 新增小红书宣传物料（9 张卡片 + 文案 + 生成脚本），"
    "README 加宣传图版块；替换 01-phone.png 为脱敏版（遮住键盘工具栏泄露的凭据前缀）"
)


def api(method, path, body=None):
    token = os.environ["GH_TOKEN"]
    req = urllib.request.Request(
        REPO_API + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "phone-VibeKey-upload",
        },
    )
    with urllib.request.urlopen(req) as r:
        txt = r.read()
        return json.loads(txt) if txt else None


def main():
    # 1. 取 main 当前 commit 和 tree
    ref = api("GET", "/git/ref/heads/" + BRANCH)
    parent_sha = ref["object"]["sha"]
    parent = api("GET", "/git/commits/" + parent_sha)
    base_tree = parent["tree"]["sha"]
    print("parent commit:", parent_sha)

    # 2. 逐个建 blob
    entries = []
    for repo_path, local_rel in FILES:
        p = os.path.join(BASE, local_rel)
        if not os.path.exists(p):
            sys.exit("缺少文件: " + p)
        with open(p, "rb") as f:
            data = f.read()
        blob = api("POST", "/git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
        entries.append({"path": repo_path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print("blob ok:", repo_path, len(data), "bytes ->", blob["sha"][:10])

    # 3. tree -> commit -> 更新 ref
    tree = api("POST", "/git/trees", {"base_tree": base_tree, "tree": entries})
    commit = api("POST", "/git/commits", {"message": COMMIT_MSG, "tree": tree["sha"], "parents": [parent_sha]})
    api("PATCH", "/git/refs/heads/" + BRANCH, {"sha": commit["sha"]})
    print("PUSHED commit:", commit["sha"])
    print("https://github.com/jm17647-dna/phone-VibeKey/commit/" + commit["sha"])


if __name__ == "__main__":
    main()
