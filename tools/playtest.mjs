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
let top = 0, topN = 0, topSnag = 0;      // 引っかかりの段が、どこまで届いたか

const browser = await chromium.launch();
const page = await browser.newPage();
const perr = [];
page.on('pageerror', e => perr.push(String(e)));

for (const idx of AMOUNTS) {
  for (const [wayName, way] of Object.entries(WAYS)) {
    await page.goto(URL);
    const r = await page.evaluate(([idx, way]) => {
      const D = window.__dev, out = { steps: 0, talked: 0, bought: 0, bare: 0, lines: 0, warn: [] };
      const SNAGTX = new Set(D.texts().snag);   // 最後の段で並べ直す行は、二度出るのが正しい
      const W = (m) => { if (out.warn.length < 6) out.warn.push(m); };
      D.fast(true);
      D.begin(idx);
      const paid = D.state().paid;

      for (let n = 0; n < 4000; n++) {
        const s = D.state();
        out.steps = n;

        /* ここが壊れていたら、遊ぶ人には必ず見える */
        /* 夜明け前も場所の札は 'cha' のままなので（dawn が置いている）、
           夜のあいだ（まだ朝になっていないあいだ）だけ見る。ここを分けないと、
           下の二つはどちらも「誰でも通った」ことになって、何も見なくなる。 */
        if (s.place === 'cha' && !s.done) {
          out.desk = true;
          /* 机の場面は仏間の引き出しを指している。仏間を読まずにここへ来ると、
             読んでいないものを思い出すことになる。朝へ通す道も同じ順を守る。 */
          if (!s.read.includes('2')) W('仏間を読まずに帳場の奥へ入った');
        }
        out.snag = s.snag.length; out.snagT = s.snagT.length; out.tier1 = s.snagTiers[0] || 99;
        out.tiers = s.snagTiers.length;
        if (s.incense < 0) W('線香が負になった');
        if (s.balance < 0) W('残高が負になった ' + s.balance);
        if (s.balance > paid) W('残高が持参より多い');
        const q = s.line && s.line.charAt(0) === '「';
        /* 原稿の差し込み（[額] [不足] など）が置き換わらずに出ていないか。
           一度これで、読み上げの一行がそのまま「[額]」と出ていた */
        if (/\[(額|不足|持参|内引|残|次封)\]/.test(s.line || '')) W('差し込みが残っている: ' + s.line.slice(0, 24));
        if (q && !s.who && !s.done) W('台詞に名札が無い: ' + s.line.slice(0, 14));
        if (!q && s.who) W('地の文に名札が出ている: ' + s.line.slice(0, 14));
        out.bare += s.kanjiBare; out.lines++;
        /* 一度読んだ行が、もう一度流れていないか。章を途中で切って戻ると、
           その場所へ入り直したときに最初から流れ直して、同じやり取りが二度起きる。
           **窓に出たままの行は数えない。**行が入れ替わった瞬間だけ見る。
           短い相槌は本当に何度も出るので、長い行だけ。
           「もう一度読む」を選んだあとは、二度出るのが正しいので見ない。 */
        if (s.line !== out.prev) {
          out.prev = s.line;
          if (!out.reread && s.line && s.line.length > 25 && !/^[「（]/.test(s.line) && !SNAGTX.has(s.line)) {
            out.said = out.said || {};
            out.seq = out.seq || []; out.seq.push(s.line);
            if (out.said[s.line]) { if (!out.dup) { out.dup = s.line;
              const i0 = out.said[s.line] - 1, i1 = out.seq.length - 1;
              W('同じ行が二度流れた: ' + s.line.slice(0, 22)
                + ' ／ 一度目の前後 ' + out.seq.slice(Math.max(0,i0-1), i0+2).map(x=>x.slice(0,14)).join('｜')
                + ' ／ 二度目の前 ' + out.seq.slice(Math.max(0,i1-3), i1).map(x=>x.slice(0,14)).join('｜')); } }
            else out.said[s.line] = out.seq.length;
          }
        }
        if (s.hamidashi > 0) { out.over = Math.max(out.over || 0, s.hamidashi);
          if ((out.over || 0) === s.hamidashi) W('枠から字がはみ出した ' + s.hamidashi + 'px: ' + (s.line||'').slice(0,16)); }

        if (s.done && document.querySelector('.slip-ed')) return finish(out, s);
        if (s.chapcard) { D.flush(4); continue; }          // 章の札は送る
        const nav = s.nav.filter(b => !b.off);
        /* 机へ寄る道を見せたか。断るのは遊ぶ人の自由だが、見せずに朝にしてはいけない */
        if (nav.some(b => /帳場の机へ寄る/.test(b.t))) out.deskOffer = true;
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
        const PLACE = /^(玄関・帳場|仏間|港|帳場の奥|玄関の外)(（[^）]*）)?$/;
        const UI = /^(閉じる|やめる|ほかの場所へ|もう一度読む|夜を終える|横になる|読み進める|はい|いいえ|最初から)$/;
        if (nav.length <= 2 && !nav.some(b => PLACE.test(b.t) || UI.test(b.t))) {
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
          const tk = nav.filter(b => !PLACE.test(b.t) && !UI.test(b.t) && !/のこと$/.test(b.t)).map(b => b.t);
          if (tk.length) { D.nav(tk[0]); out.talked++; continue; }
        }
        if (nav.some(b => b.t === 'もう一度読む')) { /* 選ばないが、押されたら数えない */ }
        const go = has(/読み進める/); if (go.length) { D.nav(go[0]); continue; }
        const yes = has(/^はい/); if (yes.length) { D.nav(yes[0]); continue; }

        /* 行き先の札が開いていれば、そこから歩く */
        const walk = has(/^(玄関・帳場|仏間|港|帳場の奥|玄関の外)(（[^）]*）)?$/);
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
        if (nav[0].t === 'もう一度読む') out.reread = true;
        D.nav(nav[0].t);
      }
      W('4000手で終わらなかった');
      return finish(out, D.state());

      function finish(o, s) {
        o.ed = s.ed; o.seals = s.seals; o.paid = s.paid; o.spent = s.spent;
        o.name = (document.querySelector('.slip-ed .nm') || {}).textContent || null;
        o.chap = s.chapSeen.length;
        o.beats = s.beats;                      // 夜のほうから動く三つが焚かれたか
        /* 買えば、朝に読まれる数の形が変わる。それを夜のうちに一度だけ言う */
        o.hasu = D.lines(4000).some(x => x.indexOf('切りのいい数ではない') >= 0);
        return o;
      }
    }, [idx, way]);

    const tag = `¥${r.paid.toLocaleString()} ／ ${wayName}`;
    if (!r.ed) note(`${tag}　最後まで行けなかった`);
    if (r.name === '（ED名は未執筆）') note(`${tag}　ED名が無い`);
    if (r.chap < 2) note(`${tag}　章の札が ${r.chap} 章分しか出ていない`);
    r.warn.forEach(w => note(`${tag}　${w}`));
    /* 買えることを知らないまま朝を迎えてはいけない。包まなかった人も机は通す */
    /* 通らずに朝になるのは、道を見せたうえで断ったときだけ許す（SPEC 10） */
    if (!r.desk && !r.deskOffer) note(`${tag}　帳場の机への道を見せずに朝になった`);
    /* 一段目に届いたのに、並べ直す場面が一度も出ていない */
    if (r.snag >= r.tier1 && !r.snagT) note(`${tag}　引っかかり${r.snag}個で並べ直しが出ていない`);
    /* 段を高く置きすぎると、いちばん強い並べ直しが誰にも出ない。
       線香を全部使う遊び方で、いくつまで届いたかを覚えておく */
    if (r.talked > 0) { top = Math.max(top, r.snagT); topN = r.tiers || topN; topSnag = Math.max(topSnag, r.snag); }
    /* 買って端数になったのに、夜のうちに何も言われないと、
       朝の読み上げで初めて気づくことになる。買った人には一度だけ言う */
    {
      const bal = (r.paid || 0) - (r.spent || 0);
      const round = /^[1-9]0*$/.test(String(bal));
      if (r.spent > 0 && bal >= 1000 && !round && !r.hasu)
        note(`${tag}　買って端数になったのに、夜のうちに何も言っていない`);
    }
    /* 夜のほうから動く三つ。線香を使い切る遊び方なら、必ず全部通るはず。
       ここが落ちると、中盤が「訊く」だけの平らな時間に戻る */
    if (r.steps > 200 && r.beats) {
      if (!r.beats.nagi)  note(`${tag}　凪さんが探しに来る場面が出ていない`);
      if (!r.beats.press) note(`${tag}　夜の半ばの場面が出ていない`);
    }
    const bare = r.lines ? (r.bare / r.lines).toFixed(1) : '-';
    console.log(`  ${tag.padEnd(22)} ED-${String(r.ed || 0).padStart(2, '0')} ${(r.name || '').padEnd(9)}` +
      ` 開封${r.seals} 話${r.talked} 一手${r.acts||0} 内引¥${(r.spent||0).toLocaleString()} 章${r.chap} 手${r.steps} 場面${(r.beats?[r.beats.mina&&'美',r.beats.nagi&&'凪',r.beats.press&&'帳'].filter(Boolean).join(''):'')||'—'} 素の漢字/行 ${bare}`);
  }
}

