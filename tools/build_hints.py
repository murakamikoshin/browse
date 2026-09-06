# -*- coding: utf-8 -*-
"""手がかりを game.html に流し込む。

朝を一つ見るごとに一つ開く。**同じ額から別の朝へ行く道**の話だけを書く。
値段と中身に触れたものは落とす。

  python3 tools/build_hints.py
"""
import io, re, sys, json

SRC = "scenario/hints.md"
DST = "game.html"
HEAD = "/* 手がかり ここから */"
TAIL = "/* 手がかり ここまで */"

# 値段・割合・中身に触れる語。書いた時点で、隠しているものを渡すことになる
NG = ["％", "%", "割", "円で", "金三", "金五", "金八", "内引",
      "第一封", "第二封", "第三封", "第四封", "保険", "抜い", "百万を",
      "ED", "結末は", "何番"]
NUM = re.compile(r"金[〇一二三四五六七八九十百千万]+円")


def load():
    out = []
    for ln in io.open(SRC, encoding="utf-8"):
        t = ln.strip()
        if not t or t.startswith("#") or t.startswith(">") or t.startswith("---"):
            continue
        out.append(t)
    return out


if __name__ == "__main__":
    rows, bad = [], []
    for t in load():
        hit = [w for w in NG if w in t]
        if hit:
            bad.append((t, "触れてはいけない語: " + hit[0])); continue
        if NUM.search(t):
            bad.append((t, "額が書いてある")); continue
        if len(t) > 60:
            bad.append((t, "長い %d字" % len(t))); continue
        rows.append(t)

    html = io.open(DST, encoding="utf-8").read()
    blob = HEAD + "\nvar HINTS=" + json.dumps(rows, ensure_ascii=False) + ";\n" + TAIL
    a, b = html.index(HEAD), html.index(TAIL) + len(TAIL)
    io.open(DST, "w", encoding="utf-8").write(html[:a] + blob + html[b:])
    print("手がかり %d本" % len(rows))
    for t, why in bad:
        print("   落とした %s  ／ %s" % (t[:30], why))
    print("game.html を更新")
