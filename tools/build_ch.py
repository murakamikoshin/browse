#!/usr/bin/env python3
"""第1〜6章の本文を game.html 用の JS データに変換する。

第7章と違い、ここは帯だけで分岐が閉じる。行は次の三つの形しか取らない。

    [L001] 本文                 … 帯1の本文（¥0でも¥100〜でも同じ）
    [L042 ¥100〜] 本文          … 包んだ人だけが読む帯1の本文
    [L042 ¥0] 本文              … 包まなかった人だけが読む本文

本文の代わりに [P …] が入っている行は、原稿に残した制作の覚え書きで、本文ではない。
行番号だけ取って、本文からは落とす（game.html の行数は原稿の L の数より少ない）。

帯2〜5の書き換えは step2 側に置く。書かれていない帯は、その下の帯を引き継ぐ
（引き継ぎは game.html 側で解く。ここでは書かれた帯だけを渡す）。

    python3 tools/build_ch.py            game.html を書き換える
    python3 tools/build_ch.py --check    いまの game.html との差だけ出す
"""
import io, re, json, sys

CHAPTERS = ["1", "2", "3", "4", "5", "6"]
VAR = {"¥0": "zero", "¥100〜": "paid"}


def chapter(n):
    order, base, ov, notes = [], {}, {}, []
    b1 = io.open("scenario/step1_ch%s_band1.md" % n, encoding="utf-8").read()
    for l in b1[b1.index("[L001]"):].split("\n"):
        m = re.match(r'^\[(L\d+)(?:\s+(\S+))?\]\s*(.*)$', l)
        if not m: continue
        lid, var, txt = m.groups()
        if txt.startswith("[P"):                       # 制作の覚え書き。本文ではない
            notes.append(lid)
            continue
        if lid not in base:
            base[lid] = {}
            order.append(lid)
        if var is None:
            base[lid]["paid"] = base[lid]["zero"] = txt
        else:
            assert var in VAR, (n, lid, var)
            base[lid][VAR[var]] = txt
    for lid in order:
        assert set(base[lid]) == {"paid", "zero"}, (n, lid, sorted(base[lid]))

    b2 = io.open("scenario/step2_ch%s_bands.md" % n, encoding="utf-8").read()
    cur = None
    for l in b2.split("\n"):
        m = re.match(r'^\[(L\d+)(?:\s+\S+?)?\]$', l.strip())
        if m:
            cur = m.group(1)
            if cur in notes: cur = None; continue
            assert cur in base, ("step2 に本文の無い行がある", n, cur)
            continue
        m2 = re.match(r'^帯(\d):\s*(.*)$', l)
        if m2 and cur:
            band, txt = m2.groups()
            assert band in "2345", (n, cur, band)
            ov.setdefault(cur, {})[band] = txt
    return {"order": order, "base": base, "ov": ov}


if __name__ == "__main__":
    ch = {n: chapter(n) for n in CHAPTERS}
    blob = "var CH = " + json.dumps(ch, ensure_ascii=False) + ";"

    g = io.open("game.html", encoding="utf-8").read()
    a = g.index("var CH = ")
    b = g.index("\n", a)
    same = g[a:b] == blob
    if "--check" in sys.argv:
        print("game.html と一致" if same else "game.html と食い違っている（--check なしで書き換わる）")
        if not same:
            old = json.loads(g[a + len("var CH = "):b].rstrip().rstrip(";"))
            for n in CHAPTERS:
                o, w = old.get(n, {}), ch[n]
                if o.get("order") != w["order"]:
                    print("  章%s 行の並びが違う（%d → %d行）" % (n, len(o.get("order", [])), len(w["order"])))
                for lid in w["order"]:
                    for k in ("paid", "zero"):
                        if o.get("base", {}).get(lid, {}).get(k) != w["base"][lid][k]:
                            print("  章%s %s %s\n    旧 %s\n    新 %s" % (
                                n, lid, k, o.get("base", {}).get(lid, {}).get(k), w["base"][lid][k]))
                    ob, nb = o.get("ov", {}).get(lid, {}), w["ov"].get(lid, {})
                    for band in sorted(set(ob) | set(nb)):
                        if ob.get(band) != nb.get(band):
                            print("  章%s %s 帯%s\n    旧 %s\n    新 %s" % (n, lid, band, ob.get(band), nb.get(band)))
        sys.exit(0)

    io.open("game.html", "w", encoding="utf-8").write(g[:a] + blob + g[b:])
    print("game.html を更新" if not same else "game.html は元から一致していた（書き換えなし）")
    for n in CHAPTERS:
        c = ch[n]
        zero = sum(1 for lid in c["order"] if c["base"][lid]["paid"] != c["base"][lid]["zero"])
        rew = sum(len(v) for v in c["ov"].values())
        print("  第%s章 %2d行　¥0で変わる行 %d　帯の書き換え %2d箇所（%d行）"
              % (n, len(c["order"]), zero, rew, len(c["ov"])))
