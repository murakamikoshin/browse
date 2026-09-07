#!/usr/bin/env python3
"""夜の行動（会話）を game.html に流し込む。

一本につき線香一本。用意した数が線香より多くないと、誰がやっても同じ夜になる。
原稿は scenario/step6_talks.md。書式は：

    ## T01　仏間　凪さん　凪さんに、美波のことを訊く
    [L001] 凪さんは少しだけ笑った。
    [L002] 「よく喋るようになったのよ」

    帯3
    [L002] 書き換えた一行

相手が居ない行動（自分で見る、思い出す）は相手の欄を — にする。
"""
import io, re, sys, json

PLACE = {"玄関・帳場":"genkan", "仏間":"butsu", "港":"minato",
         "帳場の奥":"cha", "玄関の外":"ishi"}

# 封と購入でしか出てこない事実。夜の行動に混ざったら、無料で渡すことになる。
# 帯の書き換えも同じ線で見る（帯は自己認識まで。他人の秘密は封の側）。
# 「自分で」のような普通の言い方まで止めないよう、封の言い回しごと並べてある。
NG = ["七秒", "発信履歴", "内引", "うちびき", "堤防から落ちたら", "事故になりますか",
      "胴衣を脱いだ", "四月十四日", "四月十九日", "保険金", "借入",
      "自分で海", "自分で入", "自殺", "死のう", "帳を合わせ", "精算", "抜いた金"]

def parse(path="scenario/step6_talks.md"):
    t = io.open(path, encoding="utf-8").read()
    out = []
    for blk in t.split("\n## ")[1:]:
        head, body = (blk.split("\n", 1) + [""])[:2]
        f = re.split(r"[　\t]+|\s{2,}", head.strip())
        if len(f) < 4:
            raise SystemExit("見出しの形が違う: ## " + head.strip())
        tid, place, who, label = f[0], f[1], f[2], "　".join(f[3:])
        if place not in PLACE:
            raise SystemExit("%s 場所が違う: %s（%s のどれか）" % (tid, place, " / ".join(PLACE)))
        lines, ov, order, band, need, late = {}, {}, [], None, None, None
        for l in body.split("\n"):
            l = l.rstrip()
            if not l.strip() or l.startswith(("（", ">", "---")): continue
            m = re.match(r"^帯([2-5])\s*$", l.strip())
            if m: band = int(m.group(1)); continue
            m = re.match(r"^\[あと\]\s*([1-7])\s*$", l)     # その章を読むまで出さない
            if m: need = m.group(1); continue
            m = re.match(r"^\[線香\]\s*(\d+)\s*$", l)          # 夜が更けてから出る手
            if m: late = int(m.group(1)); continue
            m = re.match(r"^\[(L\d+)\]\s*(.*)$", l)
            if not m: continue
            lid, txt = m.group(1), m.group(2).strip()
            if band is None:
                if lid in lines: raise SystemExit("%s %s が二度ある" % (tid, lid))
                lines[lid] = txt; order.append(lid)
            else:
                if lid not in lines: raise SystemExit("%s 帯%d の %s は帯1に無い" % (tid, band, lid))
                ov.setdefault(str(order.index(lid)), {})[str(band)] = txt
        if not order: raise SystemExit("%s に本文が無い" % tid)
        out.append({"k": tid.lower(), "place": PLACE[place], "who": None if who == "—" else who,
                    "label": label, "lines": [lines[i] for i in order],
                    **({"need": need} if need else {}),
                    **({"late": late} if late else {}),
                    **({"ov": ov} if ov else {})})
    return out

def check(talks, incense):
    bad, seen = [], {}
    by = {}
    for t in talks:
        by[t["place"]] = by.get(t["place"], 0) + 1
        if t["k"] in seen: bad.append("%s が二度ある" % t["k"])
        seen[t["k"]] = 1
        if len(t["label"]) > 26: bad.append("%s 選択肢が長い（%d字）" % (t["k"], len(t["label"])))
        n = sum(len(x) for x in t["lines"])
        if n < 60:  bad.append("%s 本文が短い（%d字）" % (t["k"], n))
        if n > 700: bad.append("%s 本文が長い（%d字）。250〜400字で" % (t["k"], n))
    # 一画面に収める。ある時点でその場に並ぶ手が多すぎると、頁が動く
    for k in by:
        early = [t for t in talks if t["place"] == k and not t.get("late")]
        if len(early) > 9:
            bad.append("%s に、夜の初めから並ぶ手が %d 本ある。九本までにする（[線香] で後半へ回す）"
                       % (k, len(early)))
    for t in talks:
        texts = list(t["lines"]) + [v for d in (t.get("ov") or {}).values() for v in d.values()]
        for s in texts:
            for w in NG:
                if w in s:
                    bad.append("%s に封の語が入っている: %s" % (t["k"], w))
    if len(talks) <= incense:
        bad.append("行動 %d 本に対し線香 %d 本。全部できてしまい夜が選択にならない" % (len(talks), incense))
    # 帯の段は夜の中でも上がる。ある帯だけ痩せていると、その額の段が
    # 「払っても夜が変わらない段」になる。段差は機械で見る。
    ov = {}
    for t in talks:
        for d in (t.get("ov") or {}).values():
            for b in d: ov[b] = ov.get(b, 0) + 1
    for b in ("2", "3", "4", "5"):
        if ov.get(b, 0) * 2 < max(ov.values() or [0]):
            bad.append("帯%s の書き換えが %d行しかない（いちばん多い帯の半分未満）。"
                       "この額の段は、夜が変わらない段になる" % (b, ov.get(b, 0)))
    for k in ("genkan", "butsu", "minato", "cha"):
        if not by.get(k): bad.append("%s に行動が一つも無い" % k)
    return bad, by

if __name__ == "__main__":
    g = io.open("game.html", encoding="utf-8").read()
    incense = int(re.search(r"var INCENSE=(\d+);", g).group(1))
    try:
        talks = parse()
    except FileNotFoundError:
        print("scenario/step6_talks.md がありません。発注文は PROMPT.md のステップ6")
        sys.exit(1)
    bad, by = check(talks, incense)
    for b in bad: print("NG  " + b)
    print("\n行動 %d 本（%d行） 線香 %d 本" % (talks and len(talks) or 0,
          sum(len(t["lines"]) for t in talks), incense))
    for k, v in by.items(): print("   %-7s %d" % (k, v))
    ovn = {}
    for t in talks:
        for d in (t.get("ov") or {}).values():
            for b in d: ovn[b] = ovn.get(b, 0) + 1
    print("   帯の書き換え %s（書き分けを持つ行動 %d本）"
          % ("／".join("帯%s %d行" % (b, ovn.get(b, 0)) for b in ("2", "3", "4", "5")),
             sum(1 for t in talks if t.get("ov"))))
    print("不備 %d 件" % len(bad))
    if bad: sys.exit(1)
    blob = "var TALK=" + json.dumps(talks, ensure_ascii=False, separators=(",", ":")) + ";"
    a, b = g.index("var TALK=["), g.index("\n\n/* 夜に灯る線香の数。")
    io.open("game.html", "w", encoding="utf-8").write(g[:a] + blob + g[b:])
    print("game.html を更新")
