# -*- coding: utf-8 -*-
"""夜の順番が入れ替わっても話が通るかを見る。

夜は地図なので、章と夜の行動はどの順で読まれるか分からない（SPEC 3「夜は章ではなく地図」）。
そのための規則が「章をまたいだ参照は、事実を一度自分で述べる」。
この道具は、その規則が破れていそうな所を機械で拾う。**判断は人がする。**

  python3 tools/check_order.py
"""
import io, os, re, sys, json

# 前に読んだことを前提にしている言い方。これが出たら、その場で事実を述べているか見る
DEIXIS = ["さっき", "先ほど", "例の", "あの話", "さっきの", "前に言", "前に聞",
          "さきほど", "言ったとおり", "聞いたとおり", "さっき見", "さっき訊"]

# 人。初めて出るところで、誰なのかが分かるように書いてあるか
PEOPLE = ["凪", "美波", "帳場さん", "貝原", "魚屋の奥さん", "隣のおじさん", "巽", "田上"]

PLACE = {"1": "玄関・帳場", "2": "仏間", "3": "港", "4": "帳場の奥", "5": "玄関の外",
         "6": "夜明け前", "7": "翌朝"}


def blocks(html):
    """章 / 夜の行動 / 手を動かすところ の本文を、出どころ付きで並べる"""
    out = []
    m = re.search(r"\nvar CH = (\{.*?\});\n", html, re.S)
    CH = json.loads(m.group(1))
    for src in sorted(CH):
        C = CH[src]
        for lid in C["order"]:
            b = C["base"].get(lid, {})
            for k in ("zero", "paid"):
                if b.get(k):
                    out.append(("章" + src, lid, b[k]))
            for lv, t in (C.get("ov", {}).get(lid) or {}).items():
                out.append(("章" + src + "帯" + lv, lid, t))
    m = re.search(r"\nvar TALK=(\[.*?\]);\n", html, re.S)
    if m:
        for t in json.loads(m.group(1)):
            for i, l in enumerate(t["lines"]):
                out.append(("話" + t["k"] + "・" + PLACE.get(t["place"], t["place"]),
                            "L%03d" % (i + 1), l))
            for lid, o in (t.get("ov") or {}).items():
                for lv, txt in o.items():
                    out.append(("話" + t["k"] + "帯" + lv, lid, txt))
    m = re.search(r"\nvar ACTS=(\{.*?\});\n", html, re.S)
    if m:
        A = json.loads(m.group(1))
        for src in sorted(A):
            for lid, a in A[src].items():
                for i, l in enumerate(a.get("lines", [])):
                    out.append(("一手" + src + "-" + lid, "L%03d" % (i + 1), l))
    return out


if __name__ == "__main__":
    html = io.open("game.html", encoding="utf-8").read()
    B = blocks(html)
    print("見た本文 %d行\n" % len(B))

    hit = []
    for src, lid, t in B:
        for d in DEIXIS:
            if d in t:
                hit.append((src, lid, d, t))
                break
    print("**前に読んだことを前提にした言い方 %d件**" % len(hit))
    for src, lid, d, t in hit:
        print("   %-16s %s  「%s」  %s" % (src, lid, d, t[:52]))
    if not hit:
        print("   ありません")

    print()
    first = {}
    for src, lid, t in B:
        for p in PEOPLE:
            if p in t and p not in first:
                first[p] = (src, lid, t[:46])
    print("**人が最初に出てくるところ**（夜は順番が入れ替わるので、ここが初対面になり得る）")
    for p in PEOPLE:
        if p in first:
            s, l, t = first[p]
            print("   %-8s %-16s %s  %s" % (p, s, l, t))
        else:
            print("   %-8s 出てこない" % p)
