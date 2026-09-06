# -*- coding: utf-8 -*-
"""題のロゴ（img/logo.png）を削って game.html に焼き込む。

artifact は一枚の HTML なので、img/ を置いても読めない。data URI で持つ以外に道がない。
白一色に透明という素材なので、webp の alpha 付きで十分小さくなる。

  python3 tools/build_logo.py
"""
import io, os, sys, base64
from PIL import Image

SRC = "img/logo.png"
DST = "game.html"
HEAD = "<!-- 題のロゴ ここから -->"
TAIL = "<!-- 題のロゴ ここまで -->"
WIDE = 1100          # 携帯で二倍に見ても足りる幅
Q = 86
CAP = 200 * 1024     # base64にすると1.33倍

if __name__ == "__main__":
    if not os.path.exists(SRC):
        print("%s がありません" % SRC); sys.exit(0)
    im = Image.open(SRC).convert("RGBA")
    im = im.crop(im.getbbox())                      # 余白を落としてから縮める
    w, h = im.size
    r = im.resize((WIDE, round(h * WIDE / w)), Image.LANCZOS)
    b = io.BytesIO(); r.save(b, "WEBP", quality=Q, method=6)
    d = b.getvalue()
    print("%s  %dx%d → %dx%d  %.0f KB（焼き込むと %.0f KB）"
          % (os.path.basename(SRC), w, h, r.width, r.height, len(d)/1024, len(d)*4/3/1024))
    if len(d) > CAP:
        print("NG  大きすぎます"); sys.exit(1)

    # 素材が入ったときだけ、字のほうを引っ込める。無ければ「帳場」の字がそのまま出る
    css = ('<style>.ti-t{ letter-spacing:0; text-indent:0; margin-top:6px; }'
           '.ti-logo{ color:transparent; aspect-ratio:%d/%d;'
           ' background-image:url(data:image/webp;base64,%s); }</style>'
           % (w, h, base64.b64encode(d).decode()))
    g = io.open(DST, encoding="utf-8").read()
    a, z = g.index(HEAD), g.index(TAIL) + len(TAIL)
    io.open(DST, "w", encoding="utf-8").write(
        g[:a] + HEAD + "\n" + css + "\n" + TAIL + g[z:])
    print("game.html を更新")
