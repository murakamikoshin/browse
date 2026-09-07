# -*- coding: utf-8 -*-
"""スタッフロールを game.html に流し込む。

最終行のあと、余韻を置いてから流れる。押せば飛ばせる。
**金の話は書かない。** ここは余韻の場所で、集計の場所ではない。

  python3 tools/build_credits.py
"""
import io, re, sys, json

SRC = "scenario/credits.md"
DST = "game.html"
HEAD = "/* スタッフロール ここから */"
TAIL = "/* スタッフロール ここまで */"

# 集計と封の語。余韻を金の話で上書きしない
NG = ["金", "円", "内引", "残高", "精算", "開封", "帯", "封", "結末", "ED"]


def parse():
    out, cur, body = [], None, False
    for ln in io.open(SRC, encoding="utf-8"):
        t = ln.rstrip("\n")
        if t.strip() == "---":
            body = True; continue
        if not body:
            continue
        m = re.match(r"^##\s*(.*)$", t)
        if m:
            cur = {"h": m.group(1).strip(), "l": []}
            out.append(cur); continue
        if cur is not None and t.strip():
            cur["l"].append(t.strip())
    return out


if __name__ == "__main__":
    secs = parse()
    bad = []
    for s in secs:
        for t in [s["h"]] + s["l"]:
            hit = [w for w in NG if w in t]
            if hit:
                bad.append((t[:24], "書かない語: " + hit[0]))
    if bad:
        for t, w in bad: print("   NG %-26s %s" % (t, w))
        sys.exit(1)

    html = io.open(DST, encoding="utf-8").read()
    blob = HEAD + "\nvar CREDITS=" + json.dumps(secs, ensure_ascii=False) + ";\n" + TAIL
    a, b = html.index(HEAD), html.index(TAIL) + len(TAIL)
    io.open(DST, "w", encoding="utf-8").write(html[:a] + blob + html[b:])
    n = sum(len(s["l"]) for s in secs)
    print("スタッフロール %d節（%d行）" % (len(secs), n))
    for s in secs:
        print("   %-8s %s" % (s["h"] or "——", " ／ ".join(s["l"]) or "——"))
    print("game.html を更新")
