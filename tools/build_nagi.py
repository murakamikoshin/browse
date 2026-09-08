#!/usr/bin/env python3
"""夜の半ば、凪さんが探しに来る場面を game.html に流し込む。

夜のほうから動くところが帳場さんの圧（線香四本）しかないと、中盤の前半が平らになる。
線香が九本になったとき、一度だけ、家のほうから動く。

**凪は全部知っている人なので、知っていることを言わせない。** 言うのは母親として
当たり前のことだけで、引っかかりは言い方に置く。封の中身・値段・不足額に触れて
いないかを機械で見る。凪は港まで来ない（美波が寝ている）ので、港だけは単独の場面。

  python3 tools/build_nagi.py
"""
import io, re, sys, json

SRC = "scenario/step14_nagi.md"
HEAD, TAIL = "/* 凪さんが探しに来る ここから */", "/* 凪さんが探しに来る ここまで */"
AT = 9

# 封と購入の中身。ここに触れたら、無料の人に有料の中身を配ることになる
NG = ["七秒", "発信履歴", "胴衣", "保険", "百万", "抜いて", "盗", "自殺", "死のう",
      "精算", "値段", "お代", "いくら", "不足", "残高", "円", "¥",
      "引き出し", "通帳", "借り", "知っていた"]
# 解釈を言ってしまう語（売るのは事実だけ）
NG2 = ["つまり", "ということは", "はずだ", "に違いない", "のせいで"]

PLACES = ["genkan", "butsu", "cha", "ishi", "minato"]


def parse():
    t = io.open(SRC, encoding="utf-8").read()
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


NAMED = re.compile(r'^([^\s「]{1,8})(「.+)$')
MIX = []                      # voiced() が見つけた名札の不備。main で bad に混ぜる


def voiced(who, lines, src=None, head=""):
    """「」で始まる行にだけ名札を付ける。地の文には付けない。
    行頭に `汐里「…」` のように名前を書けば、その行だけ話者を変えられる。
    **一つの塊で行き来のある場面**（凪さんと汐里が交互に喋る所）は、
    [誰] 一つでは片方の台詞にもう片方の名札が出る。実際そうなっていた。
    src を付けた行は、引っかかりが拾える（snagCatch が src+id で見ている）。"""
    out, named, bare = [], 0, 0
    for i, l in enumerate(lines):
        w = who
        m = NAMED.match(l)
        if m: w, l, named = m.group(1), m.group(2), named + 1
        elif l.startswith("「"): bare += 1
        r = {"t": l, "who": w} if l.startswith("「") else {"t": l}
        if src: r["src"] = src; r["id"] = "L%03d" % (i + 1)
        out.append(r)
    # 半分だけ名前を書くと、書き忘れた行に別人の名札が出る。全部か、一つも無いか
    if named and bare:
        MIX.append("%s に、名前を書いた台詞と書いていない台詞が混ざっている"
                   "（%d行／%d行）。片方に別人の名札が出る" % (head or "?", named, bare))
    return out


if __name__ == "__main__":
    B, bad = parse(), []
    need = ["入り・" + p for p in PLACES] + ["本文", "包んだ人", "締め"]
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
    # 凪は港まで来ない。来させると、寝ている美波を置いて坂を下りたことになる
    if not B["入り・minato"]["alone"]:
        bad.append("港の入りが単独になっていない。凪は港まで来ない")
    if B["入り・minato"]["who"]:
        bad.append("港の入りに話者がある。凪は港まで来ない")
    # ¥0 に出る側（入り・本文・締め）に、額を匂わせる語が無いこと
    zero = "".join(sum([B["入り・" + p]["lines"] for p in PLACES], [])
                   + B["本文"]["lines"] + B["締め"]["lines"])
    for w in ["お持ちの分", "お包み", "ご用意", "帳場さんのところ"]:
        if w in zero: bad.append("¥0 にも出る行に「%s」がある（SPEC 5）" % w)
    # 帳場さんの圧（線香四本）と重ならないこと
    g0 = io.open("game.html", encoding="utf-8").read()
    m = re.search(r'var PRESS=\{"at":(\d+)', g0)
    if m and int(m.group(1)) >= AT:
        bad.append("帳場さんの圧が線香%s本。この場面（%d本）と前後しているか重なる"
                   % (m.group(1), AT))

    out = {
        "at": AT,
        "enter": {p: {"alone": B["入り・" + p]["alone"],
                      "lines": voiced(B["入り・" + p]["who"], B["入り・" + p]["lines"],
                                      head="入り・" + p)}
                  for p in PLACES},
        "body": voiced(B["本文"]["who"], B["本文"]["lines"], "凪", head="本文"),
        "paid": voiced(B["包んだ人"]["who"], B["包んだ人"]["lines"], head="包んだ人"),
        "close": voiced(None, B["締め"]["lines"], head="締め"),
    }
    bad += MIX

    for b in bad: print("NG  " + b)
    n = sum(len(v["lines"]) for v in B.values())
    print("凪さんが探しに来る　線香%d本で一度だけ　全%d行" % (AT, n))
    for p in PLACES:
        e = B["入り・" + p]
        print("   入り %-7s %d行%s　話者 %s" % (p, len(e["lines"]),
              "（単独）" if e["alone"] else "", e["who"] or "——"))
    for k in ["本文", "包んだ人", "締め"]:
        print("   %-14s %d行" % (k, len(B[k]["lines"])))
    print("不備 %d 件" % len(bad))
    if bad: sys.exit(1)

    blob = "var NAGI=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
    g = io.open("game.html", encoding="utf-8").read()
    if HEAD not in g:
        raise SystemExit("game.html に %s が無い" % HEAD)
    a = g.index(HEAD); b = g.index(TAIL, a)
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + HEAD + "\n" + blob + "\n" + g[b:])
    print("game.html を更新")