/* 引っかかりの段。高く置きすぎると、いちばん強い並べ直しが誰にも出ない */
if (topN) {
  console.log(`\n  引っかかりの段　線香を全部使う遊び方で ${top} / ${topN} 段（拾えた数 ${topSnag}）`);
  if (top < topN - 1) note(`引っかかりの段が高すぎる。${topN}段のうち ${top} 段までしか出ない`);
}

/* 画面の操作。遊ぶ人が触るところが、触ったとおりに動くか */
console.log('\n  画面の操作');
await page.goto(URL);
await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });   // 覚えている設定を消してから
await page.reload();
await page.evaluate(() => { window.__dev.fast(true); window.__dev.begin(20); window.__dev.flush(200); });
/* 手を畳むのは「どうする」で。nav を直に空にすると、畳んだ札が立たないので
   「どうする」で戻せなくなる（読んでいる途中に手を作らせないための札） */
const reset = () => page.evaluate(() => {
  const n = document.getElementById('nav');
  if (!n.firstChild) window.__dev.flush(60);
  if (n.firstChild) document.getElementById('bnav').click(); });
const ui = async (name, fn) => { await reset(); const r = await fn(); console.log('    ' + (r ? '○' : '×') + ' ' + name); if (!r) note('操作: ' + name); await reset(); };

