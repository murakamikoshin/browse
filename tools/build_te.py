#!/usr/bin/env python3
"""取り消せない手を game.html に流し込む。

夜の手はどれも「選ぶ→五行読む→線香が減る」という同じ形をしている。
それを割るのが取り消せない選択で、いままで美波の場面が一つあるだけだった。

機械で見るもの：
 - 場面ごとに手が三つあること
 - 札に評価語（正しく・やさしく・うそ…）が入っていないこと
 - 相手の台詞が帯で書き分けられていないこと（変わるのは汐里の受け取り方だけ）
 - 封と値の中身に触れていないこと
 - 夜のほうから動くほかの場面（美波・凪さん・帳場さんの圧）と線香が重ならないこと

  python3 tools/build_te.py
"""
import io, re, sys, json

SRC = "scenario/step16_te.md"
DST = "game.html"
HEAD, TAIL = "/* 取り消せない手 ここから */", "/* 取り消せない手 ここまで */"
PLACES = ["genkan", "butsu", "minato", "cha", "ishi"]

# 封と購入でしか出てこない事実
NG = ["七秒", "発信履歴", "うちびき", "内引", "保険", "百万", "抜いて", "自殺", "死のう",
      "精算", "値段", "お代", "いくら", "不足", "残高", "円", "¥", "胴衣"]
# 正しい手に見せない。札に評価語を入れない
NG_LABEL = ["正しく", "やさしく", "ちゃんと", "きちんと", "うそ", "嘘", "本当のこと", "べき"]


def split_who(t):
    m = re.match(r'^([^「]{1,6})(「.+)$', t)
    if m: return {"t": m.group(2), "who": m.group(1)}
    if t.startswith("「"): return {"t": t, "who": "汐里"}
    return {"t": t}


def parse():
    t = io.open(SRC, encoding="utf-8").read()
    out = []
    for blk in t.split("\n## 場面 ")[1:]:
        head, body = blk.split("\n", 1)
        f = head.strip().split()
        if len(f) < 3: raise SystemExit("見出しの形が違う: ## 場面 " + head.strip())
        place, at, name = f[0], int(f[1]), f[2]
        parts, cur = [], None
        for l in body.split("\n"):
            l = l.rstrip()
            if l.startswith("## 場面"): break
            m = re.match(r"^###\s*(.+)$", l)
            if m:
                cur = {"head": m.group(1).strip(), "order": [], "base": {}, "ov": {}}
                parts.append(cur); continue
            if cur is None: continue
            m = re.match(r"^帯([2-5])\s*$", l.strip())
            if m: cur["band"] = int(m.group(1)); continue
            m = re.match(r"^\[(L\d+)\]\s*(.+)$", l)
            if not m: continue
            lid, txt = m.group(1), m.group(2).strip()
            if not cur.get("band"):
                if lid in cur["base"]: raise SystemExit("%s %s が二度ある" % (cur["head"], lid))
                cur["base"][lid] = txt; cur["order"].append(lid)
            else:
                if lid not in cur["base"]:
                    raise SystemExit("%s 帯%d の %s は帯1に無い" % (cur["head"], cur["band"], lid))
                cur["ov"].setdefault(lid, {})[str(cur["band"])] = txt
        out.append({"place": place, "at": at, "name": name, "parts": parts})
    return out


def pack(b, src=None):
    """src を付けた塊は、引っかかりが拾える（snagCatch が src+id で見ている）。"""
    def one(k, v):
        d = split_who(v)
        if src: d["src"] = src; d["id"] = k
        return d
    return {"order": b["order"],
            "base": {k: one(k, v) for k, v in b["base"].items()},
            "ov": {k: {bd: one(k, x) for bd, x in o.items()} for k, o in b["ov"].items()}}


if __name__ == "__main__":
    S, bad = parse(), []
    g = io.open(DST, encoding="utf-8").read()
    taken = {}
    for name, var in (("美波", r'var MINA=.*?"at"?'), ):
        pass
    m = re.search(r'var PRESS=\{"at":(\d+)', g); press = int(m.group(1)) if m else None
    m = re.search(r'var NAGI=\{"at":(\d+)', g); nagi = int(m.group(1)) if m else None
    m = re.search(r"var INCENSE=(\d+);", g); inc = int(m.group(1)) if m else 16
    others = {"夜の半ば": press, "凪さん": nagi, "美波": inc - 3}
    sasoi = re.search(r"var SASOI=(\[.*?\]);\n", g, re.S)
    if sasoi:
        for s in json.loads(sasoi.group(1)): others["呼ぶ・" + s["place"]] = s["at"]

    out = []
    for sc in S:
        if sc["place"] not in PLACES:
            bad.append("%s 場所が違う（%s のどれか）" % (sc["place"], "／".join(PLACES)))
        heads = [p["head"] for p in sc["parts"]]
        if not heads or heads[0] != "入り": bad.append("%s 最初は `### 入り`" % sc["name"])
        if not heads or heads[-1] != "締め": bad.append("%s 最後は `### 締め`" % sc["name"])
        hands = [p for p in sc["parts"] if p["head"].startswith("手 ")]
        if len(hands) != 3: bad.append("%s 手が三つない（%d）" % (sc["name"], len(hands)))
        for h in hands:
            lab = h["head"][2:].strip()
            for w in NG_LABEL:
                if w in lab: bad.append("札「%s」に評価語「%s」がある" % (lab, w))
            if len(lab) > 26: bad.append("札が長い（%d字）: %s" % (len(lab), lab))
        for p in sc["parts"]:
            for txt in list(p["base"].values()) + [x for o in p["ov"].values() for x in o.values()]:
                for w in NG:
                    if w in txt: bad.append("%s に「%s」がある。封か値の中身" % (sc["name"], w))
            for lid, o in p["ov"].items():
                who = split_who(p["base"][lid]).get("who")
                if who and who != "汐里":
                    bad.append("%s %s は%sの台詞。帯で書き分けない" % (sc["name"], lid, who))
        for k, v in others.items():
            if v is not None and v == sc["at"]:
                bad.append("%s が線香%d本。%s と重なる" % (sc["name"], sc["at"], k))
        out.append({"place": sc["place"], "at": sc["at"], "name": sc["name"],
                    "enter": pack([p for p in sc["parts"] if p["head"] == "入り"][0], "手" + sc["name"]),
                    "hands": [dict(pack(h), label=h["head"][2:].strip()) for h in hands],
                    "close": pack([p for p in sc["parts"] if p["head"] == "締め"][0])})
    ats = sorted(x["at"] for x in out)
    for a, b in zip(ats, ats[1:]):
        if a == b: bad.append("線香%d本で二つ起きる" % a)

    for x in bad: print("NG  " + x)
    n = sum(len(p["base"]) for sc in S for p in sc["parts"])
    print("取り消せない手 %d場面（全%d行）" % (len(out), n))
    for o in out:
        print("   %-5s 線香%-3d %s　手 %s" % (o["place"], o["at"], o["name"],
              "／".join(h["label"] for h in o["hands"])))
    print("不備 %d 件" % len(bad))
    if bad: sys.exit(1)

    blob = "var TE=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
    if HEAD not in g: raise SystemExit("game.html に %s が無い" % HEAD)
    a, b = g.index(HEAD), g.index(TAIL, g.index(HEAD))
    io.open(DST, "w", encoding="utf-8").write(g[:a] + HEAD + "\n" + blob + "\n" + g[b:])
    print("game.html を更新")
