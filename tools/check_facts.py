#!/usr/bin/env python3
"""本文が言っている数と、実装の数が食い違っていないかを見る。読むだけ。

このセッションで三度やった間違い：
  ・線香を14→16にしたのに、帳場さんの帳は「線香は十四本」と言い続けていた
  ・手を27→35→70→105と増やしたのに、手がかりは古い数を言っていた
  ・帳場さんの帳が「四十年、同じ机」、夜の行動が「三十年、同じ机」

本文の中の漢数字を拾って、実装の数と突き合わせる。
それと、同じものについて別の数を言っている箇所を並べる。

    python3 tools/check_facts.py
"""
import io, re, json, sys, glob
from collections import defaultdict

KAN = "〇一二三四五六七八九"

def kan(n):
    if n < 10: return KAN[n]
    if n < 20: return "十" + (KAN[n % 10] if n % 10 else "")
    if n < 100: return KAN[n // 10] + "十" + (KAN[n % 10] if n % 10 else "")
    if n < 1000: return KAN[n // 100] + "百" + (kan(n % 100) if n % 100 else "")
    return str(n)

def num(s):
    """漢数字を読む。百五 → 105"""
    s = s.strip()
    if not s: return None
    t = 0; cur = 0
    for ch in s:
        if ch in KAN: cur = KAN.index(ch)
        elif ch == "十": t += (cur or 1) * 10; cur = 0
        elif ch == "百": t += (cur or 1) * 100; cur = 0
        else: return None
    return t + cur

def impl():
    g = io.open("game.html", encoding="utf-8").read()
    def grab(name):
        for pat in ("var %s=" % name, "var %s = " % name):
            if pat in g:
                i = g.index(pat); j = g.index("\n", i)
                return json.loads(g[i + len(pat):j].rstrip().rstrip(";"))
        return None
    return {
        "線香": int(re.search(r"var INCENSE=(\d+);", g).group(1)),
        "行動": len(grab("TALK") or []),
        "引っかかり": len(grab("SNAG") or []),
        "封": len(grab("SEALTEXT") or []),
        "場所": len(re.findall(r'\{ k:"', g[g.index("var PLACES="):g.index("var PLACES=") + 900])),
    }

# 本文が数を言っている型。（正規表現, 実装のどれと比べるか）
CLAIMS = [
    # 「線香は十六本」は総数の宣言。「線香が三本立っていた」は場面の描写なので見ない
    (r"線香は([一二三四五六七八九十]+)本", "線香"),
    (r"用意した行動は([〇一二三四五六七八九十百]+)", "行動"),
    (r"行けるところ(?:は)?([一二三四五六七八九十]+)つ", "場所"),
    (r"襖の紙は([一二三四五六七八九十]+)枚", "封"),
]

def files():
    return sorted(glob.glob("scenario/*.md"))

if __name__ == "__main__":
    I = impl()
    bad, seen = [], defaultdict(list)
    for p in files():
        t = io.open(p, encoding="utf-8").read()
        for ln_no, ln in enumerate(t.split("\n"), 1):
            if ln.startswith(">") or ln.startswith("#"): continue
            for pat, key in CLAIMS:
                for m in re.finditer(pat, ln):
                    n = num(m.group(1))
                    if key and n is not None and n != I[key]:
                        bad.append("%s:%d  「%s」と書いてあるが、実装は %d（%s）"
                                   % (p, ln_no, m.group(0), I[key], kan(I[key])))
            # 「N年、同じ○○」のように、同じものに別の数を言っていないか
            # 「四十年、同じ机」のように、同じものに別の年数を言っていないか。
            # 助詞で終わる語は拾わない（「三年は」などは年数の比較にならない）
            for m in re.finditer(r"([一二三四五六七八九十]+)年[、，]?\s*(?:同じ|この)\s*([^\s、。」]{2,6})", ln):
                seen[m.group(2)].append((p, ln_no, m.group(0)))

    print("実装の数　" + "／".join("%s %d" % (k, v) for k, v in I.items()))
    print()
    print("本文が言う数と、実装の食い違い %d件" % len(bad))
    for b in bad: print("   " + b)

    # 同じ語に、違う年数が付いているもの
    print()
    conf = []
    for word, hits in seen.items():
        yrs = {re.match(r"([一二三四五六七八九十]+)", h[2]).group(1) for h in hits}
        if len(yrs) > 1 and len(hits) > 1:
            conf.append((word, hits))
    print("同じものに違う年数を言っている語 %d件" % len(conf))
    for word, hits in conf:
        print("   「%s」" % word)
        for p, n, s in hits: print("      %s:%d  %s" % (p, n, s))

    print()
    print("不備 %d 件" % len(bad))
    sys.exit(1 if bad else 0)