await ui('畳んだあと「どうする」で選択肢が戻る', async () => { await page.click('#bnav'); return await page.locator('#nav .menu').count() === 1; });
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
await ui('選択肢が真ん中にある', async () => { await page.click('#bnav');
  const sym = async () => page.evaluate(() => {
    const m = document.querySelector('#nav .menu'); const bs = [...document.querySelectorAll('#nav button')];
    if (!m || !bs.length) return null;
    const mr = m.getBoundingClientRect();
    const left = Math.min(...bs.map(b => b.getBoundingClientRect().left)) - mr.left;
    const right = mr.right - Math.max(...bs.map(b => b.getBoundingClientRect().right));
    const hasLabel = !!m.querySelector('.row-l:not([hidden])');
    return { left: Math.round(left), right: Math.round(right), hasLabel,
             page: Math.round((mr.left + mr.right) / 2 - window.innerWidth / 2) };
  });
  const a = await sym();                                   // 見出しのある札
  await page.locator('#nav button', { hasText: /夜を終える|横になる/ }).click();
  const c = await sym();                                   // 見出しの無い札（確認）
  await page.locator('#nav button', { hasText: 'いいえ' }).click();
  return a && c && Math.abs(a.page) <= 1 && Math.abs(c.page) <= 1 &&
         a.hasLabel && !c.hasLabel && Math.abs(c.left - c.right) <= 2; });
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
  const openNav = () => page.evaluate(() => { const n = document.getElementById('nav');
    if (!n.firstChild) window.__dev.flush(60);                 // 読み残しを送ってから
    if (!n.firstChild) document.getElementById('bnav').click(); });
  const go = async (to) => { await openNav(); await page.evaluate((to) => { window.__dev.nav('ほかの場所へ'); window.__dev.nav(to); window.__dev.flush(); }, to); };
  await go('仏間');
  const a = await page.evaluate(() => window.__dev.state().chapSeen.length);
  await go('玄関・帳場');
  await openNav();
  await page.evaluate(() => { window.__dev.nav('ほかの場所へ'); window.__dev.nav('仏間'); });
  const b = await page.evaluate(() => window.__dev.state().chapcard);
  return a >= 2 && b === false; });

