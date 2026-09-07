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


# ---- 夜の場所は好きな順に回れる。まだ読んでいない章のものを思い出していないか ----
# 章1 は必ず最初。章2（仏間）を読まないと、港も机も石段も開かない。
# 章3・4・5 は互いに前提にできない。仏間の手も、そのどれも前提にできない。
NEED = {"1": {"1"}, "2": {"1", "2"}, "3": {"1", "2", "3"},
        "4": {"1", "2", "4"}, "5": {"1", "2", "5"},
        "6": {"1", "2", "3", "4", "5", "6"}, "7": set("1234567")}
PLACE_NEED = {"genkan": {"1", "2"}, "butsu": {"1", "2"}, "minato": {"1", "2", "3"},
              "cha": {"1", "2", "4"}, "ishi": {"1", "2", "5"}}
EARLY = {"t01", "t03", "t04"}          # 仏間より前に読める玄関の手

# その章へ行かないと見られないもの。ここで挙げた語は、その章を読んでいない所には出せない
ONLY = {"3": ["塗り直", "白い船体", "舫", "継ぎ目", "操舵室", "船首", "堤防の先"],
        "4": ["木箱", "手帳", "切符", "小銭", "真鍮"],
        "5": ["石段"]}


def reach(html):
    """本文を、そこを読むまでに必ず読んでいる章の組と一緒に並べる"""
    out = []
    CH = json.loads(re.search(r"\nvar CH = (\{.*?\});\n", html, re.S).group(1))
    for src in sorted(CH):
        have = NEED.get(src, set())
        C = CH[src]
        for lid in C["order"]:
            for k, v in (C["base"].get(lid) or {}).items():
                out.append(("章%s %s" % (src, lid), have, v))
            for lv, v in (C.get("ov", {}).get(lid) or {}).items():
                out.append(("章%s帯%s %s" % (src, lv, lid), have, v))
    m = re.search(r"\nvar HOOKS=(\{.*?\});\n", html, re.S)
    if m:
        for src, xs in json.loads(m.group(1)).items():
            for x in xs:
                out.append(("引%s" % src, NEED.get(src, set()), x["t"]))
    m = re.search(r"\nvar ACTS=(\{.*?\});\n", html, re.S)
    if m:
        for src, d in json.loads(m.group(1)).items():
            for lid, a in d.items():
                for l in a.get("lines", []):
                    out.append(("一手%s %s" % (src, lid), NEED.get(src, set()), l))
    m = re.search(r"\nvar TALK=(\[.*?\]);\n", html, re.S)
    if m:
        for t in json.loads(m.group(1)):
            have = {"1"} if t["k"] in EARLY else set(PLACE_NEED[t["place"]])
            for l in t["lines"]:
                out.append(("話%s" % t["k"], have, l))
            for lid, o in (t.get("ov") or {}).items():
                for lv, txt in o.items():
                    out.append(("話%s帯%s" % (t["k"], lv), have, txt))
    return out


def check_reach(units):
    bad, seen = [], set()
    for name, have, txt in units:
        for src, words in ONLY.items():
            if src in have:
                continue
            for w in words:
                if w in txt and (name, w) not in seen:
                    seen.add((name, w))
                    bad.append((name, src, w, txt))
    return bad


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

    print()
    bad = check_reach(reach(html))
    print("**まだ読んでいない章のものを思い出している所 %d件**" % len(bad))
    for name, src, w, txt in bad:
        print("   %-12s 章%s の「%s」  %s" % (name, src, w, txt[:46]))
    if not bad:
        print("   ありません")
    sys.exit(1 if bad else 0)
