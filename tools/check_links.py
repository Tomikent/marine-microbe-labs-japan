"""data/labs.json のリンク（研究室HPとその他のリンク）を確認し、結果を Markdown に書く。

使い方: python tools/check_links.py [report.md]
つながらないリンクがあれば終了コード 1。

自動アクセスを拒否するサイト（403/429 など）は、ページがあっても開けないことがあるので
「要確認」として別に並べ、リンク切れには数えない。
GitHub の実行環境（海外）からは日本の大学サイトがタイムアウトすることがあるので、
タイムアウトも「要確認」に入れる。
"""
import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
TIMEOUT = 30
BLOCKED_STATUS = (401, 403, 429, 503)


def collect_urls():
    """{url: [(研究室名, 種類), ...]}"""
    labs = json.loads((ROOT / 'data' / 'labs.json').read_text(encoding='utf-8'))
    urls = {}
    for l in labs:
        urls.setdefault(l['url'], []).append((l['name'], 'メイン'))
        for x in l.get('extraLinks') or []:
            urls.setdefault(x['url'], []).append((l['name'], x.get('label', 'その他')))
    return urls


def fetch(url):
    """(status, detail) を返す。status は 'ok' | 'blocked' | 'broken'。"""
    last = ''
    for _ in range(2):
        for method in ('HEAD', 'GET'):
            safe = urllib.parse.quote(url, safe=':/?&=%#+,;@~')  # 日本語を含むURL対策
            req = urllib.request.Request(safe, method=method, headers={'User-Agent': USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                    return 'ok', str(res.status)
            except urllib.error.HTTPError as e:
                last = f'HTTP {e.code}'
                if method == 'HEAD':
                    continue  # HEAD に対応しないサーバがある
                if e.code in BLOCKED_STATUS:
                    return 'blocked', last
                break
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, ValueError) as e:
                last = str(getattr(e, 'reason', e))
                if 'timed out' in last:
                    return 'blocked', 'タイムアウト'
                break
        time.sleep(3)
    return 'broken', last


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'link_report.md'
    urls = collect_urls()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(zip(urls, pool.map(fetch, urls)))

    broken = [(u, d) for u, (s, d) in results.items() if s == 'broken']
    blocked = [(u, d) for u, (s, d) in results.items() if s == 'blocked']

    def rows(items):
        lines = ['|研究室|リンク|URL|結果|', '|:---|:---|:---|:---|']
        for url, detail in items:
            for name, kind in urls[url]:
                lines.append(f'|{name}|{kind}|{url}|{detail}|')
        return '\n'.join(lines)

    report = [f'{len(urls)} 件のリンクを確認しました。', '']
    report += [f'## リンク切れの可能性（{len(broken)} 件）', '']
    report += [rows(broken) if broken else 'ありません。', '']
    report += [f'## 要確認：自動アクセスが拒否された・時間切れになったもの（{len(blocked)} 件）', '',
               'ブラウザでは開ける場合がほとんどです。', '']
    report += [rows(blocked) if blocked else 'ありません。', '']
    Path(out_path).write_text('\n'.join(report), encoding='utf-8')

    print(f'checked={len(urls)} broken={len(broken)} blocked={len(blocked)} -> {out_path}')
    sys.exit(1 if broken else 0)


if __name__ == '__main__':
    main()