await ui('ふりがなが小さくなりすぎない', async () => {
  const px = await page.evaluate(() => {
    const rt = document.querySelector('#wt rt');
    return rt ? parseFloat(getComputedStyle(rt).fontSize) : 0;
  });
  return px >= 9.5; });
await ui('なぞっても字が選べない', async () =>
  await page.evaluate(() => {
    const v = (el) => getComputedStyle(el).webkitUserSelect || getComputedStyle(el).userSelect;
    return v(document.body) === 'none' && v(document.getElementById('wt')) === 'none';
  }));
await ui('切り替えると合図が出る', async () => {
  await page.click('#bruby');
  const a = await page.locator('#toast.on').count();
  const t = await page.textContent('#toast');
  await page.click('#bruby');
  return a === 1 && /ふりがな/.test(t); });
/* 「どうする」で場面を飛ばせてしまっていた。読んでいる途中に手を出すと、
   積んである行が捨てられて、その場の残りが読めなくなる。 */
await ui('読んでいる途中に「どうする」で場面が飛ばない', async () => {
  await page.goto(URL);
  return await page.evaluate(() => {
    const D = window.__dev; D.fast(true); D.begin(0);
    D.nav('ほかの場所へ'); D.nav('仏間（まだ）');       // 章を読み始める
    D.step();                                        // 一行だけ送る
    const before = D.state().line, q0 = D.queue().length;
    document.getElementById('bnav').click();
    const nav = document.getElementById('nav').firstChild;
    const q1 = D.queue().length;
    return !nav && q1 === q0 && D.state().line === before;
  }); });
await ui('夜の場所に章の番号が付いていない', async () => {
  const t = await page.evaluate(() => {
    const c = document.getElementById('chapcard');
    return (c.querySelector('.cc-n').textContent || '') + (c.querySelector('.cc-t').textContent || '');
  });
  return t.length > 0 && !/第.章/.test(t); });

/* 手を動かすところで畳んだら、同じ手がそのまま戻ること。
   出し直すときに手を作り直していた頃は、その場所の手に化けて、
   積んである行が捨てられ、次にそこへ入ると章が最初から流れ直していた。 */
/* 線香が尽きたあと、朝へ通す机で買っても止まらないこと。
   買ったあと burn() が true を返した時点で手を離していて、線香がもう0の机では
   手も札も出ないまま固まっていた。いちばん買われる場所なので、いちばん痛い。 */
