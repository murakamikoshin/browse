/* 通し試験。遊ぶ人の側から見て壊れていないかを見る。
   verify.mjs が「データが揃っているか」を見るのに対し、こちらは
   「どの額で、どんな遊び方をしても、行き止まりにならずに朝まで行けるか」を見る。

     node tools/playtest.mjs           全部
     node tools/playtest.mjs --quick   額を三つだけ                                  */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { fileURLToPath } from 'url';
import path from 'path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const URL = 'file://' + path.join(ROOT, 'game.html');
const quick = process.argv.includes('--quick');

/* 遊び方。どれも実際に起こりうる遊び方にする */
const WAYS = {
  '無口':   { talk: false, buy: false },   // 誰とも話さず、歩いて、夜を終える
  '話し好き': { talk: true,  buy: false },  // 線香を全部会話に使う
  '買い手':  { talk: false, buy: true  },  // 指せる語句を全部買う
  'せっかち': { talk: false, buy: false, rush: true },  // 開幕で夜を終える
};
const AMOUNTS = quick ? [0, 10, 37] : [0, 3, 9, 10, 18, 19, 27, 28, 36, 37];

const bad = [];
const note = (m) => bad.push(m);

const browser = await chromium.launch();
const page = await browser.newPage();
const perr = [];
page.on('pageerror', e => perr.push(String(e)));

