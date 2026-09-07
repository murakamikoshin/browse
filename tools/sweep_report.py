#!/usr/bin/env python3
"""tools/sweep.mjs の出した JSON を読む。

    node tools/sweep.mjs 60 777 > /tmp/s.json
    python3 tools/sweep_report.py /tmp/s.json
"""
import json,sys,collections
d=json.load(open(sys.argv[1]))
R=d["rows"]
print("== %d周 走らせた ==" % d["N"])
print("行き止まり %d／落ちた %d／六千手超え %d" % (d["dead"], d["crash"],
      sum(1 for r in R if r["warn"] and "六千手" in r["warn"][0])))
if d["errs"]: print("画面の落ち:", d["errs"])
# 手の総数は実装から引く。書き写すと、行動を増やしたときに古い数が残る
try:
    import io as _io, re as _re
    _g = _io.open("game.html", encoding="utf-8").read()
    NT = len(_re.findall(r'"k":"t\d+"', _re.search(r"\nvar TALK=(\[.*?\]);\n", _g, _re.S).group(1)))
except Exception:
    NT = 0
print("覚えた行 %d　到達 手%d/%s 結末%d/85 形%d/10 並び%d/7"
      % (d["seen"], d["talks"], NT or "?", d["eds"], d["sh"], d["ka"]))
print()
print("周ごとの「初めて読んだ行」")
band=[(1,1),(2,3),(4,6),(7,10),(11,15),(16,25),(26,50),(51,100),(101,200),(201,500),(501,1000)]
for lo,hi in band:
    xs=[r["fresh"] for r in R if lo<=r["run"]<=hi]
    ys=[r["lines"] for r in R if lo<=r["run"]<=hi]
    if not xs: continue
    print("  %4d〜%-4d周　平均 初めて %6.1f行 ／ 読んだ %5.1f行　＝ %4.1f%%"
          % (lo,hi,sum(xs)/len(xs),sum(ys)/len(ys),100*sum(xs)/max(1,sum(ys))))
tot=0
for r in R:
    tot+=r["fresh"]
    if tot>=d["seen"]*0.95:
        print("\n**%d周目で、全体の95%%を読み終えている**" % r["run"]); break
w=[r for r in R if r["warn"]]
if w:
    print("\n止まった例:")
    for r in w[:6]: print("  %d周目 額段%d: %s" % (r["run"],r["idx"],r["warn"][0]))