await ui('線香が尽きたあとの机で買っても止まらない', async () => {
  await page.goto(URL);
  return await page.evaluate(() => {
    const D = window.__dev;
    const labs = () => [...document.querySelectorAll('#nav button')].map(b => b.textContent);
    const step = () => { if (D.state().chapcard) D.flush(2); else D.step(); };
    D.fast(true); D.begin(37);
    /* 線香を使い切って、朝へ通す机まで出す */
    for (let g = 0; g < 900 && D.state().incense > 0; g++) {
      if (!labs().length) { step(); continue; }
      const n = labs();
      const t = n.find(x => !/^(夜を終える|横になる|閉じる|やめる|ほかの場所へ|もう一度読む|はい|いいえ)/.test(x));
      if (t) { D.nav(t); continue; }
      if (n.indexOf('ほかの場所へ') >= 0) {
        D.nav('ほかの場所へ');
        const sub = labs().filter(x => x !== 'やめる');
        const go = sub.find(x => x.indexOf('（まだ）') >= 0) || sub.find(x => x.indexOf('（なし）') < 0);
        if (go) { D.nav(go); continue; }
        D.nav('やめる');
      }
      const e = n.find(x => /^(夜を終える|横になる)$/.test(x));
      if (e) { D.nav(e); const y = labs().find(x => /^はい/.test(x)); if (y) D.nav(y); continue; }
      break;
    }
    /* 机の場面のあいだに語句を指して、買う。
       D.point(k) は、その語句を探して章を最後まで送ってしまうので、
       **いま窓に出ているもの**（D.asks）だけを指す。でないと章が流れ切って朝になる。 */
    /* 買えたかどうかは、押した札ではなく**帳に載ったか**で見る。
       買う道は二つ（札の「はい」と、選択肢の「訊く」）あって、
       札のほうだけ数えていたので、買えているのに落ちていた。 */
    const got = () => D.state().bought.length > 0;
    for (let g = 0; g < 3000 && !D.state().done; g++) {
      const yy = document.querySelector('#card .cb [data-y]:not([disabled])');
      if (yy) { yy.click(); continue; }
      const n = labs();
      if (n.indexOf('訊く') >= 0) { D.nav('訊く'); continue; }
      if (!got()) {
        const a = D.asks().filter(x => !x.used)[0];
        if (a) { D.point(a.k); continue; }
      }
      if (!n.length) { step(); continue; }
      const t = n.find(x => !/^(閉じる|やめる|いいえ)/.test(x));
      if (!t) break;
      D.nav(t);
    }
    const s = D.state();
    return got() && s.spent > 0 && s.done && s.ed > 0;
  }); });

await ui('手を動かすところで畳んでも、同じ手が戻る', async () => {
  await page.goto(URL);
  const r = await page.evaluate(() => {
    const D = window.__dev;
    const labs = () => [...document.querySelectorAll('#nav button')].map(b => b.textContent);
    D.fast(true); D.begin(19);
    D.nav('ほかの場所へ'); D.nav('仏間（まだ）');
    for (let i = 0; i < 200 && !labs().length; i++) { if (D.state().chapcard) D.flush(2); else D.step(); }
    const a = labs().join('|'); if (!a) return { err: '手が出ない' };
    const q0 = D.queue().length, l0 = D.state().line;
    document.getElementById('bnav').click();                 // 畳む
    const folded = !document.getElementById('nav').firstChild;
    document.getElementById('win').click();                  // 窓を押しても送らない
    const moved = D.state().line !== l0 || D.queue().length !== q0;
    document.getElementById('bnav').click();                 // 戻す
    return { a, folded, moved, b: labs().join('|') };
  });
  return !r.err && r.folded && !r.moved && r.a === r.b; });


/* 隣り合う額で、朝がはっきり違うか。
   帯は五つしかないので、同じ帯の中では最終行しか変わらなかった。
   額の読み（数の形・切りのよさ・町の額との並び）を入れて、一段動かすだけで
   朝の読み上げの直後が変わるようにした。ここが同じに戻ったら、それは退化。 */
console.log('\n  隣り合う額');
{
  await page.goto(URL);
  const r = await page.evaluate(() => {
    const D = window.__dev, S = D.STEPS, same = [], empty = [];
    for (let i = 0; i < S.length; i++) {
      const cur = D.yomi(S[i]).join('');
      if (S[i] > 0 && !cur) empty.push(S[i]);
      if (i > 0 && S[i - 1] > 0 && cur === D.yomi(S[i - 1]).join('')) same.push(S[i]);
    }
    /* 買って端数になった額でも読みが変わるか */
    const hasu = D.yomi(970000).join('') !== D.yomi(1000000).join('');
    return { same, empty, hasu };
  });
  const ok1 = r.same.length === 0 && r.empty.length === 0;
  console.log('    ' + (ok1 ? '\u25cb' : '\u00d7') + ' 三十八段のどの隣どうしも、朝の読みが違う');
  if (r.same.length) note('隣り合う額: 同じ読みになる段 ' + r.same.join(','));
  if (r.empty.length) note('隣り合う額: 読みが空の段 ' + r.empty.join(','));
  console.log('    ' + (r.hasu ? '\u25cb' : '\u00d7') + ' 買って端数になると読みが変わる');
  if (!r.hasu) note('隣り合う額: 端数でも読みが変わらない');
}

