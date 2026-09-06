# -*- coding: utf-8 -*-
"""語注を game.html に流し込む。

scenario/gloss.md を読んで var GLOSS={...} を差し替える。
本文に出てこない語、買える語句と重なる語は落とす。

  python3 tools/build_gloss.py
"""
import io, os, re, sys, json

SRC = "scenario/gloss.md"
DST = "game.html"
HEAD = "/* 語注 ここから */"
TAIL = "/* 語注 ここまで */"

# 意味が物語の側で決まる語。辞書の説明を付けると、封で売っているものと衝突する
NG = ["内引", "帳", "封", "帯", "残高", "精算書", "控え", "指す"]

# 人の名前と重なる語。呼びかけ（さん・様）が続くときは game.html 側でも出さないが、
# 呼びかけ無しでも名前として読める語は、そもそも入れない
NAMES = ["汐里", "美波", "貝原", "巽", "田上", "魚政", "しおり"]


def load():
    d, order = {}, []
    for ln in io.open(SRC, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if not ln or ln.startswith("#") or ln.startswith(">") or ln.startswith("---"):
            continue
        if "　" not in ln:
            continue
        w, t = ln.split("　", 1)
        w, t = w.strip(), t.strip()
        if not w or not t:
            continue
        d[w] = t
        order.append(w)
    return d, order


def corpus(html):
    """本文らしいところを全部つないで、語が実際に出るかを見るための塊にする"""
    out = []
    for name in ["CH", "CH7", "SEALTEXT", "SEALCLOSE", "FINALS", "TALK",
                 "ACTS", "CHOBA", "ASKS"]:
        m = re.search(r"\nvar %s\s*=\s*(.*?);\n" % name, html, re.S)
        if m:
            out.append(m.group(1))
    return "\n".join(out)


def askPhrases(html):
    m = re.search(r"\nvar ASKS\s*=\s*(\{.*?\});\n", html, re.S)
    if not m:
        return []
    return re.findall(r'"phrase"\s*:\s*"(.*?)"', m.group(1)) + \
           re.findall(r'phrase\s*:\s*"(.*?)"', m.group(1))


if __name__ == "__main__":
    d, order = load()
    html = io.open(DST, encoding="utf-8").read()
    body = corpus(html)
    phr = askPhrases(html)

    bad = []
    keep = []
    for w in order:
        if w in NG:
            bad.append((w, "物語の側で意味が決まる語")); continue
        if w in NAMES:
            bad.append((w, "人の名前と重なる")); continue
        hit = [p for p in phr if w in p or p in w]
        if hit:
            bad.append((w, "買える語句と重なる: " + hit[0])); continue
        if w not in body:
            bad.append((w, "本文に出てこない")); continue
        if len(d[w]) > 40:
            bad.append((w, "説明が長い %d字" % len(d[w]))); continue
        keep.append(w)

    out = dict((w, d[w]) for w in keep)
    blob = HEAD + "\nvar GLOSS=" + json.dumps(out, ensure_ascii=False) + ";\n" + TAIL
    a, b = html.index(HEAD), html.index(TAIL) + len(TAIL)
    io.open(DST, "w", encoding="utf-8").write(html[:a] + blob + html[b:])

    print("語注 %d語（用意 %d語）" % (len(keep), len(order)))
    for w, why in bad:
        print("   落とした %-6s %s" % (w, why))
    print("game.html を更新")
