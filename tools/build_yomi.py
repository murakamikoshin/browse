#!/usr/bin/env python3
"""額の読みを game.html に流し込む。

朝、町の前で読まれるのは「残った額」である。その数の**形**（頭の数字）と、
切りのよさ（端）と、町の額と並べたときの**格**を、汐里が聞き取る。
帯でも封でもない三本目の軸で、額そのものからしか決まらないので、
帯（自己認識）とも残高（開く封）とも交わらない。

原稿は scenario/step12_yomi.md。書式は：

    ## 形 8
    受	章1で袋を見るときの一行
    読	朝に聞こえる行
    読	朝に聞こえる行

  python3 tools/build_yomi.py
"""
import io, re, sys, json

SRC = "scenario/step12_yomi.md"
DST = "game.html"
HEAD = "/* 額の読み ここから */"
TAIL = "/* 額の読み ここまで */"

# 封と購入でしか出てこない事実。ここに混ぜたら、額を包んだだけで渡すことになる
NG = ["七秒", "発信履歴", "留守番電話", "内引", "不足", "保険金", "借入", "胴衣を脱いだ",
      "自分で海", "自殺", "抜いた額", "精算書", "第一封", "第二封", "第三封", "第四封",
      "開封", "エンディング", "結末"]
# 読み上げ済みでない町の額を出していないか（芳名帳で読まれるのはこの三つだけ）
TOWN_OK = ["一万", "三万"]

KEYS = ["端金", "下", "並", "上", "桁", "外"]
ZERO = "無"   # ¥0 専用。夜に見る一行だけを持つ

def parse(path=SRC):
    t = io.open(path, encoding="utf-8").read()
    shape, kaku, hasu = {}, {}, None
    for blk in t.split("\n## ")[1:]:
        head, body = (blk.split("\n", 1) + [""])[:2]
        f = re.split(r"[　\s]+", head.strip())
        uke, mi, yomi = None, None, []
        for l in body.split("\n"):
            m = re.match(r"^受[\s\t]+(.+)$", l.rstrip())
            if m: uke = m.group(1).strip(); continue
            m = re.match(r"^見[\s\t]+(.+)$", l.rstrip())
            if m: mi = m.group(1).strip(); continue
            m = re.match(r"^読[\s\t]+(.+)$", l.rstrip())
            if m: yomi.append(m.group(1).strip())
        if f[0] == "形":
            d = f[1]
            if d not in list("123456789") + ["切"]: raise SystemExit("形の数字が違う: " + d)
            shape[d] = {"uke": uke, "yomi": yomi}
        elif f[0] == "端":
            hasu = {"yomi": yomi}
        elif f[0] == "格":
            k = f[1]
            if k not in KEYS + [ZERO]:
                raise SystemExit("格の名が違う: %s（%s）" % (k, "／".join(KEYS + [ZERO])))
            kaku[k] = {"yomi": yomi, "mi": mi}
        else:
            raise SystemExit("見出しが違う: ## " + head.strip())
    return shape, hasu, kaku

def check(shape, hasu, kaku):
    bad = []
    if sorted(shape) != sorted(list("123456789") + ["切"]):
        bad.append(("形", "一から九と、切が揃っていない"))
    if not hasu: bad.append(("端", "無い"))
    for k in KEYS + [ZERO]:
        if k not in kaku: bad.append(("格 " + k, "無い"))
    for k in KEYS + [ZERO]:
        if k in kaku and not kaku[k].get("mi"): bad.append(("格 " + k, "見（夜の一行）が無い"))
    # ¥0 は朝に読まれないので、読の行を持ってはいけない
    if kaku.get(ZERO, {}).get("yomi"): bad.append(("格 " + ZERO, "¥0 は朝に読まれない。読は置かない"))
    all_t = []
    for d, v in shape.items():
        if not v["uke"]: bad.append(("形 " + d, "受が無い"))
        if len(v["yomi"]) < 3: bad.append(("形 " + d, "読が三行に足りない"))
        all_t += [v["uke"] or ""] + v["yomi"]
    for k, v in kaku.items(): all_t += v["yomi"] + ([v["mi"]] if v.get("mi") else [])
    if hasu: all_t += hasu["yomi"]
    for t in all_t:
        for ng in NG:
            if ng in t: bad.append((t[:16], "封か買い物の語: " + ng))
        # 町の額は、朝までに読み上げられたものしか引かない
        for m in re.finditer(r"([一二三四五六七八九十百千]+万)円", t):
            if m.group(1) not in TOWN_OK:
                bad.append((t[:16], "読み上げていない町の額: " + m.group(0)))
        # 帯で書き分けないので、解釈を断定する語を置かない
        for ng in ["ということだ", "つまり", "だからだ"]:
            if ng in t: bad.append((t[:16], "因果を書いている: " + ng))
    return bad

if __name__ == "__main__":
    shape, hasu, kaku = parse()
    bad = check(shape, hasu, kaku)
    if bad:
        print("不備 %d 件" % len(bad))
        for a, b in bad: print("   %-18s %s" % (a, b))
        sys.exit(1)
    blob = ("var YOMI={\"shape\":" + json.dumps(shape, ensure_ascii=False)
            + ",\"hasu\":" + json.dumps(hasu, ensure_ascii=False)
            + ",\"kaku\":" + json.dumps(kaku, ensure_ascii=False) + "};")
    g = io.open(DST, encoding="utf-8").read()
    a, b = g.index(HEAD), g.index(TAIL)
    io.open(DST, "w", encoding="utf-8").write(g[:a] + HEAD + "\n" + blob + "\n" + g[b:])
    print("額の読み　形%d／端1／格%d（うち夜に見る一行 %d）　不備 0 件"
          % (len(shape), len(kaku), sum(1 for v in kaku.values() if v.get("mi"))))
    print("game.html を更新")