/* 帳。見た結末の数と、帳場さんの帳が段どおりに開くか */
console.log('\n  帳');
const to = async (name, fn) => { const r = await fn(); console.log('    ' + (r ? '\u25cb' : '\u00d7') + ' ' + name); if (!r) note('帳: ' + name); };
const seed = async (n) => {
  await page.goto(URL);
  await page.evaluate((n) => { const a = []; for (let i = 1; i <= n; i++) a.push(i);
    try { localStorage.setItem('choba.ed', JSON.stringify(a)); } catch (e) {} }, n);
  await page.reload();
};
await to('何も見ていないと帳は押せない', async () => {
  await page.goto(URL); await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
  await page.reload();
  return await page.locator('#tto').isDisabled(); });
await to('一度見ると題の画面から開ける', async () => {
  await seed(1); return !(await page.locator('#tto').isDisabled()); });
await to('八十五行あり、見た分だけ名が出る', async () => {
  await seed(38); await page.click('#tto');
  const all = await page.locator('#tobox .to-e').count();
  const on = await page.locator('#tobox .to-e:not(.off)').count();
  const named = await page.locator('#tobox .to-e:not(.off) .nm').evaluateAll(e => e.filter(x => x.textContent.trim()).length);
  const blank = await page.locator('#tobox .to-e.off .nm').evaluateAll(e => e.every(x => !x.textContent.trim()));
  return all === 85 && on === 38 && named === 38 && blank; });
await to('見ていない結末の名は出ていない', async () => {
  const t = await page.locator('#tobox').innerText();
  return t.indexOf('わたしの帳') < 0 && t.indexOf('兄の帳') < 0; });
await to('額と開封の対応は帳に出ていない', async () => {
  const t = await page.locator('#tobox').innerText();
  return !/金[一二三四五六七八九十百千万]+円/.test(t) && t.indexOf('開封') < 0; });
/* 段は原稿側で増える。数を書き写さず、CHOBA から引く */
const chobaN = JSON.parse((await import('fs')).readFileSync(path.join(ROOT, 'game.html'), 'utf8')
  .match(/var CHOBA=(\[[\s\S]*?\]);/)[1]).map(s => s.n);
for (const n of [chobaN[0] - 1, ...chobaN]) {
  const open = chobaN.filter(x => x <= n).length;
  await to(`結末${n} で帳場さんの帳が${open}節`, async () => {
    await seed(n); await page.click('#tto');
    const o = await page.locator('#tobox .to-s.on').count();
    const lock = await page.locator('#tobox .to-s.lock').count();
    return o === open && o + lock === chobaN.length; });
}
await to('結末を押すと最後の一行が出る', async () => {
  await seed(40); await page.click('#tto');
  await page.locator('.to-e[data-n]').nth(5).click();
  const t = await page.textContent('#tod');
  return t.length > 20 && !/金[一二三四五六七八九十百千万]+円|¥|開封/.test(t); });
await to('Escape で閉じる', async () => {
  await page.keyboard.press('Escape'); return await page.locator('#tobox.on').count() === 0; });

/* 夜のほうから動く三つ。歩き方に頼ると、線香を使わない遊び方では一度も焚かれず、
   壊れても気づけない。任意の場所と線香の残りから、直に焚いて見る。 */
console.log('\n  夜のほうから動く場面');
const beat = async (idx, steps) => {
  await page.goto(URL);            // S は begin では戻らない。毎回読み直す
  return await page.evaluate(([idx, steps]) => {
  const D = window.__dev; D.fast(true); D.begin(idx); D.flush(400);
  const out = [];
  for (const [pl, inc] of steps) { const s = D.beat(pl, inc);
    out.push({ pl, inc, beats: s.beats, nav: s.nav.map(b => b.t), line: s.line }); }
  return { out, log: D.lines(400) };
  }, [idx, steps]);
};