for (const idx of AMOUNTS) {
  for (const [wayName, way] of Object.entries(WAYS)) {
    await page.goto(URL);
    const r = await page.evaluate(([idx, way]) => {
      const D = window.__dev, out = { steps: 0, talked: 0, bought: 0, bare: 0, lines: 0, warn: [] };
      const W = (m) => { if (out.warn.length < 6) out.warn.push(m); };
      D.fast(true);
      D.begin(idx);
      const paid = D.state().paid;

      for (let n = 0; n < 4000; n++) {
        const s = D.state();
        out.steps = n;

        /* ここが壊れていたら、遊ぶ人には必ず見える */
        if (s.incense < 0) W('線香が負になった');
        if (s.balance < 0) W('残高が負になった ' + s.balance);
        if (s.balance > paid) W('残高が持参より多い');
        const q = s.line && s.line.charAt(0) === '「';
        if (q && !s.who && !s.done) W('台詞に名札が無い: ' + s.line.slice(0, 14));
        if (!q && s.who) W('地の文に名札が出ている: ' + s.line.slice(0, 14));
        out.bare += s.kanjiBare; out.lines++;

        if (s.done && document.querySelector('.slip-ed')) return finish(out, s);
        if (s.chapcard) { D.flush(4); continue; }          // 章の札は送る
        const nav = s.nav.filter(b => !b.off);
        if (way.buy && !nav.length) {                      // 指せる語句を探しながら読む
          for (const k of D.ASKS) if (!s.bought.includes(k) && !s.noted.includes(k) && D.point(k)) { out.pointed = (out.pointed||0)+1; break; }
        }

        if (!nav.length && !s.chapcard) {
          const before = s.line;
          D.flush(60);
          if (D.state().line === before && !D.state().nav.length) { W('行き止まり: ' + s.place + ' / ' + before.slice(0, 16)); return finish(out, D.state()); }
          continue;
        }

        /* 選べるものが一つも無ければ行き止まり */
        const has = (re) => nav.filter(b => re.test(b.t)).map(b => b.t);
        /* 手を動かすところ。半分は「やめる」ほうを選んで、戻ってこられるか見る */
        if (nav.length <= 2 && !nav.some(b => /^(玄関|仏間|港|帳場|閉じる|夜を終える|横になる|読み進める|はい|いいえ|最初から)/.test(b.t))) {
          out.acts = (out.acts || 0) + 1;
          D.nav(nav.length === 2 && out.acts % 2 === 0 ? nav[1].t : nav[0].t); continue;
        }
        if (nav.length === 1) { D.nav(nav[0].t); continue; }

        if (way.rush) {
          const e = has(/夜を終える|横になる/); if (e.length) { D.nav(e[0]); continue; }
          const y = has(/^はい/); if (y.length) { D.nav(y[0]); continue; }
        }
        if (way.buy) {
          const yy = document.querySelector('#card .cb [data-y]:not([disabled])');
          if (yy) { yy.click(); out.bought = (out.bought||0)+1; continue; }        // 帳場さんに訊く
          const nn = document.querySelector('#card .cb [data-y][disabled]');
          if (nn) { document.querySelector('#card .cb [data-n]').click(); continue; }
          if (s.place === 'cha') { const a2 = has(/のこと$/); if (a2.length) { D.nav(a2[0]); continue; } }
        }
        if (way.talk) {
          const skip = /^(玄関|仏間|港|帳場|閉じる|やめる|ほかの場所へ|もう一度読む|夜を終える|横になる|読み進める|いいえ|はい|最初から)/;
          const tk = nav.filter(b => !skip.test(b.t) && !/のこと$/.test(b.t)).map(b => b.t);
          if (tk.length) { D.nav(tk[0]); out.talked++; continue; }
        }
        const go = has(/読み進める/); if (go.length) { D.nav(go[0]); continue; }
        const yes = has(/^はい/); if (yes.length) { D.nav(yes[0]); continue; }

        /* 行き先の札が開いていれば、そこから歩く */
        const walk = has(/^(玄関・帳場|仏間|港|帳場の奥|玄関の外)$/);
        if (walk.length) {
          const to = walk[out.steps % walk.length];
          out.went = (out.went || []); if (!out.went.includes(to)) out.went.push(to);
          D.nav(to); continue;
        }
        /* 四箇所まわったら夜を終える。まだなら行き先を開く */
        const end = has(/夜を終える|横になる/);
        if (end.length && (out.went || []).length >= 4) { D.nav(end[0]); continue; }
        const open = has(/^ほかの場所へ$/); if (open.length) { D.nav(open[0]); continue; }
        if (end.length) { D.nav(end[0]); continue; }
        D.nav(nav[0].t);
      }
      W('4000手で終わらなかった');
      return finish(out, D.state());

      function finish(o, s) {
        o.ed = s.ed; o.seals = s.seals; o.paid = s.paid; o.spent = s.spent;
        o.name = (document.querySelector('.slip-ed .nm') || {}).textContent || null;
        o.chap = s.chapSeen.length;
        return o;
      }
    }, [idx, way]);

    const tag = `¥${r.paid.toLocaleString()} ／ ${wayName}`;
    if (!r.ed) note(`${tag}　最後まで行けなかった`);
    if (r.name === '（ED名は未執筆）') note(`${tag}　ED名が無い`);
    if (r.chap < 2) note(`${tag}　章の札が ${r.chap} 章分しか出ていない`);
    r.warn.forEach(w => note(`${tag}　${w}`));
    const bare = r.lines ? (r.bare / r.lines).toFixed(1) : '-';
    console.log(`  ${tag.padEnd(22)} ED-${String(r.ed || 0).padStart(2, '0')} ${(r.name || '').padEnd(9)}` +
      ` 開封${r.seals} 話${r.talked} 一手${r.acts||0} 内引¥${(r.spent||0).toLocaleString()} 章${r.chap} 手${r.steps} 素の漢字/行 ${bare}`);
  }
}

/* 画面の操作。遊ぶ人が触るところが、触ったとおりに動くか */
console.log('\n  画面の操作');
await page.goto(URL);
await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });   // 覚えている設定を消してから
await page.reload();
await page.evaluate(() => { window.__dev.begin(20); document.getElementById('nav').replaceChildren(); });
const reset = () => page.evaluate(() => { document.getElementById('nav').replaceChildren(); });
const ui = async (name, fn) => { await reset(); const r = await fn(); console.log('    ' + (r ? '○' : '×') + ' ' + name); if (!r) note('操作: ' + name); await reset(); };

