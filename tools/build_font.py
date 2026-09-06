#!/usr/bin/env python3
"""fonts/ の書体を、この作品が使う文字だけに削って game.html に焼き込む。

artifact では外部のフォントを読めない（CSPで fonts.gstatic.com 以外は遮断される）ので、
焼き込む以外に道がない。日本語フォントは丸ごとだと数MBあるが、使う文字だけなら数百KBに収まる。

  python3 tools/build_font.py            削って焼き込む
  python3 tools/build_font.py --check    無い文字を並べるだけ
  python3 tools/build_font.py --ruby     ふりがなにも使う（既定は使わない）
"""
import io, os, re, sys, glob, base64
from fontTools import subset
from fontTools.ttLib import TTFont

CAP = 1_200_000          # base64にすると1.33倍。ここを超えたら使う場所を絞る

def chars():
    """game.html が画面に出しうる文字を全部集める。注釈と識別子は入れない。"""
    g = io.open("game.html", encoding="utf-8").read()
    g = re.sub(r"/\*.*?\*/", " ", g, flags=re.S)
    g = re.sub(r"^\s*//.*$", " ", g, flags=re.M)
    s = set()
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', g): s.update(m.group(1))
    for m in re.finditer(r'>([^<>]*)<', g):          s.update(m.group(1))
    s.update("0123456789¥／・ー〜（）「」『』…—　")
    return {c for c in s if c.strip() and ord(c) > 0x20}

def find():
    for p in sorted(glob.glob("fonts/*")):
        if os.path.splitext(p)[1].lower() in (".otf", ".ttf", ".woff2", ".woff", ".ttc"):
            return p
    return None

if __name__ == "__main__":
    p = find()
    if not p:
        print("fonts/ に書体がありません（fonts/README.md）"); sys.exit(0)
    want = chars()
    f = TTFont(p, fontNumber=0)
    have = set()
    for t in f["cmap"].tables: have.update(chr(c) for c in t.cmap)
    miss = sorted(want - have)
    print("%s  収録 %d字 ／ この作品が使う %d字" % (os.path.basename(p), len(have), len(want)))
    if miss:
        print("\n**この書体に無い文字 %d字**（落ちずに次の書体で出るが、そこだけ書体が混ざる）" % len(miss))
        print("   " + " ".join(miss))
    else:
        print("\n無い文字はありません")
    if "--check" in sys.argv: sys.exit(0)

    use = "".join(sorted(want & have))
    out = "/tmp/subset.woff2"
    subset.main([p, "--text=" + use, "--flavor=woff2", "--layout-features=*",
                 "--no-hinting", "--desubroutinize", "--output-file=" + out])
    b = io.open(out, "rb").read()
    print("\n削った結果 %.0f KB（焼き込むと %.0f KB）" % (len(b)/1024, len(b)*4/3/1024))
    if len(b) > CAP:
        print("NG  大きすぎます。使う場所を絞ってください"); sys.exit(1)
    face = ('@font-face{font-family:"Craft";font-display:swap;'
            'src:url(data:font/woff2;base64,%s) format("woff2");}'
            % base64.b64encode(b).decode())
    g = io.open("game.html", encoding="utf-8").read()
    a, z = g.index("<!-- 書体 ここから -->"), g.index("<!-- 書体 ここまで -->")
    body = '\n:root{ --mincho:"Craft","Zen Old Mincho","Hiragino Mincho ProN",serif; }\n'
    if "--ruby" not in sys.argv:
        body += 'rt{ font-family:"Zen Old Mincho","Hiragino Mincho ProN",serif; }\n'
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + "<!-- 書体 ここから -->\n<style>" + face + body + "</style>\n" + g[z:])
    print("game.html を更新")