{
  const r = await beat(20, [['butsu', 12], ['genkan', 9], ['cha', 4]]);
  const [m, n, p2] = r.out;
  await to('仏間で線香十二本なら、美波が起きてくる', async () => m.beats.mina && m.nav.length >= 3);
  await to('美波の手は三つあり、どれも札に評価語が無い', async () =>
    m.nav.filter(t => !/^(閉じる|やめる)$/.test(t)).length === 3);
  await to('線香九本で、凪さんが探しに来る', async () => n.beats.nagi);
  await to('線香四本で、帳場さんが来る', async () => p2.beats.press);
}
{
  const r = await beat(20, [['minato', 9]]);
  await to('港でも凪さんの場面は通る（凪は来ず、坂の上の灯りを見る）', async () =>
    r.out[0].beats.nagi && !/凪さん「/.test(r.log.join('')) );
}
{
  const r = await beat(20, [['genkan', 10]]);
  await to('仏間へ戻らないままだと、一度だけ音で呼ぶ', async () => r.out[0].beats.call);
}
{
  /* 取り消せない手。四つあって、どれも三択で、どれも正しくない */
  const r = await beat(20, [['cha', 7]]);
  await to('帳場の奥で線香七本なら、木箱をどうするか訊かれる', async () =>
    r.out[0].nav.filter(t => !/^(閉じる|やめる)$/.test(t)).length === 3);
  const r2 = await beat(20, [['butsu', 12], ['butsu', 5]]);
  await to('美波のあと、仏間で線香五本なら、布をどうするか訊かれる', async () =>
    r2.out[1].nav.filter(t => !/^(閉じる|やめる)$/.test(t)).length === 3);
  const r3 = await beat(20, [['minato', 10]]);
  await to('港で線香十本なら、船の中のものをどうするか訊かれる', async () =>
    r3.out[0].nav.filter(t => !/^(閉じる|やめる)$/.test(t)).length === 3);
  const r4 = await beat(20, [['ishi', 12]]);
  await to('玄関の外で線香十二本なら、返事をどうするか訊かれる', async () =>
    r4.out[0].nav.filter(t => !/^(閉じる|やめる)$/.test(t)).length === 3);
  const all = [r, r2, r3, r4];
  await to('四つの手は、どれも札に評価語が無い', async () =>
    !all.some(x => /正しく|やさしく|ちゃんと|きちんと/.test(x.log.join(''))));
}
{
  /* 玄関から動かないままでも、まだ通っていない場所が向こうから呼ぶ */
  /* 机は必ず仏間のあとなので、仏間を一度通してから玄関で更けさせる */
  const r = await beat(20, [['butsu', 14], ['genkan', 11], ['genkan', 8], ['genkan', 6]]);
  const got = r.out[r.out.length - 1].beats.sasoi || [];
  await to('歩かないままだと、通っていない場所が呼ぶ', async () =>
    ['minato', 'cha', 'ishi'].every(k => got.includes(k)));
}
{
  const r = await beat(0, [['genkan', 9], ['cha', 3]]);
  const t0 = r.log.join('');
  /* 章4の引きにも「お持ちの分」は出る（額は言っていない）。ここで見るのは
     夜の半ばと凪さんの、包んだ人だけに出る行 */
  await to('¥0 には、包んだ分の話をしない', async () =>
    t0.indexOf('相応に、と昨夜') < 0 && t0.indexOf('寄ったのね') < 0);
}

/* 画面の並び。題 → 説明三枚 → 支払い。どの画面も一枚に収まって、頁が動かない */
console.log('\n  画面の並び');
const noScroll = () => page.evaluate(() =>
  document.documentElement.scrollHeight <= window.innerHeight + 1 &&
  document.documentElement.scrollWidth <= window.innerWidth);
await to('題から始まる', async () => {
  await page.goto(URL);
  await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
  await page.reload();
  return await page.locator('#title.on').count() === 1 && await noScroll(); });
