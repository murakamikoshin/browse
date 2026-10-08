#!/usr/bin/env python3
"""客に出す一枚を書き出す。検証用の口を落として release/game.html にする。

`docs/RELEASE.md`「客側から消すもの」のうち、機械でできる二つをやる——

  * `window.__dev` と `window.__t`（STEPS・jump・begin・log ほか全部）
  * 「検証用：指せる語句を光らせる」の欄（`.dev`）

**三つ目（封の本文・帯4/5・最終行を初期の一枚から抜く）はやらない。**
あれはサーバが要る話で、出し方が決まってからでないと形が決められない。

  python3 tools/build_release.py          release/game.html を書き出す
  python3 tools/build_release.py --check  書き出さずに、落とせるかだけ見る
"""
import io, os, re, sys

SRC = "game.html"
OUT = os.path.join("release", "game.html")
CUTS = [("<!-- 検証用の欄 ここから", "<!-- 検証用の欄 ここまで -->"),
        ("/* 検証用の口 ここから", "/* 検証用の口 ここまで */")]
# 落としたあとに残っていてはいけない語
BAN = ["window.__dev", "window.__t", '$("mk")', '$("again")', 'id="mk"', 'id="again"']


def cut(s):
    bad = []
    for a, z in CUTS:
        i = s.find(a)
        j = s.find(z)
        if i < 0 or j < 0 or j < i:
            bad.append("印が見つからない: %s" % a.strip())
            continue
        s = s[:i] + s[j + len(z):]
    return s, bad


if __name__ == "__main__":
    s = io.open(SRC, encoding="utf-8").read()
    before = len(s)
    s, bad = cut(s)
    left = [w for w in BAN if w in s]
    if left:
        bad.append("落としたのに残っている: " + "／".join(left))
    # 口を外しても呼ばれる所が無いこと（$("dev") は守ってある）
    for pat in [r'(?<!var d=)\$\("dev"\)\.hidden']:
        if re.search(pat, s):
            bad.append("検証用の欄を直に触っている所がある: " + pat)
    for b in bad:
        print("NG  " + b)
    print("game.html %.0f KB → 客に出す一枚 %.0f KB（%.1f KB 落ちた）"
          % (before / 1024, len(s) / 1024, (before - len(s)) / 1024))
    if bad:
        sys.exit(1)
    if "--check" in sys.argv:
        print("落とせる。書き出していない（--check）")
        sys.exit(0)
    os.makedirs("release", exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(s)
    print("%s を書き出した" % OUT)
    print("※ 封の本文を一枚から抜くのは、出し方が決まってから（docs/RELEASE.md）")
