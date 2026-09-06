# -*- coding: utf-8 -*-
"""引っかかりを game.html に流し込む。

夜のあいだに読んだ行だけを、あとで並べ直す場面。新しい事実は足さない。
出どころの行が実在するかを機械で見る。無い行を指していると、
「読んでいないものが並ぶ」ことになって、そこだけ矛盾する。

  python3 tools/build_snags.py
"""
import io, re, sys, json

SRC = "scenario/step10_snags.md"
DST = "game.html"
HEAD = "/* 引っかかり ここから */"
TAIL = "/* 引っかかり ここまで */"

# 封と購入でしか出てこない事実。並べ直しに混ぜたら、無料で渡すことになる
NG = ["七秒", "発信履歴", "内引", "うちびき", "堤防から落ちたら", "事故になりますか",
      "胴衣を脱いだ", "四月十四日", "四月十九日", "保険金", "借入", "抜いた", "相応",
      "自分で", "自殺", "死のう", "決めていた"]


def parse():
    snags, tiers = [], []
    cur = None
    for ln in io.open(SRC, encoding="utf-8"):
        t = ln.rstrip("\n")
        m = re.match(r"^引\s+(\S+)\t(\S+)\t(L\d{3})\t(.+)$", t)
        if m:
            snags.append({"k": m.group(1), "src": m.group(2), "id": m.group(3),
                          "t": m.group(4).strip()})
            continue
        m = re.match(r"^##\s*段\s*(\d+)\s*$", t)
        if m:
            cur = {"n": int(m.group(1)), "head": "", "tail": {}}
            tiers.append(cur); continue
        if cur is None:
            continue
        m = re.match(r"^頭\t(.+)$", t)
        if m: cur["head"] = m.group(1).strip(); continue
        m = re.match(r"^尻([1-5])\t(.+)$", t)
        if m: cur["tail"][m.group(1)] = m.group(2).strip()
    return snags, tiers


if __name__ == "__main__":
    snags, tiers = parse()
    html = io.open(DST, encoding="utf-8").read()
    CH = json.loads(re.search(r"\nvar CH = (\{.*?\});\n", html, re.S).group(1))
    TALK = json.loads(re.search(r"\nvar TALK=(\[.*?\]);\n", html, re.S).group(1))
    TK = dict((t["k"], t) for t in TALK)

    bad = []
    for s in snags:
        if s["src"] in CH:
            if s["id"] not in CH[s["src"]]["order"]:
                bad.append((s["k"], "章%s に %s が無い" % (s["src"], s["id"])))
        elif s["src"] in TK:
            n = int(s["id"][1:])
            if n < 1 or n > len(TK[s["src"]]["lines"]):
                bad.append((s["k"], "%s に %s が無い" % (s["src"], s["id"])))
        else:
            bad.append((s["k"], "出どころが無い: " + s["src"]))
        hit = [w for w in NG if w in s["t"]]
        if hit:
            bad.append((s["k"], "封の語が入っている: " + hit[0]))
    for tr in tiers:
        for b, t in tr["tail"].items():
            hit = [w for w in NG if w in t]
            if hit:
                bad.append(("段%d帯%s" % (tr["n"], b), "封の語: " + hit[0]))
        if not tr["head"] or "1" not in tr["tail"]:
            bad.append(("段%d" % tr["n"], "頭か尻1が無い"))
    if bad:
        for k, w in bad: print("   NG %-8s %s" % (k, w))
        sys.exit(1)

    blob = (HEAD + "\nvar SNAG=" + json.dumps(snags, ensure_ascii=False) +
            ";\nvar SNAGT=" + json.dumps(tiers, ensure_ascii=False) + ";\n" + TAIL)
    a, b = html.index(HEAD), html.index(TAIL) + len(TAIL)
    io.open(DST, "w", encoding="utf-8").write(html[:a] + blob + html[b:])
    print("引っかかり %d個 ／ 段 %s" % (len(snags), " ".join(str(t["n"]) for t in tiers)))
    for t in tiers:
        print("   段%-3d 帯の書き分け %d" % (t["n"], len(t["tail"])))
    print("game.html を更新")