await to('送りのボタンが三枚とも同じ位置', async () => {
  await page.goto(URL); await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
  await page.reload(); await page.click('#tstart');
  const pos = [];
  for (let i = 0; i < 3; i++) {
    pos.push(await page.evaluate(() => [...document.querySelectorAll('#inav button')]
      .map(b => { const r = b.getBoundingClientRect(); return Math.round(r.left) + ',' + Math.round(r.top); }).join('/')));
    if (i < 2) await page.locator('#inav button', { hasText: '次へ' }).click();
  }
  return pos[0] === pos[1] && pos[1] === pos[2]; });
await to('説明は三枚で、戻れる', async () => {
  await page.goto(URL); await page.reload(); await page.click('#tstart');
  const t = [];
  t.push(await page.textContent('#ititle'));
  await page.locator('#inav button', { hasText: '次へ' }).click();
  t.push(await page.textContent('#ititle'));
  await page.locator('#inav button', { hasText: '戻る' }).click();
  const back = await page.textContent('#ititle');
  await page.locator('#inav button', { hasText: '次へ' }).click();
  await page.locator('#inav button', { hasText: '次へ' }).click();
  t.push(await page.textContent('#ititle'));
  return t.length === 3 && back === t[0] && await noScroll(); });
await to('支払いへ進んで、題へ戻れる', async () => {
  await page.locator('#inav button', { hasText: '包む画面へ' }).click();
  const at = await page.locator('#pay.on').count();
  const ns = await noScroll();
  await page.click('#pback');
  return at === 1 && ns && await page.locator('#title.on').count() === 1; });
await to('設定でふりがなと音を切り替えられる', async () => {
  await page.click('#tset');
  const a = await page.textContent('#setruby');
  await page.click('#setruby');
  const b = await page.textContent('#setruby');
  await page.click('#setruby');
  const c = await page.textContent('#setau');
  await page.click('#setau');
  const d = await page.textContent('#setau');
  await page.click('#setau'); await page.click('#setclose');
  return a !== b && c !== d; });

/* 狭い画面。配信を見て携帯で開く人がいるので、ここが崩れていると届かない */
console.log('\n  狭い画面');
for (const [w, h, name] of [[390, 844, '携帯 390x844'], [360, 640, '小さめ 360x640'], [820, 1180, 'タブレット 820x1180']]) {
  const pg = await browser.newPage({ viewport: { width: w, height: h }, isMobile: true, hasTouch: true });
  const pe = []; pg.on('pageerror', e => pe.push(String(e)));
  await pg.goto(URL);
  const r = await pg.evaluate(() => {
    const D = window.__dev; D.fast(true); D.begin(20); D.flush(400);
    if (!document.getElementById('nav').firstChild) document.getElementById('bnav').click();
    const nv = document.getElementById('nav');
    const bs = [...nv.querySelectorAll('button')];
    const last = bs.length ? bs[bs.length - 1].getBoundingClientRect() : null;
    const hud = document.querySelector('.hud-in').getBoundingClientRect();
    const chap = document.getElementById('chap').getBoundingClientRect();
    return {
      yoko: document.documentElement.scrollWidth > window.innerWidth + 1,
      hud: Math.round(hud.height),
      kasanari: chap.top < hud.bottom - 1,
      todokanai: last && last.bottom > window.innerHeight + 1 && nv.scrollHeight <= nv.clientHeight + 1,
      buttons: bs.length
    };
  });
  const ok = !r.yoko && !r.kasanari && !r.todokanai && r.hud < 90 && !pe.length;
  console.log(`    ${ok ? '○' : '×'} ${name}  HUD${r.hud}px 選択肢${r.buttons}個` +
    `${r.yoko ? ' 横あふれ' : ''}${r.kasanari ? ' 章題が隠れる' : ''}${r.todokanai ? ' 押せない選択肢' : ''}${pe.length ? ' ERR' : ''}`);
  if (!ok) note('狭い画面: ' + name);
  await pg.close();
}

if (perr.length) note('画面のエラー: ' + perr[0]);
console.log('\n不備 ' + bad.length + ' 件');
bad.forEach(b => console.log('NG  ' + b));
await browser.close();
process.exit(bad.length ? 1 : 0);
