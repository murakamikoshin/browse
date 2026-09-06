/* 検証モード。決済を入れる前に、game.html を機械で舐める。
   node tools/verify.mjs            全部
   node tools/verify.mjs --ed       エンディング85組だけ
   node tools/verify.mjs --band     章と帯だけ                       */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { fileURLToPath } from 'url';
import path from 'path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const only = process.argv.slice(2);
const want = t => only.length === 0 || only.includes('--' + t);

const SEALP = [1000, 10000, 100000, 1000000];
const opened = bal => SEALP.filter(x => bal >= x).length;

const browser = await chromium.launch();
const page = await browser.newPage();
await page.route(u => !u.protocol.startsWith('file'), r => r.abort());
const errs = [];
page.on('pageerror', e => errs.push(String(e)));
await page.goto('file://' + path.join(ROOT, 'game.html'), { waitUntil: 'domcontentloaded' });
const D = (fn, ...a) => page.evaluate(([f, args]) => window.__dev[f](...args), [fn, a]);

const bad = [];
const ng = (m) => { bad.push(m); console.log('NG  ' + m); };

const STEPS = await page.evaluate(() => window.__dev.STEPS);
const KEYS  = await page.evaluate(() => window.__dev.ASKS);

/* 価格帯はゲーム自身に計算させる。満額で一件だけ買った内引額が、そのまま％になる。 */
async function tiers_(){
  const t={};
  for(const k of KEYS){
    await page.reload({ waitUntil:'domcontentloaded' });
    await D('jump', 37, [k]);
    t[k] = (await D('state')).spent / 10000;
  }
  return t;
}

/* 支払額と目標開封数から、それを満たす買い方をひとつ見つける */
function subsetFor(paid, target, tiers) {
  const ks = Object.keys(tiers);
  for (let m = 0; m < (1 << ks.length); m++) {
    let pct = 0, pick = [];
    for (let i = 0; i < ks.length; i++) if (m & (1 << i)) { pct += tiers[ks[i]]; pick.push(ks[i]); }
    if (pct > 100) continue;
    const spent = paid / 100 * pct;
    if (spent > paid) continue;
    if (opened(paid - spent) === target) return pick;
  }
  return null;
}

/* ---------- 1. エンディング85組 ---------- */
if (want('ed')) {
  const tiers = await tiers_();
  console.log('価格帯 ' + KEYS.map(k => k + ':' + tiers[k] + '%').join(' '));

  let n = 0, seen = new Set();
  for (let i = 0; i < STEPS.length; i++) {
    const paid = STEPS[i];
    const maxO = opened(paid);
    const maxPct = (() => { let b = 0; const ks = Object.keys(tiers);
      for (let m = 0; m < (1 << ks.length); m++) { let s = 0;
        for (let j = 0; j < ks.length; j++) if (m & (1 << j)) s += tiers[ks[j]];
        if (s <= 100 && s > b) b = s; } return b; })();
    const minO = opened(paid * (100 - maxPct) / 100);
    for (let o = minO; o <= maxO; o++) {
      n++;
      const buys = subsetFor(paid, o, tiers);
      if (buys === null) { ng(`¥${paid.toLocaleString()} 開封${o} を作れる買い方が無い`); continue; }
      await page.reload({ waitUntil: 'domcontentloaded' });
      const before = errs.length;
      await D('jump', i, buys);
      const s = await D('state');
      const tag = `ED-${String(n).padStart(2,'0')} ¥${paid.toLocaleString()} 開封${o}`;
      if (s.seals !== o) ng(`${tag} 開封数が ${s.seals} になった`);
      if (s.ed !== n) ng(`${tag} 番号が ED-${s.ed} になった`);
      if (seen.has(s.ed)) ng(`${tag} 番号が重複`); seen.add(s.ed);
      if (!s.line || !s.line.trim()) ng(`${tag} 最終行が空`);
      if (paid === 0 && /[¥円]/.test(s.card || '')) ng(`${tag} ¥0 に額が出ている`);
      if (errs.length > before) ng(`${tag} pageerror: ${errs[before]}`);
    }
  }
  console.log(`\nエンディング ${n} 組を通した（成立する組の総数と一致すべき: 85）`);
  if (n !== 85) ng(`成立する組が ${n} 個。85 のはず`);
}

/* ---------- 2. 章と帯。指せる語句が全帯に残っているか ---------- */
if (want('band')) {
  console.log('');
  for (let band = 1; band <= 5; band++) {
    const idx = [0, 10, 19, 28, 37][band - 1];
    await page.reload({ waitUntil: 'domcontentloaded' });
    await D('begin', idx);
    const found = {};
    for (const src of ['1','2','3','4','5','6']) {
      const ch = await D('chapter', src);
      ch.forEach(l => l.asks.forEach(k => { found[k] = (found[k] || 0) + 1; }));
      ch.forEach(l => { if (!l.t || !l.t.trim()) ng(`帯${band} 第${src}章 ${l.id} が空`); });
    }
    const missing = KEYS.filter(k => !found[k]);
    console.log(`帯${band}（¥${STEPS[idx].toLocaleString()}） 指せる語句 ${Object.keys(found).length}/${KEYS.length}`);
    if (missing.length) ng(`帯${band} で消えた語句: ${missing.join(', ')}`);
  }
}

/* ---------- 3. 夜。選ばせるだけの行動が用意されているか ---------- */
if (want('night')) {
  console.log('');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await D('begin', 0);
  const n = await D('night');
  console.log(`夜の行動 ${n.talks} 本（${n.lines}行） 線香 ${n.incense} 本`);
  Object.keys(n.byPlace).forEach(k => console.log(`   ${k} ${n.byPlace[k]}`));
  /* 用意した行動が線香以下なら、全部やっても余る。誰がやっても同じ夜になり、
     無料のプレイヤーには選ぶところが一つも無くなる（SPEC 3.5 B）。 */
  if (n.talks <= n.incense)
    ng(`行動 ${n.talks} 本に対し線香 ${n.incense} 本。全部できてしまうので夜が選択にならない`);
  const places = ['genkan','butsu','minato','cha'];
  places.forEach(k => { if (!n.byPlace[k]) ng(`${k} に行動が一つも無い`); });
}

/* ---------- 4. 絵。場面の割り当てに穴が無いか ---------- */
if (want('art')) {
  console.log('');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await D('begin', 0);
  const a = await D('art');
  a.missing.forEach(m => ng('場面の割り当て先が無い: ' + m));
  const unused = a.scenes.filter(s => !s.used);
  console.log(`場面 ${a.scenes.length} 枚（使用 ${a.scenes.length - unused.length}／実画像 ${a.real.length}）`);
  unused.forEach(s => console.log(`   未使用 ${s.k}　${s.name}`));
  a.scenes.filter(s => s.used).forEach(s => console.log(`   ${s.k}　${s.name}`));
}

console.log(`\n不備 ${bad.length} 件`);
await browser.close();
process.exit(bad.length ? 1 : 0);
