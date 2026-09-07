#!/usr/bin/env python3
"""夜の半ばの一場面を game.html に流し込む。

線香が四本になったとき、一度だけ、夜のほうから動く。こちらから訊く以外に
何も起きないと中盤が平らになるので、ここだけは選ばずに起きる。

封の中身・値段・不足額に触れていないかを機械で見る。¥0 に出す行に
「お持ちの分」が混ざっていないかも見る（SPEC 5）。
"""
import io, re, sys, json

# 封と購入の中身。ここに触れたら、無料の人に有料の中身を配ることになる
NG = ["七秒", "発信履歴", "胴衣", "保険", "百万", "抜いて", "盗", "自殺",
      "精算", "値段", "お代", "いくら", "不足", "残高", "円", "¥",
      "端金", "相応にいたし", "帳に記します"]
# 解釈を言ってしまう語（売るのは事実だけ）
NG2 = ["つまり", "ということは", "はずだ", "に違いない", "のせいで"]

PLACES = ["genkan", "butsu", "cha", "ishi", "minato"]


def parse():
    t = io.open("scenario/step11_press.md", encoding="utf-8").read()
    blocks = {}
    for blk in t.split("\n## ")[1:]:
        head, body = blk.split("\n", 1)
        head = head.strip()
        alone, who, lines = False, None, []
        for l in body.split("\n"):
            l = l.rstrip()
            if l.startswith("---"): break
            if l.strip() == "[単独]": alone = True; continue
            m = re.match(r'^\[誰\]\s*(\S+)\s*$', l)
            if m: who = m.group(1); continue
            m = re.match(r'^\[L\d+\]\s*(.+)$', l)
            if m: lines.append(m.group(1).strip())
        if not lines: raise SystemExit("%s が空" % head)
        blocks[head] = {"who": who, "alone": alone, "lines": lines}
    return blocks


def voiced(who, lines):
    """「」で始まる行にだけ名札を付ける。地の文には付けない（通し試験が見ている）"""
    return [{"t": l, "who": who} if l.startswith("「") else {"t": l} for l in lines]


if __name__ == "__main__":
    B, bad = parse(), []
    need = ["入り・" + p for p in PLACES] + ["本文", "包んだ人", "机をまだ通っていない人", "締め"]
    for k in need:
        if k not in B: bad.append("`## %s` が無い" % k)
    if bad:
        for b in bad: print("NG  " + b)
        sys.exit(1)

    for k, v in B.items():
        body = "".join(v["lines"])
        for w in NG:
            if w in body: bad.append("%s に「%s」がある。封か値の中身に触れている" % (k, w))
        for w in NG2:
            if w in body: bad.append("%s に「%s」がある。解釈は言わない" % (k, w))
        for l in v["lines"]:
            if l.startswith("「") and not v["who"]:
                bad.append("%s に話者の無い台詞がある: %s" % (k, l[:14]))

    # ¥0 に出る側（入り・本文・机まだ・締め）に、額を匂わせる語が無いこと
    zero = "".join(sum([B["入り・" + p]["lines"] for p in PLACES], [])
                   + B["本文"]["lines"] + B["机をまだ通っていない人"]["lines"] + B["締め"]["lines"])
    for w in ["お持ちの分", "お包み", "ご用意"]:
        if w in zero: bad.append("¥0 にも出る行に「%s」がある（SPEC 5）" % w)

    out = {
        "at": 4,
        "enter": {p: {"alone": B["入り・" + p]["alone"],
                      "lines": voiced(B["入り・" + p]["who"], B["入り・" + p]["lines"])}
                  for p in PLACES},
        "body": voiced(B["本文"]["who"], B["本文"]["lines"]),
        "paid": voiced(B["包んだ人"]["who"], B["包んだ人"]["lines"]),
        "teach": voiced(B["机をまだ通っていない人"]["who"], B["机をまだ通っていない人"]["lines"]),
        "close": voiced(None, B["締め"]["lines"]),
    }

    for b in bad: print("NG  " + b)
    n = sum(len(v["lines"]) for v in B.values())
    print("夜の半ばの一場面　線香%d本で一度だけ　全%d行" % (out["at"], n))
    for p in PLACES:
        e = B["入り・" + p]
        print("   入り %-7s %d行%s　話者 %s" % (p, len(e["lines"]),
              "（単独）" if e["alone"] else "", e["who"] or "——"))
    for k in ["本文", "包んだ人", "机をまだ通っていない人", "締め"]:
        print("   %-14s %d行" % (k, len(B[k]["lines"])))
    print("不備 %d 件" % len(bad))
    if bad: sys.exit(1)

    blob = "var PRESS=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
    g = io.open("game.html", encoding="utf-8").read()
    a = g.index("/* 夜の半ば ここから */")
    b = g.index("/* ここまで */", a)
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + "/* 夜の半ば ここから */\n" + blob + "\n" + g[b:])
    print("game.html を更新")
