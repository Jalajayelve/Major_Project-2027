/* Real form -> Agent 7 -> Agent 2 -> results/report/PDF.
   Requires the running app and a dedicated Chrome CDP session on 9222.
   Expected results are produced by test_agent2_live.py using real inference. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const delay = ms => new Promise(r => setTimeout(r, ms));
const output = path.resolve(__dirname, '../reports/agent2-local');
const expected = JSON.parse(fs.readFileSync(path.join(output, 'live-inference.json'), 'utf8'));

async function main() {
  const tabs = await (await fetch('http://127.0.0.1:9222/json')).json();
  const tab = tabs.find(t => t.type === 'page' && t.url.startsWith('http://localhost:3000'));
  assert(tab, 'Dedicated app test tab is required');
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let id = 0;
  const pending = new Map();
  ws.onmessage = e => {
    const m = JSON.parse(e.data), p = pending.get(m.id);
    if (p) { pending.delete(m.id); m.error ? p.reject(Error(JSON.stringify(m.error))) : p.resolve(m.result); }
  };
  ws.onclose = () => {
    for (const p of pending.values()) p.reject(Error('Browser disconnected during test'));
    pending.clear();
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const requestId = ++id;
    const timer = setTimeout(() => { pending.delete(requestId); reject(Error('Browser command timed out: '+method)); }, 30000);
    pending.set(requestId, {resolve: r=>{clearTimeout(timer);resolve(r);}, reject: e=>{clearTimeout(timer);reject(e);}});
    ws.send(JSON.stringify({id:requestId, method, params}));
  });
  const evaluate = async expression => {
    const r = await send('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true});
    if (r.exceptionDetails) throw Error(JSON.stringify(r.exceptionDetails));
    return r.result.value;
  };
  const wait = async (expression, label, timeout=120000) => {
    const end = Date.now()+timeout;
    while (Date.now()<end) { if (await evaluate(expression)) return; await delay(300); }
    throw Error(label+'\n'+await evaluate('document.body.innerText'));
  };
  const click = async text => {
    await evaluate(`(() => {const b=[...document.querySelectorAll('button')].find(b=>b.textContent.includes(${JSON.stringify(text)})); if(!b)throw Error('Button missing'); b.click();})()`);
    await delay(500);
  };
  const field = async (name,value) => {
    await wait(`!!document.getElementById(${JSON.stringify('f-'+name)})`, `Input ${name} did not appear`, 20000);
    await evaluate(`(() => {const e=document.getElementById(${JSON.stringify('f-'+name)});if(!e)throw Error('Input missing'); e.focus(); Object.getOwnPropertyDescriptor(e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));if(e.tagName!=='SELECT')e.dispatchEvent(new FocusEvent('focusout',{bubbles:true}));e.blur();})()`);
    await delay(220);
  };
  const readRows = () => evaluate("[...document.querySelectorAll('[data-testid=agent2-result] table tbody tr')].slice(0,10).map(r=>r.innerText)");
  const checkRows = async result => {
    const rows = await readRows();
    const section = await evaluate("document.querySelector('[data-testid=agent2-result]').innerText");
    assert(section.toLowerCase().includes('unvalidated model score'));
    assert(!rows.some(r => /\b(Safe|Target|Reach)\b/.test(r)));
    assert.equal(rows.length, result.universities.length);
    result.universities.forEach((u,i) => {
      for(const value of [u.name,u.program,u.tier,u.prob_str,u.match_str,u.tuition_str])
        assert(rows[i].includes(value), `Row ${i} missing ${value}`);
    });
    return rows;
  };
  const analyze = async () => {
    await click('Programs');
    await wait("[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Continue to documents'))", 'Final profile step missing');
    await click('Continue to documents');
    await wait("location.pathname==='/documents' && [...document.querySelectorAll('button')].some(b=>b.textContent.includes('Start analysis'))", 'Profile submission failed');
    await click('Start analysis');
    await wait("[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Open your dossier'))", 'Analysis did not finish');
    const status = await evaluate('document.body.innerText');
    assert(!status.includes('Agent 2 unavailable'), status);
    await click('Open your dossier');
    await wait("location.pathname==='/results' && !!document.querySelector('[data-testid=agent2-result] table')", 'Real Agent 2 results missing');
  };
  try {
    await send('Page.enable');
    await send('Emulation.setDeviceMetricsOverride', {width:1440,height:1100,deviceScaleFactor:1,mobile:false});
    await send('Browser.setDownloadBehavior', {behavior:'allow',downloadPath:output});
    await send('Page.navigate', {url:'http://localhost:3000/profile'});
    await wait("[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Personal'))",'Profile missing');
    // Dedicated test browser: start a fresh session, including after a dev-server reload.
    await evaluate('sessionStorage.clear(); localStorage.clear();');
    await send('Page.reload');
    await delay(1200);
    await wait("[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Personal'))",'Fresh profile missing');
    await delay(1300);
    await click('Personal');
    await field('full_name', 'TEST PROFILE - Agent 2 and Agent 7');
    await click('Academic'); await field('gpa', '8.4'); await field('gpa_scale','10');
    await click('Tests'); await field('gre_quant', '165');
    await click('Goals'); await field('degree_goal','MS'); await field('field','Computer Science');
    await click('Experience');
    for(const [key,value] of Object.entries(expected.agent7_inputs)) await field(key,value);
    if (process.env.PROFILE_NAV_ONLY === '1') {
      await field('research_score','');
      await click('Programs');
      await click('Continue to documents');
      await wait("!!document.querySelector('[data-testid=profile-submission-error]')",'Missing-input error was not shown');
      assert((await evaluate('document.body.innerText')).includes('Preferred programs'));
      assert((await evaluate('document.body.innerText')).includes('research_score'));
      await click('Review Experience fields');
      await field('research_score','9');
      assert(!(await evaluate("[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Next section'))")));
      await click('Continue to documents');
      await wait("location.pathname==='/documents' && [...document.querySelectorAll('button')].some(b=>b.textContent.includes('Start analysis'))",'Corrected profile did not reach Documents');
      console.log('PASS: missing input stays on final step; correction in Experience submits directly to Documents using real Agent 7.');
      return;
    }
    await analyze();
    const firstRows = await checkRows(expected.first);
    await wait("document.querySelector('[data-testid=agent7-result]').innerText.includes('55.4')",'Agent 7 score missing after count animation',10000);
    console.log('PASS: real form -> Agent 7 -> Agent 2 -> ten matching rows');
    await click('Download report');
    await delay(2000);
    const pdf = fs.readFileSync(path.join(output,'Meridian-Study-Abroad-Report.pdf'));
    assert(pdf.subarray(0,4).equals(Buffer.from('%PDF')));
    await send('Page.navigate',{url:'http://localhost:3000/report'});
    await wait("!!document.querySelector('[data-testid=agent2-result] table')",'Printable report missing');
    await checkRows(expected.first);
    console.log('PASS: printable report and PDF download');
    await send('Page.navigate',{url:'http://localhost:3000/profile'});
    await wait("[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Academic'))",'Profile reload missing');
    await click('Academic'); await field('gpa','9.8');
    await send('Page.navigate',{url:'http://localhost:3000/results'});
    await wait("!!document.querySelector('[data-testid=agent2-unavailable]')",'Edited profile retained stale results');
    await send('Page.navigate',{url:'http://localhost:3000/profile'});
    await wait("[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Programs'))",'Profile tabs missing');
    await analyze();
    const secondRows = await checkRows(expected.second);
    assert.notDeepEqual(firstRows,secondRows);
    console.log('PASS: changing GPA invalidates old results and changes real predictions');
    await send('Page.reload');
    await delay(1200);
    await wait("!!document.querySelector('[data-testid=agent2-result] table')",'Results lost on refresh');
    await checkRows(expected.second);
    await evaluate("document.getElementById('university-matches').scrollIntoView({block:'start'})");
    await delay(1200);
    const screenshot=await send('Page.captureScreenshot',{format:'png'});
    fs.writeFileSync(path.join(output,'frontend-results.png'),Buffer.from(screenshot.data,'base64'));
    await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
    await delay(600);
    const mobile=await send('Page.captureScreenshot',{format:'png'});
    fs.writeFileSync(path.join(output,'frontend-mobile.png'),Buffer.from(mobile.data,'base64'));
    await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
    await send('Page.navigate',{url:'http://localhost:3000/profile'});
    await wait("[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Tests'))",'Profile tests missing');
    await click('Tests'); await field('gre_quant','');
    await analyze();
    const unsupportedRows = await readRows();
    assert.equal(unsupportedRows.length,10);
    assert(unsupportedRows.every(r=>r.includes('Insufficient evidence') && !/\b(Safe|Target|Reach)\b/.test(r)));
    assert((await evaluate("document.querySelector('[data-testid=agent2-result]').innerText")).includes('GRE Quant is missing'));
    await send('Page.navigate',{url:'http://localhost:3000/report'});
    await wait("!!document.querySelector('[data-testid=agent2-result] table')",'Unsupported printable report missing');
    assert((await readRows()).every(r=>r.includes('Insufficient evidence')));
    await send('Page.navigate',{url:'http://localhost:3000/results'});
    await wait("!!document.querySelector('[data-testid=agent2-result] table')",'Unsupported results missing');
    await evaluate("document.getElementById('university-matches').scrollIntoView({block:'start'})");
    await delay(700);
    const unsupportedImage=await send('Page.captureScreenshot',{format:'png'});
    fs.writeFileSync(path.join(output,'frontend-insufficient-evidence.png'),Buffer.from(unsupportedImage.data,'base64'));
    fs.writeFileSync(path.join(output,'browser-check.json'),JSON.stringify({passed:true,
      checks:['real_form_submission','agent7_to_agent2','ten_real_rows','printable_report_consistency','pdf_download',
              'profile_edit_invalidates_results','changed_gpa_changes_predictions','refresh_preserves_results',
              'experimental_score_labels','missing_gre_no_score','unsupported_printable_report'],
      firstRows,secondRows,unsupportedRows,url:'http://localhost:3000/results'},null,2));
    console.log('PASS: session refresh and desktop/mobile screenshots saved');
  } finally { ws.close(); }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
