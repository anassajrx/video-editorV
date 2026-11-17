// Live progress page for an edit.  Usage: node scripts/progress-server.mjs <slug> [port]
// Open http://localhost:4321 . Reads:
//   public/videos/<slug>/raw/progress.json   steps written by Claude: [{name, status: pending|running|done|failed, note?}]
//   public/videos/<slug>/raw/phrases.log     "SEG n" lines from transcribe_phrases.py  -> exact % of segments
//   public/videos/<slug>/raw/cut.mp4.cuts.json  number of segments
//   public/videos/<slug>/raw/render.log      Remotion "Rendered x/y" lines -> exact % of frames
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const slug = process.argv[2] ?? "comeback";
const port = Number(process.argv[3] ?? 4321);
const R = path.join("public", "videos", slug, "raw");
const read = (f) => {
  try {
    return fs.readFileSync(path.join(R, f), "utf8");
  } catch {
    return null;
  }
};

const status = () => {
  let steps = [];
  try {
    steps = JSON.parse(read("progress.json") ?? "[]");
  } catch {}
  const live = {};
  const cuts = read("cut.mp4.cuts.json");
  const log = read("phrases.log");
  if (cuts && log) {
    const total = JSON.parse(cuts).cuts.length;
    const done = (log.match(/^SEG\s+\d+/gm) ?? []).length;
    const last = (log.match(/^SEG.*$/gm) ?? []).slice(-1)[0] ?? "";
    live.transcribe = { done, total, last: last.replace(/^SEG\s+\d+\s+[\d.]+-\s*[\d.]+\s*/, "") };
  }
  const rl = read("render.log");
  if (rl) {
    const m = [...rl.matchAll(/(Rendered|Encoded)\s+(\d+)\/(\d+)/g)].pop();
    if (m) live.render = { done: Number(m[2]), total: Number(m[3]), what: m[1] };
  }
  return { slug, steps, live, now: new Date().toISOString() };
};

const page = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Edit progress</title><style>
:root{--plum:#120A1F;--v:#8B5CF6;--l:#C4B5FD;--w:#F5F3FF;--m:#9A8FB5;--d:#3B2A63}
body{margin:0;background:var(--plum);color:var(--w);font:16px system-ui,sans-serif;padding:28px 16px}
main{max-width:640px;margin:0 auto}h1{font:italic 400 40px Georgia,serif;margin:0 0 4px}
.sub{font:12px ui-monospace,monospace;letter-spacing:3px;color:var(--l);margin-bottom:24px}
.big{font:700 64px system-ui;letter-spacing:-2px}.bar{height:10px;background:var(--d);border-radius:5px;overflow:hidden;margin:8px 0 6px}
.bar div{height:100%;background:var(--v);transition:width .6s}
.step{display:flex;gap:12px;padding:11px 0;border-bottom:1px solid #251a3d;align-items:flex-start}
.dot{width:12px;height:12px;border-radius:50%;margin-top:5px;flex-shrink:0;background:var(--d)}
.done .dot{background:var(--l)}.running .dot{background:var(--v);box-shadow:0 0 0 5px rgba(139,92,246,.25)}
.failed .dot{background:#e0607a}.pending{color:var(--m)}.note{font-size:13px;color:var(--m);margin-top:3px}
.live{background:#1d1233;border:1px solid #3b2a63;border-radius:12px;padding:14px 16px;margin:18px 0}
.mono{font:13px ui-monospace,monospace;color:var(--m);direction:rtl;text-align:right;margin-top:6px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.t{font-size:12px;color:var(--m);margin-top:22px}</style></head><body><main>
<h1>Edit progress</h1><div class="sub" id="slug"></div><div class="big" id="pct">–</div>
<div class="bar"><div id="pbar" style="width:0"></div></div><div id="pnote" class="note"></div>
<div id="live"></div><div id="steps"></div><div class="t" id="t"></div></main><script>
async function tick(){try{const s=await (await fetch('/status')).json();
document.getElementById('slug').textContent=s.slug.toUpperCase()+' · LIVE';
const n=s.steps.length||1,done=s.steps.filter(x=>x.status==='done').length;
let part=0;const run=s.steps.find(x=>x.status==='running');
if(run&&run.live&&s.live[run.live])part=s.live[run.live].done/s.live[run.live].total;
const pct=Math.min(100,Math.round((done+part)/n*100));
document.getElementById('pct').textContent=pct+'%';document.getElementById('pbar').style.width=pct+'%';
document.getElementById('pnote').textContent=done+' of '+n+' steps done'+(run?' · now: '+run.name:'');
let L='';if(s.live.transcribe){const x=s.live.transcribe;L+='<div class="live">Transcription: <b>'+x.done+' / '+x.total+'</b> segments ('+Math.round(x.done/x.total*100)+'%)<div class="bar"><div style="width:'+(x.done/x.total*100)+'%"></div></div><div class="mono">'+(x.last||'')+'</div></div>'}
if(s.live.render){const x=s.live.render;L+='<div class="live">Render ('+x.what.toLowerCase()+'): <b>'+x.done+' / '+x.total+'</b> frames ('+Math.round(x.done/x.total*100)+'%)<div class="bar"><div style="width:'+(x.done/x.total*100)+'%"></div></div></div>'}
document.getElementById('live').innerHTML=L;
document.getElementById('steps').innerHTML=s.steps.map(x=>'<div class="step '+x.status+'"><div class="dot"></div><div><div>'+x.name+'</div>'+(x.note?'<div class="note">'+x.note+'</div>':'')+'</div></div>').join('');
document.getElementById('t').textContent='Updated '+new Date(s.now).toLocaleTimeString()+' · refreshes every 3 s';
}catch(e){document.getElementById('t').textContent='Server not reachable…'}}
tick();setInterval(tick,3000);</script></body></html>`;

http
  .createServer((req, res) => {
    if (req.url === "/status") {
      res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      return res.end(JSON.stringify(status()));
    }
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(page);
  })
  .listen(port, "127.0.0.1", () => console.log(`Progress page: http://localhost:${port}`));
