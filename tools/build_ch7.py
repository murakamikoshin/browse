#!/usr/bin/env python3
"""第7章・四つの封・最終行を game.html 用の JS データに変換する。

第7章だけは帯で分岐が閉じない。開封数は残高で決まり、残高は帯とは独立に動くため、
行の変奏は帯と状態（¥0か／不足があるか／封が開いたか）の二軸を持つ。
"""
import io, re, json

COND = {"¥0": "zero", "¥100〜": "paid", "不足あり": "short", "不足なし": "noshort",
        "開封0": "seal0", "開封1〜": "seal1"}

def ch7():
    b1 = io.open("scenario/step1_ch7_band1.md", encoding="utf-8").read()
    order, lines = [], {}
    for l in b1[b1.index("[L001]"):].split("\n"):
        m = re.match(r'^\[(L\d+)(?:\s+(\S+))?\]\s*(.*)$', l)
        if not m: continue
        lid, var, txt = m.groups()
        if lid not in lines: lines[lid] = {}; order.append(lid)
        lines[lid].setdefault(COND.get(var, "all"), {})["1"] = txt
    b2 = io.open("scenario/step2_ch7_bands.md", encoding="utf-8").read()
    cur = None
    for l in b2.split("\n"):
        m = re.match(r'^\[(L\d+)(?:\s+(\S+?))?\]$', l.strip())
        if m: cur = (m.group(1), COND.get(m.group(2), "all")); continue
        m2 = re.match(r'^帯(\d):\s*(.*)$', l)
        if m2 and cur:
            lid, c = cur
            assert lid in lines, lid
            if c not in lines[lid]:                    # 印なしの見出しは既存の枝すべてに掛かる
                c = "all" if "all" in lines[lid] else c
            lines[lid].setdefault(c, {})[m2.group(1)] = m2.group(2)
    return {"order": order, "lines": lines}

def seals():
    t = io.open("scenario/step1_ch7_seals.md", encoding="utf-8").read()
    out, close = [], []
    for blk in t.split("\n## ")[1:]:
        head, body = blk.split("\n", 1)
        body = body.split("\n---")[0]
        if head.startswith("開封") or "締め" in head:
            close = [x for x in body.strip().split("\n") if x.strip() and not x.startswith(("（", ">"))]
            continue
        cur, s = "common", {"title": head.strip(), "common": [], "bought": [], "unbought": []}
        for l in body.split("\n"):
            l = l.strip()
            if not l or l.startswith("（"): continue
            tag = l.strip("*")
            if tag == "【買った人】": cur = "bought"; continue
            if tag == "【買わなかった人】": cur = "unbought"; continue
            if tag == "【共通】": cur = "common"; continue
            s[cur].append(l)
        out.append(s)
    return {"seals": out, "close": close}

def finals():
    t = io.open("scenario/step3_final_lines.md", encoding="utf-8").read()
    t = t[t.index("帯1"):]
    d = {}
    for a, l in re.findall(r'^¥([\d,]+)\n(.+(?:\n.+)?)$', t, re.M):
        d[int(a.replace(",", ""))] = l.strip().split("\n")
    return d

if __name__ == "__main__":
    c, s, f = ch7(), seals(), finals()
    assert len(f) == 38, len(f)
    assert len(s["seals"]) == 4 and len(s["close"]) == 2, (len(s["seals"]), len(s["close"]))
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    blob = (
        "var CH7=" + j(c) + ";\nvar SEALTEXT=" + j(s["seals"]) +
        ";\nvar SEALCLOSE=" + j(s["close"]) + ";\nvar FINALS=" + j(f) + ";\n")
    io.open("/tmp/ch7.js", "w", encoding="utf-8").write(blob)
    g = io.open("game.html", encoding="utf-8").read()
    a = g.index("var CH7=")
    b = g.index("var STEPS=[];")
    io.open("game.html", "w", encoding="utf-8").write(g[:a] + blob + "\n" + g[b:])
    print("game.html を更新")
    br = {}
    for lid, v in c["lines"].items():
        for k in v: br[k] = br.get(k, 0) + 1
    print("第7章 %d行 枝%s" % (len(c["order"]), br))
    for x in s["seals"]:
        print("  %-22s 共通%2d 買った%2d 買わない%2d" % (x["title"], len(x["common"]), len(x["bought"]), len(x["unbought"])))
    print("締め%d行 ／ 最終行%d本" % (len(s["close"]), len(f)))
