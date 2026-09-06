#!/usr/bin/env python3
"""audio/ の音声を game.html に data URI で焼き込む。

artifact では外部の音声ホストが遮断されるので、焼き込む以外に道がない。
置いたファイルだけが差し替わり、無いものは合成音のまま鳴る。

  python3 tools/build_audio.py
"""
import io, os, re, sys, base64, json

WANT = ["nami", "kaze", "heya", "asa", "ki", "kami", "ko", "fusuma", "rin",
        "music_yoru", "music_asa"]
MIME = {".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".wav": "audio/wav"}
CAP = 3 * 1024 * 1024

if __name__ == "__main__":
    d, total = {}, 0
    for k in WANT:
        for ext in MIME:
            p = os.path.join("audio", k + ext)
            if not os.path.exists(p): continue
            b = io.open(p, "rb").read(); total += len(b)
            d[k] = "data:%s;base64,%s" % (MIME[ext], base64.b64encode(b).decode())
            print("   %-8s %-5s %7.1f KB" % (k, ext[1:], len(b) / 1024))
            break
    if not d:
        print("audio/ に音声がありません。合成音のままです（audio/README.md）"); sys.exit(0)
    print("\n合計 %.2f MB" % (total / 1048576))
    if total > CAP:
        print("NG  素材が大きすぎます。data URI にすると 1.33 倍になるので 3MB 以内に")
        sys.exit(1)
    blob = "var SND=" + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + ";"
    g = io.open("game.html", encoding="utf-8").read()
    a, b = g.index("/* 音の素材 ここから */"), g.index("/* 音の素材 ここまで */")
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + "/* 音の素材 ここから */\n" + blob + "\n" + g[b:])
    print("game.html を更新　%d本" % len(d))
