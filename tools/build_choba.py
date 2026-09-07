#!/usr/bin/env python3
"""帳場さんの帳を game.html に流し込む。見た結末の数で開く。

封の中身に触れていないかを機械でも見る。触れていたら、無料で集めた人に
課金の中身を配ることになるので、そこだけは落ちないようにする。
"""
import io, re, sys, json

NG = ["七秒", "発信履歴", "内引", "「内」", "うちびき", "堤防から落ちたら",
      "事故になりますか", "息を吸", "胴衣", "四月十四日", "四月十九日",
      "汐里に、もう", "保険", "百万", "抜いて", "相応"]

def parse():
    t = io.open("scenario/step9_choba.md", encoding="utf-8").read()
    out = []
    for blk in t.split("\n## ")[1:]:
        head, body = blk.split("\n", 1)
        m = re.match(r'^(\d+)[　\s]+(\S+)\s*$', head.strip())
        if not m: raise SystemExit("見出しの形が違う: ## " + head.strip())
        lines = [x.group(1).strip() for x in
                 (re.match(r'^\[L\d+\]\s*(.+)$', l.rstrip()) for l in body.split("\n")) if x]
        if not lines: raise SystemExit("%s が空" % m.group(2))
        out.append({"n": int(m.group(1)), "title": m.group(2), "lines": lines})
    return sorted(out, key=lambda x: x["n"])

def numbers(d):
    """帳場さんの帳が言う数と、実装の数が食い違っていないか。
    線香の本数を変えたのに、帳場さんが古い数を言い続けていたことがある。"""
    import re
    g = io.open("game.html", encoding="utf-8").read()
    inc = int(re.search(r"var INCENSE=(\d+);", g).group(1))
    KAN = "〇一二三四五六七八九十"
    def kan(n):
        if n < 10: return KAN[n]
        if n < 20: return "十" + (KAN[n % 10] if n % 10 else "")
        return KAN[n // 10] + "十" + (KAN[n % 10] if n % 10 else "")
    want = "線香は" + kan(inc) + "本"
    body = "".join("".join(s["lines"]) for s in d)
    out = []
    if "線香は" in body and want not in body:
        out.append("帳場さんの帳が言う線香の数が、実装（%d本）と違う。「%s」になっているはず" % (inc, want))
    return out


if __name__ == "__main__":
    d, bad = parse(), []
    bad += numbers(d)
    for s in d:
        body = "".join(s["lines"])
        for w in NG:
            if w in body: bad.append("%s に「%s」がある。封か購入の中身に触れている" % (s["title"], w))
        if len(body) < 150: bad.append("%s が短い（%d字）" % (s["title"], len(body)))
    for b in bad: print("NG  " + b)
    print("\n帳場さんの帳 %d節（%d行 %d字）"
          % (len(d), sum(len(x["lines"]) for x in d), sum(len("".join(x["lines"])) for x in d)))
    for x in d: print("   結末%2d で開く　%-6s %2d行" % (x["n"], x["title"], len(x["lines"])))
    print("不備 %d 件" % len(bad))
    if bad: sys.exit(1)
    blob = "var CHOBA=" + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + ";"
    g = io.open("game.html", encoding="utf-8").read()
    a, b = g.index("/* 帳場さんの帳 ここから */"), g.index("/* 帳場さんの帳 ここまで */")
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + "/* 帳場さんの帳 ここから */\n" + blob + "\n" + g[b:])
    print("game.html を更新")
