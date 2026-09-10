#!/usr/bin/env python3
"""fonts/ の書体を、この作品が使う文字だけに削って game.html に焼き込む。

artifact では外部のフォントを読めない（CSPで fonts.gstatic.com 以外は遮断される）ので、
焼き込む以外に道がない。日本語フォントは丸ごとだと数MBあるが、使う文字だけなら数百KBに収まる。

  python3 tools/build_font.py            削って焼き込む
  python3 tools/build_font.py --check    無い文字を並べるだけ
  python3 tools/build_font.py --ruby     ふりがなにも使う（既定は使わない）
"""
import hashlib, io, os, re, sys, glob, base64
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

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
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    have = set()
    for t in f["cmap"].tables: have.update(chr(c) for c in t.cmap)

    # 字割りだけあって輪郭が無い字がある。クラフト明朝は第二水準の多く（綺・柩・框・鋏・舫）が
    # これで、cmap には載っているので次の書体に落ちてくれない。**そのまま焼くと空白になる。**
    # 削る前にここで外して、端末に入っている明朝へ渡す。
    blank = set()
    for c in want & have:
        g = cmap.get(ord(c))
        if not g: continue
        bp = BoundsPen(gs)
        try: gs[g].draw(bp)
        except Exception: continue
        if bp.bounds is None: blank.add(c)

    miss = sorted(want - have)
    print("%s  収録 %d字 ／ この作品が使う %d字" % (os.path.basename(p), len(have), len(want)))
    if miss:
        print("\n**この書体に無い文字 %d字**（落ちずに次の書体で出るが、そこだけ書体が混ざる）" % len(miss))
        print("   " + " ".join(miss))
    else:
        print("\nこの書体に無い文字はありません")
    if blank:
        print("\n**中身が空の字 %d字**（焼き込むと空白になるので、この書体からは外す）" % len(blank))
        print("   " + " ".join(sorted(blank)))
    use = "".join(sorted((want & have) - blank))
    # woff2 は同じ字を渡しても毎回ちがう塊になる。焼き直すたびに game.html の
    # 七百キロの一行が変わって、本当の直しがその中に埋もれる。**入力は字の集合**
    # なので、集合の指紋を一緒に焼き込んで、変わっていなければ何もしない。
    key = hashlib.sha1(use.encode("utf-8")).hexdigest()[:12]
    g0 = io.open("game.html", encoding="utf-8").read()
    a0, z0 = g0.index("<!-- 書体 ここから -->"), g0.index("<!-- 書体 ここまで -->")
    m0 = re.search(r"<!-- 字 ([0-9a-f]{12}) -->", g0[a0:z0])
    fresh = bool(m0 and m0.group(1) == key)
    if "--check" in sys.argv:
        # 焼き込んである字と、いま本文が使う字が合っているか。合っていないと、
        # あとから足した字だけ端末の書体で出る（そこだけ形が変わる）
        if fresh:
            print("\n焼き込んだ字は本文と合っています（%d字／%s）" % (len(use), key))
            sys.exit(0)
        print("\nNG  焼き込んだ字が古い（いま %d字／%s）。"
              "python3 tools/build_font.py で焼き直すこと" % (len(use), key))
        sys.exit(1)
    if fresh and "--force" not in sys.argv:
        print("\n使う字は変わっていません（%d字／%s）。焼き直しません" % (len(use), key))
        sys.exit(0)
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
    # 外から書体を取りに行かない（privacy.md「外部への通信を行いません」）。
    # 焼き込んだ Craft に無い字は、端末に入っている明朝へ落とす。
    body = '\n:root{ --mincho:"Craft","Hiragino Mincho ProN","Yu Mincho","Noto Serif JP",serif; }\n'
    if "--ruby" not in sys.argv:
        body += 'rt{ font-family:"Hiragino Mincho ProN","Yu Mincho","Noto Serif JP",serif; }\n'
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + "<!-- 書体 ここから -->\n<!-- 字 " + key + " -->\n<style>"
        + face + body + "</style>\n" + g[z:])
    print("game.html を更新")
