#!/usr/bin/env python3
"""data/labs.json から data/labs.js と data/labs.csv を作り直す。

研究室を追加・修正したら、data/labs.json を編集してからリポジトリ直下で
    python3 tools/build_data.py
を実行する（標準ライブラリのみ・追加インストール不要）。
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REQUIRED = ["id", "name", "institution", "prefecture", "mapCity",
            "latitude", "longitude", "scope", "url", "description"]
CSV_COLS = ["id", "name", "institution", "prefecture", "mapCity", "latitude",
            "longitude", "scope", "leaders", "organisms", "url",
            "lastReview"]


PUBLIC = ["id", "name", "institution", "prefecture", "mapCity", "latitude", "longitude", "scope",
          "leaders", "themes", "organisms", "methods", "tags", "description", "url", "linkType",
          "extraLinks", "lastReview", "checked"]


def main() -> int:
    labs = json.loads((DATA / "labs.json").read_text(encoding="utf-8"))

    # 最低限のチェック
    errors, seen = [], set()
    for i, l in enumerate(labs):
        for k in REQUIRED:
            if l.get(k) in (None, ""):
                errors.append(f"{i}: {l.get('id', '?')} に {k} がない")
        if l.get("id") in seen:
            errors.append(f"{i}: id が重複 {l['id']}")
        seen.add(l.get("id"))
        if l.get("scope") not in ("core", "related"):
            errors.append(f"{i}: {l.get('id')} の scope は core/related のどちらか")
        if not str(l.get("url", "")).startswith(("http://", "https://")):
            errors.append(f"{i}: {l.get('id')} の url が http(s) で始まらない")
    if errors:
        print("データにエラーがあります:", *errors, sep="\n  ")
        return 1

    updated = max((l.get("lastReview") or l.get("checked") or "") for l in labs)
    # ページで使う項目だけを書き出す（確認メモなどは labs.json にだけ残す）
    public = [{k: l[k] for k in PUBLIC if k in l} for l in labs]
    payload = json.dumps(public, ensure_ascii=False, indent=1).replace("</", "<\\/")
    (DATA / "labs.js").write_text(
        "// 自動生成ファイル：直接編集せず data/labs.json を編集して tools/build_data.py を実行\n"
        f"window.LABS_UPDATED = {json.dumps(updated)};\n"
        f"window.LABS = {payload};\n",
        encoding="utf-8",
    )
    # ブラウザが古いデータを使い続けないよう、index.html の読み込みに版番号を付ける
    import hashlib, re
    ver = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:8]
    index = ROOT / "index.html"
    if index.exists():
        html = index.read_text(encoding="utf-8")
        html2 = re.sub(r'data/labs\.js(\?v=[0-9a-f]+)?"', f'data/labs.js?v={ver}"', html)
        if html2 != html:
            index.write_text(html2, encoding="utf-8")
    with open(DATA / "labs.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLS)
        for l in labs:
            w.writerow(["・".join(v) if isinstance(v := l.get(c, ""), list) else v for c in CSV_COLS])

    print(f"{len(labs)} 件を書き出しました（最終確認日 {updated}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
