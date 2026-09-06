#!/usr/bin/env python3
"""ふりがなの辞書を game.html に流し込む。

本文を形態素に割り、漢字の連なりごとに読みを当てる。読みは janome（IPADIC）から取り、
同じ表記に二つ以上の読みが出たものと、辞書が読めなかったものは `ruby_fix.md` で手当てする。
文中への埋め込みはしない。**辞書だけを積んで、描画のときに当てる。**
原稿を書き換えないので、指せる語句も帯の書き換えも壊れない。

  python3 tools/build_ruby.py --report   当たらなかった語と読みの割れを出す
  python3 tools/build_ruby.py            辞書を作って流し込む
"""
import io, re, sys, json
from janome.tokenizer import Tokenizer

KANJI = re.compile(r'[\u4e00-\u9fff々〆ヶ]+')
HAS_K = re.compile(r'[\u4e00-\u9fff々〆]')

def kata2hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヴ" else c for c in s)

def fixes():
    """手当て表。表記→読み。辞書より優先する。"""
    d = {}
    try:
        t = io.open("scenario/ruby_fix.md", encoding="utf-8").read()
    except FileNotFoundError:
        return d
    for l in t.split("\n"):
        m = re.match(r'^([\u4e00-\u9fff々〆ヶぁ-んァ-ヴー]+)[\s\t]+([ぁ-ん・ー]+)\s*$', l.strip())
        if m: d[m.group(1)] = m.group(2)
    return d

def strings():
    """game.html の中の本文をぜんぶ集める。注釈と識別子は入れない。"""
    g = io.open("game.html", encoding="utf-8").read()
    g = re.sub(r"/\*.*?\*/", " ", g, flags=re.S)          # 注釈は辞書に入れない
    g = re.sub(r"^\s*//.*$", " ", g, flags=re.M)
    out = []
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', g):     # 文字列リテラル
        s = m.group(1)
        if HAS_K.search(s): out.append(s)
    for m in re.finditer(r'>([^<>]*)<', g):                 # 画面に出る素の文字
        s = m.group(1).strip()
        if HAS_K.search(s): out.append(s)
    return out

def align(surface, reading):
    """表記と読みを突き合わせて、漢字の連なりごとの読みを返す。"""
    if not HAS_K.search(surface): return []
    if not reading or reading == "*": return None
    r = kata2hira(reading)
    parts = re.split(r'([\u4e00-\u9fff々〆ヶ]+)', surface)
    pat, runs = "", []
    for p in parts:
        if not p: continue
        if KANJI.fullmatch(p): pat += "(.+?)"; runs.append(p)
        else: pat += re.escape(kata2hira(p))
    m = re.fullmatch(pat, r)
    if not m: return None
    return list(zip(runs, m.groups()))

if __name__ == "__main__":
    tk, fx = Tokenizer(), fixes()
    got, miss = {}, {}
    def units(s):
        """続いた漢字だけの語はつなげて一語にする。芳名／帳 を 芳名帳 に戻すため。"""
        buf = []
        for t in tk.tokenize(s):
            if KANJI.fullmatch(t.surface) and t.reading and t.reading != "*":
                buf.append((t.surface, t.reading)); continue
            if buf:
                yield "".join(x for x, _ in buf), "".join(y for _, y in buf); buf = []
            yield t.surface, t.reading
        if buf: yield "".join(x for x, _ in buf), "".join(y for _, y in buf)

    for s in strings():
        for surface, reading in units(s):
            pairs = align(surface, reading)
            if pairs is None:
                for run in KANJI.findall(surface):
                    if run not in fx: miss[run] = miss.get(run, 0) + 1
                continue
            key = surface
            val = "|".join(y for _, y in pairs)
            got.setdefault(key, {})
            got[key][val] = got[key].get(val, 0) + 1
    split = {k: v for k, v in got.items() if len(v) > 1 and k not in fx}
    if "--report" in sys.argv:
        print("読めなかった語 %d" % len(miss))
        for k, n in sorted(miss.items(), key=lambda x: -x[1]): print("   %-8s %d" % (k, n))
        print("\n読みが割れた語 %d" % len(split))
        for k, v in sorted(split.items()): print("   %-8s %s" % (k, "  ".join("%s(%d)" % x for x in sorted(v.items(), key=lambda y: -y[1]))))
        sys.exit(0)
    d = {k: max(v.items(), key=lambda x: x[1])[0] for k, v in got.items()}
    d.update(fx)
    d = {k: v for k, v in d.items() if v and v != k}
    blob = "var RUBY=" + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + ";"
    g = io.open("game.html", encoding="utf-8").read()
    a, b = g.index("/* ふりがな ここから */"), g.index("/* ふりがな ここまで */")
    io.open("game.html", "w", encoding="utf-8").write(
        g[:a] + "/* ふりがな ここから */\n" + blob + "\n" + g[b:])
    print("game.html を更新　ふりがな %d語（手当て %d／読めず %d／割れ %d）"
          % (len(d), len(fx), len(miss), len(split)))