await ui('「どうする」で選択肢が出る', async () => { await page.click('#bnav'); return await page.locator('#nav .menu').count() === 1; });
await ui('もう一度押すと閉じる', async () => { await page.click('#bnav'); await page.click('#bnav'); return await page.locator('#nav .menu').count() === 0; });
await ui('Escape でも閉じる', async () => { await page.click('#bnav'); await page.keyboard.press('Escape'); return await page.locator('#nav .menu').count() === 0; });
await ui('「閉じる」で閉じる', async () => { await page.click('#bnav'); await page.locator('#nav button', { hasText: '閉じる' }).click(); return await page.locator('#nav .menu').count() === 0; });
await ui('行き先は一段奥にある', async () => { await page.click('#bnav');
  const a = await page.locator('#nav button', { hasText: 'ほかの場所へ' }).count();
  await page.locator('#nav button', { hasText: 'ほかの場所へ' }).click();
  const b = await page.locator('#nav button', { hasText: '仏間' }).count();
  const here = await page.locator('#nav button', { hasText: '玄関・帳場' }).count();
  await page.locator('#nav button', { hasText: 'やめる' }).click();
  return a === 1 && b === 1 && here === 0; });
await ui('線香の本数が用意した数と合っている', async () =>
  await page.locator('#sticks .stick').count() === await page.evaluate(() => window.__dev.state().incense));
await ui('段が三つに分かれている', async () => { await page.click('#bnav');
  const c = await page.locator('#nav .row').evaluateAll(r => r.map(x => x.className));
  return c.some(x => x === 'row') && c.some(x => /sub/.test(x)) && c.some(x => /faint/.test(x)); });
await ui('「夜を終える」は確認してから', async () => {
  await page.click('#bnav');
  await page.locator('#nav button', { hasText: /夜を終える|横になる/ }).click();
  const w = await page.locator('.menu-h.warn').count();
  const yes = await page.locator('#nav button', { hasText: '^はい' }).count();
  await page.locator('#nav button', { hasText: 'いいえ' }).click();
  return w === 1 && yes === 0 ? true : w === 1; });
await ui('「記録」が開いて閉じる', async () => { await page.click('#blog');
  const on = await page.locator('#logbox.on').count(); await page.click('#blog');
  return on === 1 && await page.locator('#logbox.on').count() === 0; });
await ui('「記録」に読んだ行が入っている', async () => { await page.click('#blog');
  const n = await page.locator('#loglist p.l').count(); await page.click('#blog'); return n > 20; });
await ui('「ふりがな」で出たり消えたりする', async () => {
  const a = await page.locator('#wt ruby').count(); await page.click('#bruby');
  const b = await page.locator('#wt ruby').count(); await page.click('#bruby');
  const c = await page.locator('#wt ruby').count();
  return a > 0 && b === 0 && c === a; });
await ui('ふりがなの入り切りを覚えている', async () => {
  await page.click('#bruby'); await page.reload();
  const kept = await page.evaluate(() => { try { return localStorage.getItem('ruby'); } catch (e) { return null; } });
  await page.evaluate(() => { window.__dev.begin(20); });
  const off = await page.locator('#wt ruby').count() === 0;
  await page.click('#bruby'); return kept === '0' && off; });
await ui('「音」で入り切りできる', async () => { const a = await page.locator('#bau.off').count();
  await page.click('#bau'); const b = await page.locator('#bau.off').count();
  await page.click('#bau'); const c = await page.locator('#bau.off').count();
  return a !== b && a === c; });
await ui('章の札は同じ章で二度出ない', async () => {
  const openNav = () => page.evaluate(() => { if (!document.getElementById('nav').firstChild) document.getElementById('bnav').click(); });
  const go = async (to) => { await openNav(); await page.evaluate((to) => { window.__dev.nav('ほかの場所へ'); window.__dev.nav(to); window.__dev.flush(); }, to); };
  await go('仏間');
  const a = await page.evaluate(() => window.__dev.state().chapSeen.length);
  await go('玄関・帳場');
  await openNav();
  await page.evaluate(() => { window.__dev.nav('ほかの場所へ'); window.__dev.nav('仏間'); });
  const b = await page.evaluate(() => window.__dev.state().chapcard);
  return a >= 2 && b === false; });

if (perr.length) note('画面のエラー: ' + perr[0]);
console.log('\n不備 ' + bad.length + ' 件');
bad.forEach(b => console.log('NG  ' + b));
await browser.close();
process.exit(bad.length ? 1 : 0);
