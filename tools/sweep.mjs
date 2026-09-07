/* 何十周も、でたらめに遊ぶ。**飽きを数で測るための道具。**
   verify.mjs はデータが揃っているかを、playtest.mjs は行き止まりが無いかを見る。
   これは「何周目で新しい行が尽きるか」を見る。

     node tools/sweep.mjs 60        六十周
     node tools/sweep.mjs 60 777    種を指定して同じ結果を出す

   出るのは JSON。読むのは tools/sweep_report.py。

   実測（六十周・2026-09）：
     1周目      読んだ633行のうち **581行が初めて**（92%）
     2〜10周    毎周 **50行前後**が初めて（8%）
     11〜25周   **10行前後**（1.5%）
     26周以降   **数行**（0.4%）
     **49周目で、全体の95%を読み終える**
   異なり行はおよそ1,300行しかないので、これは足し算の結果であって不具合ではない。
   何周でも新しくしたければ、本文を増やすほかにない。                            */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const N = Number(process.argv[2] || 200);
const SEED0 = Number(process.argv[3] || 1);
const b = await chromium.launch();
const p = await b.newPage();
const errs = [];
p.on('pageerror', e => errs.push(String(e)));
await p.goto('file:///home/user/browse/game.html');

const seenAll = new Set();          // 通しで覚えた行（人がずっと遊んでいる想定）
const talkAll = new Set(), edAll = new Set(), shAll = new Set(), kaAll = new Set();
const rows = [];
let dead = 0, dup = 0, crash = 0;

for (let run = 0; run < N; run++) {
  await p.goto('file:///home/user/browse/game.html');
  let r;
  try {
    r = await p.evaluate(([seed]) => {
      let s = seed >>> 0;
      const rnd = () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296;
      const D = window.__dev, lines = [], warn = [];
      const bare = () => { const w = document.getElementById('wt'); if (!w) return '';
        const c = w.cloneNode(true); c.querySelectorAll('rt,rp').forEach(x => x.remove());
        return c.textContent.trim(); };
      const labs = () => [...document.querySelectorAll('#nav button')].filter(b => !b.disabled)
        .map(b => b.textContent);
      D.fast(true);
      const idx = Math.floor(rnd() * 38);
      D.begin(idx);
      const talks = [], said = {}; let dups = 0, last = '', guard = 0, stuck = 0;
      while (guard++ < 6000) {
        const st = D.state();
        const t = bare();
        if (t && t !== last) { last = t; lines.push(t);
          if (t.length > 25 && !/^[「（]/.test(t)) { if (said[t]) dups++; else said[t] = 1; } }
        if (st.done && document.querySelector('.slip-ed')) break;
        if (st.chapcard) { D.flush(3); continue; }
        const yy = document.querySelector('#card .cb [data-y]:not([disabled])');
        if (yy && rnd() < .5) { yy.click(); continue; }
        const nn = document.querySelector('#card .cb [data-y][disabled]');
        if (nn) { document.querySelector('#card .cb [data-n]').click(); continue; }
        const n = labs();
        if (!n.length) {
          const before = t;
          if (rnd() < .25) { const a = D.asks().filter(x => !x.used)[0]; if (a) { D.point(a.k); continue; } }
          D.step();
          if (bare() === before) { if (++stuck > 40) { warn.push('行き止まり: ' + before.slice(0,20)); break; } }
          else stuck = 0;
          continue;
        }
        stuck = 0;
        /* 人が遊ぶように、たまに終える。ほとんどは進む */
        const end = n.filter(x => /^(夜を終える|横になる)$/.test(x));
        const rich = n.filter(x => !/^(閉じる|やめる|ほかの場所へ|もう一度読む|夜を終える|横になる|いいえ.*|それでも朝まで横になる)$/.test(x));
        let pick;
        if (rich.length && (end.length === 0 || rnd() < .88)) pick = rich[Math.floor(rnd() * rich.length)];
        else if (n.includes('ほかの場所へ') && rnd() < .7) pick = 'ほかの場所へ';
        else pick = (end[0] || n[Math.floor(rnd() * n.length)]);
        if (/^T?/.test(pick)) {} 
        D.nav(pick);
      }
      if (guard >= 6000) warn.push('六千手で終わらなかった');
      const st = D.state();
      return { idx, lines, warn, dups, ed: st.ed,
               talk: JSON.parse(localStorage.getItem('choba.talk') || '[]'),
               yomi: JSON.parse(localStorage.getItem('choba.yomi') || '{"sh":[],"ka":[]}') };
    }, [SEED0 + run * 7919]);
  } catch (e) { crash++; continue; }

  let fresh = 0;
  for (const l of r.lines) { if (!seenAll.has(l)) { seenAll.add(l); fresh++; } }
  (r.talk || []).forEach(k => talkAll.add(k));
  if (r.ed) edAll.add(r.ed);
  (r.yomi.sh || []).forEach(x => shAll.add(x));
  (r.yomi.ka || []).forEach(x => kaAll.add(x));
  if (r.warn.length) dead++;
  dup += r.dups;
  rows.push({ run: run + 1, idx: r.idx, lines: r.lines.length, fresh, ed: r.ed,
              warn: r.warn.slice(0, 1) });
}
console.log(JSON.stringify({ N, rows, dead, dup, crash,
  seen: seenAll.size, talks: talkAll.size, eds: edAll.size,
  sh: shAll.size, ka: kaAll.size, errs: errs.slice(0, 3) }));
await b.close();
