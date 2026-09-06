#!/usr/bin/env python3
"""手を動かすところを game.html に流し込む。

読むだけの時間を切るための一手。話は分岐しない。選ばなかったほうを選ぶと
短い場面が入って、同じ選択肢に戻る。二度目は出ない。

  python3 tools/build_acts.py
"""
import io, re, sys, json

def hooks():
    """章の終わりの引き。一度目だけ出る。＊は翳りの音、名前「…」は名札。"""
    try:
        t = io.open("scenario/step8_hooks.md", encoding="utf-8").read()
    except FileNotFoundError:
        return {}
    out = {}
    for blk in t.split("\n## ")[1:]:
        head, body = blk.split("\n", 1)
        m = re.match(r'^(\d)\s+終わりに\s*$', head.strip())
        if not m: raise SystemExit("見出しの形が違う: ## " + head.strip())
        rows = []
        for l in body.split("\n"):
            l = l.rstrip()
            if l.startswith("---"): break
            m2 = re.match(r'^(＊?)\[(L\d+)\]\s*(.+)$', l)
            if not m2: continue
            se, txt = m2.group(1), m2.group(3).strip()
            who = None
            m3 = re.match(r'^([^「]{1,6})(「.+)$', txt)
            if m3: who, txt = m3.group(1), m3.group(2)
            r = {"t": txt}
            if who: r["who"] = who
            if se: r["se"] = "kage"
            rows.append(r)
        if not rows: raise SystemExit("%s の引きが空" % m.group(1))
        out[m.group(1)] = rows
    return out

def parse():
    t = io.open("scenario/step7_acts.md", encoding="utf-8").read()
    out = {}
    for blk in t.split("\n## ")[1:]:
        head, body = blk.split("\n", 1)
        m = re.match(r'^(\d)\s+(L\d+)\s*$', head.strip())
        if not m: raise SystemExit("見出しの形が違う: ## " + head.strip())
        ch, lid = m.group(1), m.group(2)
        go = alt = None; lines = []
        for l in body.split("\n"):
            l = l.rstrip()
            if l.startswith("---"): break
            m2 = re.match(r'^選ぶ[　\s]+(.+)$', l)
            if m2: go = m2.group(1).strip(); continue
            m3 = re.match(r'^やめる[　\s]+(.+)$', l)
            if m3: alt = m3.group(1).strip(); continue
            m4 = re.match(r'^\[(L\d+)\]\s*(.+)$', l)
            if m4: lines.append(m4.group(2).strip())
        if not go or not alt: raise SystemExit("%s %s に選択肢が足りない" % (ch, lid))
        if len(lines) < 2: raise SystemExit("%s %s の場面が短い" % (ch, lid))
        out.setdefault(ch, {})[lid] = {"go": go, "alt": alt, "lines": lines}
    return out

if __name__ == "__main__":
    d, bad = parse(), []
    seen = {}
    for ch in d:
        for lid, a in d[ch].items():
            for k in ("go", "alt"):
                if len(a[k]) > 16: bad.append("%s %s %s が長い（%d字）" % (ch, lid, a[k], len(a[k])))
                if a[k] in seen and seen[a[k]] != ch + lid:
                    bad.append("%s %s「%s」が %s と同じ" % (ch, lid, a[k], seen[a[k]]))
                seen[a[k]] = ch + lid
            n = sum(len(x) for x in a["lines"])
            if n > 220: bad.append("%s %s の場面が長い（%d字）。短い間にする" % (ch, lid, n))
    for b in bad: print("NG  " + b)
    n = sum(len(v) for v in d.values())
    print("\n手を動かすところ %d箇所（%d行）" % (n, sum(len(a["lines"]) for v in d.values() for a in v.values())))
    for ch in sorted(d): print("   第%s章 %d" % (ch, len(d[ch])))
    print("不備 %d 件" % len(bad))
    if bad: sys.exit(1)
    h = hooks()
    blob = ("var ACTS=" + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + ";\n"
            + "var HOOKS=" + json.dumps(h, ensure_ascii=False, separators=(",", ":")) + ";")
    g = io.open("game.html", encoding="utf-8").read()
    a, b = g.index("/* 手を動かすところ ここから */"), g.index("/* 手を動かすところ ここまで */")
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + "/* 手を動かすところ ここから */\n" + blob + "\n" + g[b:])
    print("章の終わりの引き %d箇所（%d行）" % (len(h), sum(len(v) for v in h.values())))
    print("game.html を更新")
