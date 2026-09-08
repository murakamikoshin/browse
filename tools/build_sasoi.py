#!/usr/bin/env python3
"""まだ通っていない場所が、一度だけ呼ぶ一行を game.html に流し込む。

夜の行動を増やしたら、玄関だけで一晩もつようになった。歩かない周は
章1・2・4しか読まずに朝になる。手を減らすのではなく、向こうから呼ぶ。
**行くかどうかは、その人が決める。**

機械で見るもの：
 - 呼ぶ先が、章を持つ場所であること（仏間と玄関・帳場は呼ばない）
 - 呼ぶ線香の数が、互いに重ならないこと（二つ続けて来ない）
 - 封と値の語に触れていないこと
 - 「行け」と言っていないこと（呼ぶだけ）

  python3 tools/build_sasoi.py
"""
import io, re, sys, json

SRC = "scenario/step15_sasoi.md"
HEAD, TAIL = "/* 呼ぶ ここから */", "/* 呼ぶ ここまで */"

# その場所の章。仏間（2）は最初に必ず通り、玄関・帳場（1）は始まりの場所
CH = {"minato": "3", "cha": "4", "ishi": "5"}
# 机は必ず仏間のあと（章4は仏間の引き出しを指している）。呼ぶときも順を守る
NEED = {"cha": "2"}
NG = ["七秒", "発信履歴", "胴衣", "保険", "百万", "抜いて", "自殺", "精算",
      "値段", "お代", "いくら", "不足", "残高", "円", "¥"]
# 呼ぶだけ。行けとは言わない
NG2 = ["行きなさい", "行ってください", "行くべき", "見に行け", "寄りなさい"]


def parse():
    t = io.open(SRC, encoding="utf-8").read()
    out = []
    for blk in t.split("\n## ")[1:]:
        head, body = blk.split("\n", 1)
        m = re.match(r"^(\S+)[　\s]+線香(\d+)\s*$", head.strip())
        if not m:
            raise SystemExit("見出しの形が違う: ## " + head.strip())
        place, at = m.group(1), int(m.group(2))
        who, lines = None, []
        for l in body.split("\n"):
            l = l.rstrip()
            if l.startswith("---"): break
            m2 = re.match(r"^\[誰\]\s*(\S+)\s*$", l)
            if m2: who = m2.group(1); continue
            m3 = re.match(r"^\[L\d+\]\s*(.+)$", l)
            if m3: lines.append(m3.group(1).strip())
        if not lines: raise SystemExit("%s が空" % place)
        out.append({"place": place, "at": at, "who": who, "lines": lines})
    return out


if __name__ == "__main__":
    S, bad = parse(), []
    seen = {}
    for s in S:
        if s["place"] not in CH:
            bad.append("%s は呼ばない場所（%s のどれか）" % (s["place"], "／".join(CH)))
        if s["at"] in seen:
            bad.append("線香%d本で二つ呼んでいる（%s と %s）" % (s["at"], seen[s["at"]], s["place"]))
        seen[s["at"]] = s["place"]
        body = "".join(s["lines"])
        for w in NG:
            if w in body: bad.append("%s に「%s」がある。封か値の中身" % (s["place"], w))
        for w in NG2:
            if w in body: bad.append("%s に「%s」がある。呼ぶだけにする" % (s["place"], w))
        for l in s["lines"]:
            if l.startswith("「") and not s["who"]:
                bad.append("%s に話者の無い台詞がある: %s" % (s["place"], l[:14]))
    ats = sorted(x["at"] for x in S)
    for a, b in zip(ats, ats[1:]):
        if b - a < 2: bad.append("線香%d本と%d本が近すぎる。二つ続けて来る" % (a, b))

    out = [{"place": s["place"], "ch": CH.get(s["place"], "?"), "at": s["at"],
            **({"need": NEED[s["place"]]} if s["place"] in NEED else {}),
            "lines": [{"t": l, "who": s["who"]} if l.startswith("「") else {"t": l}
                      for l in s["lines"]]} for s in S]

    for b in bad: print("NG  " + b)
    print("呼ぶ %d箇所" % len(S))
    for s in sorted(S, key=lambda x: -x["at"]):
        print("   線香%-3d %-7s %d行　話者 %s" % (s["at"], s["place"], len(s["lines"]), s["who"] or "——"))
    print("不備 %d 件" % len(bad))
    if bad: sys.exit(1)

    blob = "var SASOI=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
    g = io.open("game.html", encoding="utf-8").read()
    if HEAD not in g: raise SystemExit("game.html に %s が無い" % HEAD)
    a, b = g.index(HEAD), g.index(TAIL, g.index(HEAD))
    io.open("game.html", "w", encoding="utf-8").write(g[:a] + HEAD + "\n" + blob + "\n" + g[b:])
    print("game.html を更新")
