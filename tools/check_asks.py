#!/usr/bin/env python3
"""指せる語句が全帯に存在するかを検査する。

帯が上がると本文が書き換わるため、書き換えで消える語句をアンカーにすると
高額を払った人ほど指せる語句が減る。設計と逆のことが起きるので、
game.html の ASKS が参照する語句が帯1〜帯5のすべてに存在することを確認する。
"""
import io, re, sys, json

def load(n):
    b1 = io.open("scenario/step1_ch%d_band1.md" % n, encoding="utf-8").read()
    base, order = {}, []
    for l in b1[b1.index("[L001]"):].split("\n"):
        m = re.match(r'^\[(L\d+)(?:\s+(¥\S+))?\]\s*(.*)$', l)
        if not m: continue
        lid, var, txt = m.groups()
        if lid not in base: base[lid] = {}; order.append(lid)
        base[lid]["zero" if var == "¥0" else "paid"] = txt
    for k in base:
        base[k].setdefault("paid", base[k].get("zero", ""))
    ov, cur = {}, None
    for l in io.open("scenario/step2_ch%d_bands.md" % n, encoding="utf-8").read().split("\n"):
        m = re.match(r'^\[(L\d+)', l)
        if m: cur = m.group(1); continue
        m2 = re.match(r'^帯(\d):\s*(.*)$', l)
        if m2 and cur: ov.setdefault(cur, {})[int(m2.group(1))] = m2.group(2)
    return base, ov

def text_at(base, ov, lid, band):
    t = base[lid]["paid"]
    for lv in range(2, band + 1):
        if lid in ov and lv in ov[lid]: t = ov[lid][lv]
    return t

g = io.open("game.html", encoding="utf-8").read()
asks = re.findall(r'\w+:\{\s*ch:"(\d)",\s*line:"(L\d+)",\s*phrase:"([^"]+)"', g)
if not asks:
    print("ASKS を読み取れませんでした"); sys.exit(1)

bad = 0
for ch, lid, phrase in asks:
    base, ov = load(int(ch))
    if lid not in base:
        print("NG  第%s章 %s が存在しません" % (ch, lid)); bad += 1; continue
    missing = [b for b in range(1, 6) if phrase not in text_at(base, ov, lid, b)]
    if missing:
        print("NG  第%s章 %s「%s」が帯%s に存在しません"
              % (ch, lid, phrase, "・".join(map(str, missing))))
        for b in missing:
            print("      帯%d: %s" % (b, text_at(base, ov, lid, b)))
        bad += 1
    else:
        print("OK  第%s章 %s「%s」" % (ch, lid, phrase))

print()
print("不備 %d 件" % bad)
sys.exit(1 if bad else 0)
