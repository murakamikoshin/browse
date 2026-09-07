#!/usr/bin/env python3
"""本文の見た目を機械で見る。読み返しでは落ちるものだけを拾う。

 - 「」（）の開きと閉じが合っていない行
 - 、、 や 。。 のような重なり、行末の空白
 - 句点で終わっていない地の文
 - 別々のところに、同じ一行がそのまま二度ある（書き写しの取りこぼし）
 - 長すぎる行（窓からはみ出す）

叩くと報告だけ出る。直すかどうかは人が決める。

  python3 tools/check_prose.py
"""
import io, re, json, sys

def blocks():
    """game.html の中から、画面に出る本文を（出どころ付きで）集める。"""
    g = io.open("game.html", encoding="utf-8").read()
    out = []
    m = re.search(r"\nvar CH = (\{.*?\});\n", g, re.S)
    if m:
        for ch, d in json.loads(m.group(1)).items():
            for lid in d["order"]:
                v = d["base"].get(lid)
                if isinstance(v, str): out.append(("章%s %s" % (ch, lid), v))
                elif isinstance(v, dict):
                    for k2, s in v.items():
                        if isinstance(s, str): out.append(("章%s %s(%s)" % (ch, lid, k2), s))
            for lid, o in (d.get("ov") or {}).items():
                for b, s in o.items(): out.append(("章%s %s 帯%s" % (ch, lid, b), s))
    m = re.search(r"\nvar TALK=(\[.*?\]);\n", g, re.S)
    if m:
        for t in json.loads(m.group(1)):
            for i, s in enumerate(t["lines"]): out.append(("%s L%03d" % (t["k"], i + 1), s))
            for i, o in (t.get("ov") or {}).items():
                for b, s in o.items(): out.append(("%s L%03d 帯%s" % (t["k"], int(i) + 1, b), s))
    return out

PAIRS = [("「", "」"), ("（", "）"), ("『", "』")]

# わざとそう書いてある行。新しく出たものだけが目に入るように、ここへ避ける。
OK = {
    # 言いよどんで、次の行が「言葉が見つからなかった」で受ける
    "t53 L005": "句点で終わっていない",
    # 父の葬式の朝を思い出す一段落。窓は折り返すので、長いままでよい
    "章1 L039 帯5": "長い",
}

if __name__ == "__main__":
    rows = blocks()
    bad, seen = [], {}
    for where, s in rows:
        for a, b in PAIRS:
            if s.count(a) != s.count(b):
                bad.append((where, "括弧が合っていない: " + s[:28]))
        for w in ("、、", "。。", "  ", "！！", "、。", "。、"):
            if w in s: bad.append((where, "重なり「%s」: %s" % (w, s[:28])))
        if s != s.strip(): bad.append((where, "前後に空白: " + s[:28]))
        if len(s) > 120: bad.append((where, "長い（%d字）: %s" % (len(s), s[:28])))
        if s and s[-1] not in "。」』？！…—-":
            bad.append((where, "句点で終わっていない: " + s[-24:]))
        if len(s) > 18:
            # ¥0 と ¥100〜 で分岐しない行は、同じ文が両方に入る。これは仕様
            key = re.sub(r"\((zero|paid)\)", "", where)
            if s in seen and re.sub(r"\((zero|paid)\)", "", seen[s]) != key:
                bad.append((where, "同じ一行が %s にもある: %s" % (seen[s], s[:24])))
            elif s not in seen: seen[s] = where
    keep = [(w, m) for w, m in bad if not (w in OK and m.startswith(OK[w]))]
    print("見た行 %d（わざとそう書いてある行 %d を除く）" % (len(rows), len(OK)))
    for w, m in keep: print("   %-18s %s" % (w, m))
    print("\n気になるところ %d件" % len(keep))
