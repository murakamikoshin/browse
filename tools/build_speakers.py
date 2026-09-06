#!/usr/bin/env python3
"""話者表を game.html に流し込む。

「」で始まる行のうち汐里以外が喋る行だけを表に持つ。表に無い「」の行は汐里。
地の文には名札を出さない。封と購入の本文は src を持たないので名札は出ない。

原稿の「」の行のうち表に無いものを汐里として数え、内訳を出す。
数が想定と合わなければ、原稿側で台詞が増えたか、行番号がずれている。
"""
import io, re, sys, json

def table():
    t = io.open("scenario/speakers.md", encoding="utf-8").read()
    d, cur = {}, None
    for l in t.split("\n"):
        m = re.match(r'^##\s*(\S+)\s*$', l)
        if m: cur = m.group(1); d.setdefault(cur, {}); continue
        m2 = re.match(r'^(L\d+)\s+(\S+)\s*$', l.strip())
        if m2 and cur: d[cur][m2.group(1)] = m2.group(2)
    return d

def quotes():
    """原稿にある「」の行を章ごとに数える。"""
    out = {}
    for n in range(1, 8):
        ids = []
        b = io.open("scenario/step1_ch%d_band1.md" % n, encoding="utf-8").read()
        for l in b[b.index("[L001]"):].split("\n"):
            m = re.match(r'^\[(L\d+)(?:\s+\S+)?\]\s*(.*)$', l)
            if m and m.group(2).startswith("「") and m.group(1) not in ids:
                ids.append(m.group(1))
        out[str(n)] = ids
    b = io.open("scenario/step6_talks.md", encoding="utf-8").read()
    for blk in b.split("\n## ")[1:]:
        head, body = blk.split("\n", 1)
        tid = re.split(r"[　\t]+", head.strip())[0].lower()
        ids, band = [], False
        for l in body.split("\n"):
            if re.match(r"^帯[2-5]\s*$", l.strip()): band = True
            m = re.match(r'^\[(L\d+)\]\s*(.*)$', l)
            if m and not band and m.group(2).startswith("「"): ids.append(m.group(1))
        out[tid] = ids
    return out

if __name__ == "__main__":
    d, q = table(), quotes()
    bad = []
    for k in d:
        for lid in d[k]:
            if lid not in q.get(k, []):
                bad.append("%s %s は「」の行ではない" % (k, lid))
    for b in bad: print("NG  " + b)
    mine = sum(len([i for i in v if i not in d.get(k, {})]) for k, v in q.items())
    other = sum(len(v) for v in d.values())
    print("\n台詞 %d行　汐里 %d　ほか %d" % (mine + other, mine, other))
    who = {}
    for k in d:
        for lid, nm in d[k].items(): who[nm] = who.get(nm, 0) + 1
    for k, v in sorted(who.items(), key=lambda x: -x[1]): print("   %-8s %d" % (k, v))
    print("不備 %d 件" % len(bad))
    if bad: sys.exit(1)
    blob = "var SPEAK=" + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + ";"
    g = io.open("game.html", encoding="utf-8").read()
    a, b = g.index("/* 話者表 ここから */"), g.index("/* 話者表 ここまで */")
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + "/* 話者表 ここから */\n" + blob + "\n" + g[b:])
    print("game.html を更新")
