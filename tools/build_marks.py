# -*- coding: utf-8 -*-
"""音の付く行（翳・重）を game.html に流し込む。

**帯で書き換わる行には付けない。** 付けると、どこが伏線かを音で教えることになる。
無料で遊んでいる人の画面が「印の付いた穴だらけの話」に見えた時点で作りが壊れる。
この道具が、書き換わる行に付いていたら落とす。

  python3 tools/build_marks.py
"""
import io, re, sys, json

SRC = "scenario/marks.md"
DST = "game.html"
HEAD = "/* 印 ここから */"
TAIL = "/* 印 ここまで */"
KIND = {"翳": "kage", "重": "omo"}


def load():
    out = []
    for ln in io.open(SRC, encoding="utf-8"):
        m = re.match(r"^([1-7])\s+(L\d{3})\s+([翳重])\s*(.*)$", ln.strip())
        if m:
            out.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return out


def variants(html):
    """帯で書き換わる行を集める。章1〜6は ov、章7は行ごとの分岐の数で見る"""
    v = {}
    CH = json.loads(re.search(r"\nvar CH = (\{.*?\});\n", html, re.S).group(1))
    for src, C in CH.items():
        v[src] = set((C.get("ov") or {}).keys())
    m = re.search(r"\nvar CH7=(\{.*?\});\n", html, re.S)
    s7 = set()
    if m:
        C7 = json.loads(m.group(1))
        for lid, band in (C7.get("lines") or {}).items():
            for b, ops in band.items():
                if isinstance(ops, dict) and len(ops) > 1:
                    s7.add(lid); break
    v["7"] = s7
    return v, CH, (json.loads(m.group(1)) if m else {})


if __name__ == "__main__":
    html = io.open(DST, encoding="utf-8").read()
    var, CH, C7 = variants(html)
    rows, bad = [], []
    for src, lid, k, note in load():
        ids = CH[src]["order"] if src in CH else list((C7.get("lines") or {}).keys())
        if lid not in ids:
            bad.append((src, lid, k, "その行が無い")); continue
        if lid in var.get(src, set()):
            bad.append((src, lid, k, "帯で書き換わる行なので落とす")); continue
        rows.append((src, lid, k))

    out = {}
    for src, lid, k in rows:
        out.setdefault(src, {})[lid] = KIND[k]
    blob = HEAD + "\nvar MARK=" + json.dumps(out, ensure_ascii=False) + ";\n" + TAIL
    a, b = html.index(HEAD), html.index(TAIL) + len(TAIL)
    io.open(DST, "w", encoding="utf-8").write(html[:a] + blob + html[b:])

    n翳 = len([r for r in rows if r[2] == "翳"])
    n重 = len([r for r in rows if r[2] == "重"])
    print("印 %d行（翳 %d ／ 重 %d）" % (len(rows), n翳, n重))
    for src, lid, k, why in bad:
        print("   落とした 章%s %s %s  %s" % (src, lid, k, why))
    if not bad:
        print("落としたものはありません")
    print("game.html を更新")
