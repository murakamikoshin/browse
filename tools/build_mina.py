#!/usr/bin/env python3
"""夜、美波が起きてくる場面を game.html に流し込む。

この夜で唯一、汐里が人に何かを渡す場面。選んで起きることではないので、
仏間にいるあいだに向こうから始まる。手は三つ、どれも正しくない。

機械で見るもの：
 - 封の中身（死の理由・金・保険）に触れていないか
 - **手が三つあり、どれも「正しい手」に見える札になっていないか**
 - 美波の台詞が帯で書き分けられていないか（変わるのは汐里の受け取り方だけ）
 - まだ読んでいない章のものを出していないか
"""
import io, re, sys, json

SRC = "scenario/step13_mina.md"
DST = "game.html"
HEAD = "/* 美波 ここから */"
TAIL = "/* 美波 ここまで */"

# 封でしか出てこない事実。ここに混ぜたら、無料で配ることになる
NG = ["保険", "百万", "借", "精算", "自殺", "落ちた", "胴衣", "七秒", "発信履歴",
      "帳場", "封筒", "金", "円", "額", "包ん"]
# 正しい手に見せない。札に評価語を入れない
NG_LABEL = ["正しく", "やさしく", "ちゃんと", "きちんと", "うそ", "嘘", "本当のこと"]


def parse():
    t = io.open(SRC, encoding="utf-8").read()
    t = t[t.index("\n## "):]
    blocks = []
    for blk in t.split("\n## ")[1:]:
        head, body = (blk.split("\n", 1) + [""])[:2]
        head = head.strip()
        base, ov, band = {}, {}, None
        order = []
        for l in body.split("\n"):
            l = l.rstrip()
            m = re.match(r'^帯([2-5])\s*$', l)
            if m: band = m.group(1); continue
            m = re.match(r'^\[(L\d+)\]\s*(.+)$', l)
            if not m: continue
            lid, txt = m.group(1), m.group(2).strip()
            if band is None:
                if lid in base: raise SystemExit("%s に %s が二度ある" % (head, lid))
                base[lid] = txt; order.append(lid)
            else:
                ov.setdefault(lid, {})[band] = txt
        if not base: raise SystemExit("%s が空" % head)
        for lid in ov:
            if lid not in base: raise SystemExit("%s の %s に帯だけがある" % (head, lid))
        blocks.append({"head": head, "order": order, "base": base, "ov": ov})
    return blocks


def split_who(t):
    """美波「…」→ 話者つき。頭に名の無い「」は汐里。
    この場面の行は src を持たないので、speakerOf が汐里を補えない。
    **ここで名札まで決めておく**（でないと台詞に名札が付かない）。"""
    m = re.match(r'^(美波|凪さん|帳場さん)(「.+)$', t)
    if m: return {"t": m.group(2), "who": m.group(1)}
    if t.startswith("「"): return {"t": t, "who": "汐里"}
    return {"t": t}


if __name__ == "__main__":
    B, bad = parse(), []
    heads = [b["head"] for b in B]
    if heads[0] != "入り": bad.append("最初は `## 入り`")
    if heads[-1] != "締め": bad.append("最後は `## 締め`")
    hands = [b for b in B if b["head"].startswith("手 ")]
    if len(hands) != 3: bad.append("手が三つない（%d）" % len(hands))

    for b in B:
        texts = list(b["base"].values()) + [x for o in b["ov"].values() for x in o.values()]
        for t in texts:
            for w in NG:
                if w in t: bad.append("%s に「%s」がある。封か金の話" % (b["head"][:10], w))
        # 美波の台詞は帯で書き分けない
        for lid, o in b["ov"].items():
            if b["base"][lid].startswith("美波「"):
                bad.append("%s %s は美波の台詞。帯で書き分けない" % (b["head"][:10], lid))
    for h in hands:
        lab = h["head"][2:].strip()
        for w in NG_LABEL:
            if w in lab: bad.append("札「%s」に評価語「%s」がある。正しい手を作らない" % (lab, w))

    out = {"enter": None, "hands": [], "close": None}
    def pack(b):
        return {"order": b["order"],
                "base": {k: split_who(v) for k, v in b["base"].items()},
                "ov": {k: {bd: split_who(x) for bd, x in o.items()} for k, o in b["ov"].items()}}
    for b in B:
        if b["head"] == "入り": out["enter"] = pack(b)
        elif b["head"] == "締め": out["close"] = pack(b)
        else: out["hands"].append(dict(pack(b), label=b["head"][2:].strip()))

    for x in bad: print("NG  " + x)
    n = sum(len(b["base"]) for b in B)
    ovn = sum(len(o) for b in B for o in b["ov"].values())
    print("美波の場面　%d行（帯の書き換え %d箇所）" % (n, ovn))
    print("   入り %d行" % len(out["enter"]["order"]))
    for h in out["hands"]: print("   手「%s」 %d行" % (h["label"], len(h["order"])))
    print("   締め %d行" % len(out["close"]["order"]))
    print("不備 %d 件" % len(bad))
    if bad: sys.exit(1)

    blob = "var MINA=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
    g = io.open(DST, encoding="utf-8").read()
    a = g.index(HEAD); b2 = g.index(TAIL, a)
    io.open(DST, "w", encoding="utf-8").write(g[:a] + HEAD + "\n" + blob + "\n" + g[b2:])
    print("game.html を更新")
