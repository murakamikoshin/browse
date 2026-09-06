#!/usr/bin/env python3
"""エンディング名を game.html に流し込む。名前が要る組を数えるのもここ。

開封数は残高で決まり、残高は支払額の1%を下回らない（購入の合計は99%を超えられない）。
したがって ¥100,000 以上は必ず一封、¥1,000,000 は必ず二封が開く。
支払額×開封数の格子は96あるが、そのうち11は誰も到達できない。名前が要るのは85。

  python3 tools/build_ed.py --slots    名前が要る85組を並べる（発注用）
  python3 tools/build_ed.py            step5_ed_names.md を検査して流し込む
"""
import io, re, sys, json
from itertools import combinations

STEPS = ([a for a in range(0, 1000, 100)] + [b for b in range(1000, 10000, 1000)]
         + [c for c in range(10000, 100000, 10000)]
         + [d for d in range(100000, 1000000, 100000)] + [1000000])
SEALP = [1000, 10000, 100000, 1000000]

def rates():
    """指せる語句の価格帯を game.html から読む。価格表が変われば到達可能な組も変わる。"""
    g = io.open("game.html", encoding="utf-8").read()
    r = dict(re.findall(r'(\w+):\s*(\d+)', g[g.index("var RATE="):g.index("\n", g.index("var RATE="))]))
    return [int(r[t]) for t in re.findall(r'tier:"(\w+)"', g)]

def maxpct(pcts):
    """100%以下で買える最大の割合。この差が残高の下限になる。"""
    best = 0
    for n in range(len(pcts) + 1):
        for c in combinations(pcts, n):
            s = sum(c)
            if s <= 100 and s > best: best = s
    return best

def opened(bal): return sum(1 for p in SEALP if bal >= p)

def slots():
    mp = maxpct(rates())
    out = []
    for v in STEPS:
        lo, hi = opened(v * (100 - mp) // 100), opened(v)
        for o in range(lo, hi + 1):
            out.append((len(out) + 1, v, o))
    return out

def parse():
    t = io.open("scenario/step5_ed_names.md", encoding="utf-8").read()
    d, cur = {}, None
    for l in t.split("\n"):
        m = re.match(r'^##\s*¥([\d,]+)\s*$', l)
        if m: cur = int(m.group(1).replace(",", "")); d.setdefault(cur, {}); continue
        m2 = re.match(r'^開封(\d)\s+(\S.*)$', l.strip())
        if m2 and cur is not None: d[cur][int(m2.group(1))] = m2.group(2).strip()
    return d

def check(d, sl):
    bad, seen = [], {}
    want = {(v, o) for _, v, o in sl}
    for v in d:
        for o in d[v]:
            if (v, o) not in want:
                bad.append("到達しない組に名前がある　¥%s 開封%d" % (f"{v:,}", o))
    for n, v, o in sl:
        s = d.get(v, {}).get(o)
        if not s:
            bad.append("ED-%02d ¥%s 開封%d が無い" % (n, f"{v:,}", o)); continue
        if re.search(r'[0-9０-９¥円万千]', s):
            bad.append("ED-%02d「%s」に数字か額がある" % (n, s))
        if len(s) > 16:
            bad.append("ED-%02d「%s」が長い（%d字）。数語で" % (n, s, len(s)))
        if s in seen:
            bad.append("ED-%02d「%s」が ED-%02d と同じ" % (n, s, seen[s]))
        seen[s] = n
    return bad

if __name__ == "__main__":
    sl = slots()
    if "--slots" in sys.argv:
        cur = None
        for n, v, o in sl:
            if v != cur: print("\n## ¥%s" % f"{v:,}"); cur = v
            print("開封%d" % o)
        print("\n（%d組）" % len(sl), file=sys.stderr)
        sys.exit(0)
    try:
        d = parse()
    except FileNotFoundError:
        print("scenario/step5_ed_names.md がありません。--slots で発注用の一覧を出せます")
        sys.exit(1)
    bad = check(d, sl)
    for b in bad: print("NG  " + b)
    print("\n不備 %d 件" % len(bad))
    if bad: sys.exit(1)
    tbl = {}
    for _, v, o in sl: tbl.setdefault(str(v), {})[str(o)] = d[v][o]
    blob = "var EDNAMES=" + json.dumps(tbl, ensure_ascii=False, separators=(",", ":")) + ";"
    g = io.open("game.html", encoding="utf-8").read()
    a, b = g.index("/* ED名 ここから */"), g.index("/* ED名 ここまで */")
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + "/* ED名 ここから */\n" + blob + "\n" + g[b:])
    print("game.html を更新　ED名 %d個" % len(sl))
