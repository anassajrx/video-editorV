"use client";
import { useCallback, useEffect, useRef, useState } from "react";

type Vid = { id: string; name: string; size?: string; modifiedTime?: string };
type JobRow = { id: string; name: string; created?: string; stage?: string; state?: string; percent?: number; message?: string; heartbeat?: string };
type Step = { id: string; label: string; state: string; done: number | null; total: number | null; unit: string };
type Status = {
  slug?: string; stage?: string; state?: string; percent?: number; eta_s?: number | null; message?: string; error?: string | null;
  heartbeat?: string; steps?: Step[]; current?: string | null; video?: { name?: string; id?: string };
  storyboard?: { folder_id?: string; png?: string; md?: string }; final?: { folder_id?: string; video?: string; preview?: string };
  prep?: { orientation?: string; duration_s?: number }; history?: { stage: string; state: string }[];
  cut?: { folder_id?: string; decisions?: string; to_omni?: string; from_omni?: string; clips?: number };
  post?: { folder_id?: string; compare?: string | null };
  job?: { options?: { omni?: boolean; background?: boolean } };
};

function stagesFor(o?: { omni?: boolean; background?: boolean }): [string, string][] {
  const s: [string, string][] = [["prep", "Prep GPU"]];
  if (o?.omni || o?.background) s.push(["cut", "Choix des prises"]);
  if (o?.omni) s.push(["omni", "Omni Flash (toi)"]);
  if (o?.omni || o?.background) s.push(["post", o?.background ? "Fond (GPU)" : "Omni (GPU)"]);
  s.push(["storyboard", "Storyboard"], ["review", "Ta validation"], ["final", "Montage final"], ["done", "Terminé"]);
  return s;
}
const ALL: [string, string][] = stagesFor({ omni: true, background: true });

const fmtBytes = (n: number) => (n > 1e9 ? `${(n / 1e9).toFixed(2)} GB` : n > 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1e3)} KB`);
const fmtSecs = (s: number) => (s >= 3600 ? `${Math.floor(s / 3600)} h ${Math.round((s % 3600) / 60)} min` : s >= 60 ? `${Math.floor(s / 60)} min ${Math.round(s % 60)} s` : `${Math.round(s)} s`);
function count(s: Step) {
  if (s.total == null || s.done == null) return "";
  if (s.unit === "bytes") return `${fmtBytes(s.done)} / ${fmtBytes(s.total)}`;
  if (s.unit === "s") return `${fmtSecs(s.done)} / ${fmtSecs(s.total)}`;
  return `${Math.round(s.done)} / ${Math.round(s.total)} ${s.unit}`;
}
const ago = (iso?: string) => (iso ? (Date.now() - Date.parse(iso)) / 1000 : Infinity);

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { cache: "no-store", ...init });
  if (r.status === 401) { location.reload(); throw new Error("login"); }
  const b = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(b.error || `HTTP ${r.status}`);
  return b as T;
}

export default function Studio() {
  const [vids, setVids] = useState<Vid[]>([]);
  const [vidErr, setVidErr] = useState("");
  const [pick, setPick] = useState<string>("");
  const [link, setLink] = useState("");
  const [name, setName] = useState("");
  const [context, setContext] = useState("");
  const [script, setScript] = useState("");
  const [bg, setBg] = useState(false);
  const [bgLink, setBgLink] = useState("");
  const [hasMe, setHasMe] = useState(true);
  const [omni, setOmni] = useState(false);
  const [runErr, setRunErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [st, setSt] = useState<Status | null>(null);
  const [stErr, setStErr] = useState("");

  const loadJobs = useCallback(async () => {
    try {
      const r = await j<{ jobs: JobRow[] }>("/api/jobs");
      setJobs(r.jobs);
      setSel((s) => s ?? r.jobs[0]?.id ?? null);
    } catch { /* shown on next poll */ }
  }, []);

  useEffect(() => {
    j<{ files: Vid[] }>("/api/videos").then((r) => setVids(r.files)).catch((e) => setVidErr(String(e.message || e)));
    loadJobs();
    const t = setInterval(loadJobs, 15000);
    return () => clearInterval(t);
  }, [loadJobs]);

  // the progress bar: status.json every 3 s
  useEffect(() => {
    if (!sel) return;
    let alive = true;
    const tick = async () => {
      try { const s = await j<Status>(`/api/jobs/${sel}`); if (alive) { setSt(s); setStErr(""); } }
      catch (e) { if (alive) setStErr(String((e as Error).message)); }
    };
    setSt(null); tick();
    const t = setInterval(tick, 3000);
    return () => { alive = false; clearInterval(t); };
  }, [sel]);

  async function run() {
    setBusy(true); setRunErr("");
    try {
      const r = await j<{ id: string }>("/api/run", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video: link.trim() || pick, name, context, script, background: bg, background_image: bgLink, background_has_me: hasMe, omni }),
      });
      setSel(r.id); setLink(""); setScript(""); await loadJobs();
    } catch (e) { setRunErr(String((e as Error).message)); }
    setBusy(false);
  }

  return (
    <div className="wrap">
      <div className="top">
        <div className="brand">Video Studio<small>DARIJA · PURPLE ROOM</small></div>
        <button className="btn ghost" onClick={async () => { await fetch("/api/logout", { method: "POST" }); location.reload(); }}>Déconnexion</button>
      </div>
      <div className="grid">
        <div className="card">
          <h2>Nouvelle vidéo</h2>
          <label className="label">Tes vidéos récentes (Drive)</label>
          <div className="vids">
            {vids.map((v) => (
              <div key={v.id} className={`vid ${pick === v.id && !link ? "on" : ""}`} onClick={() => { setPick(v.id); setLink(""); }}>
                <span className="n">{v.name}</span>
                <span className="m">{v.size ? fmtBytes(Number(v.size)) : ""}</span>
              </div>
            ))}
            {!vids.length && <div className="vid"><span className="m">{vidErr || "Chargement…"}</span></div>}
          </div>
          <label className="label">…ou un lien Google Drive</label>
          <input className="input" placeholder="https://drive.google.com/file/d/…" value={link} onChange={(e) => setLink(e.target.value)} />
          <label className="label">Nom (optionnel)</label>
          <input className="input" placeholder="ex. cybersecurite-hook" value={name} onChange={(e) => setName(e.target.value)} />
          <label className="label">Contexte (mots du sujet, noms de technos…)</label>
          <input className="input" placeholder="cybersécurité, Python, Progma Academy" value={context} onChange={(e) => setContext(e.target.value)} />
          <label className="label">Script ou caption de référence (optionnel, prioritaire)</label>
          <textarea className="input" rows={4} value={script} onChange={(e) => setScript(e.target.value)} />
          <div style={{ marginTop: 10 }}>
            <label className="toggle"><input type="checkbox" checked={bg} onChange={(e) => setBg(e.target.checked)} /> Changer le fond<span className="soon">MatAnyone 2</span></label>
            {bg && (
              <div style={{ paddingBottom: 8 }}>
                <input className="input" placeholder="Lien Drive de l'image du nouveau fond" value={bgLink} onChange={(e) => setBgLink(e.target.value)} />
                <label className="toggle" style={{ borderTop: 0 }}><input type="checkbox" checked={hasMe} onChange={(e) => setHasMe(e.target.checked)} /> Je suis dans cette image (je serai effacé)</label>
              </div>
            )}
            <label className="toggle"><input type="checkbox" checked={omni} onChange={(e) => setOmni(e.target.checked)} /> Omni Flash (tenue)<span className="soon">clips ≤ 15 s</span></label>
          </div>
          <button className="btn wide" disabled={busy || (!pick && !link.trim())} onClick={run}>{busy ? "Lancement…" : "Run"}</button>
          {runErr && <div className="err">{runErr}</div>}
        </div>

        <div className="card">
          <h2>Projets</h2>
          <div className="jobs">
            {jobs.map((x) => (
              <div key={x.id} className={`job ${sel === x.id ? "on" : ""}`} onClick={() => setSel(x.id)}>
                <div><div className="n">{x.name}</div><div className="s">{label(x.stage, x.state)}</div></div>
                <div className={`bar ${x.state === "running" && !x.percent ? "indet" : ""}`}><i style={{ width: `${x.percent || 0}%` }} /></div>
                <div className="pct">{Math.round(x.percent || 0)}%</div>
              </div>
            ))}
            {!jobs.length && <div className="empty">Aucun projet. Choisis une vidéo et clique sur Run.</div>}
          </div>
          {sel && <Detail id={sel} st={st} err={stErr} />}
        </div>
      </div>
    </div>
  );
}

function label(stage?: string, state?: string) {
  if (state === "error") return "Erreur";
  if (stage === "review" || state === "waiting" && stage === "storyboard") return "En attente de ta validation";
  if (stage === "omni") return "À toi : clips Omni Flash";
  if (stage === "done") return "Terminé";
  if (stage === "queued") return "En file d'attente";
  const n = ALL.find((s) => s[0] === stage)?.[1];
  return n ? `${n}${state === "waiting" ? " · en attente" : ""}` : stage || "…";
}

function Detail({ id, st, err }: { id: string; st: Status | null; err: string }) {
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [md, setMd] = useState("");
  const mdFor = useRef("");

  useEffect(() => {
    const mid = st?.storyboard?.md;
    if (mid && mdFor.current !== mid) {
      mdFor.current = mid;
      fetch(`/api/text/${mid}`).then((r) => (r.ok ? r.text() : "")).then(setMd).catch(() => setMd(""));
    }
  }, [st?.storyboard?.md]);
  useEffect(() => { setNotes(""); setMsg(""); setMd(""); mdFor.current = ""; }, [id]);

  if (!st) return <div className="empty">{err || "Chargement…"}</div>;
  const stage = st.stage || "queued";
  const failed = st.state === "error";
  const stalled = st.state === "running" && ago(st.heartbeat) > 120;
  const STAGES = stagesFor(st.job?.options);
  const ORDER = ["queued", ...STAGES.map((x) => x[0])];
  const cur = ORDER.indexOf(stage);
  const reviewing = stage === "review";
  const running = st.state === "running";
  const curStep = st.steps?.find((s) => s.id === st.current);
  const indet = running && curStep && !curStep.total;

  async function act(body: object, ok: string) {
    setBusy(true); setMsg("");
    try {
      await j(`/api/jobs/${id}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setMsg(ok); setNotes("");
    } catch (e) { setMsg(String((e as Error).message)); }
    setBusy(false);
  }

  return (
    <div className="section">
      <div className="stages">
        {STAGES.map(([k, n]) => {
          const i = ORDER.indexOf(k);
          const cls = failed && k === stage ? "bad" : i < cur || stage === "done" ? "done" : k === stage ? "now" : "";
          return <span key={k} className={`chip ${cls}`}>{n}</span>;
        })}
      </div>
      <div className="head">
        <div>
          <h1>{st.slug}</h1>
          <div className="meta">
            {st.video?.name && <span>{st.video.name}</span>}
            {st.prep?.duration_s && <span>{fmtSecs(st.prep.duration_s)} après nettoyage</span>}
            {st.eta_s != null && running && <span>≈ {fmtSecs(st.eta_s)} restantes pour cette étape</span>}
          </div>
        </div>
        <div className="big-pct">{Math.round(st.percent || 0)}%</div>
      </div>
      <div className={`bar big ${indet ? "indet" : ""}`} style={{ marginTop: 12 }}><i style={{ width: `${st.percent || 0}%` }} /></div>
      <div className="msg">{st.message}</div>

      {stalled && <div className="alert stalled">Aucune nouvelle depuis {fmtSecs(ago(st.heartbeat))}. La machine est peut-être bloquée.
        <div style={{ marginTop: 8 }}><button className="btn ghost" disabled={busy} onClick={() => act({ action: "retry" }, "Relancé")}>Relancer cette étape</button></div></div>}
      {failed && <div className="alert">{st.error || "Erreur"}
        <div style={{ marginTop: 10 }}><button className="btn" disabled={busy} onClick={() => act({ action: "retry" }, "Relancé")}>Retry</button></div></div>}

      {!!st.steps?.length && (
        <div className="steps">
          {st.steps.map((s) => (
            <div key={s.id} className={`step ${s.state}`}>
              <span className="ic">{s.state === "done" ? "✓" : s.state === "error" ? "!" : ""}</span>
              <span>{s.label}</span>
              <span className="cnt">{count(s)}</span>
              {s.state === "running" && <div className="sub"><div className={`bar ${!s.total ? "indet" : ""}`}><i style={{ width: `${s.total ? Math.min(100, (100 * (s.done || 0)) / s.total) : 0}%` }} /></div></div>}
            </div>
          ))}
        </div>
      )}

      {stage === "omni" && st.cut?.to_omni && (
        <div className="section">
          <h3>À toi : Omni Flash</h3>
          <div className="md">{`1. Ouvre « clips à modifier » : ${st.cut.clips ?? ""} clips de 15 s max (clip_01.mp4, clip_02.mp4…).
2. Modifie chaque clip dans Omni Flash (ta tenue…).
3. Mets chaque résultat dans « résultats Omni » avec le MÊME nom (clip_01.mp4…).
   Un clip que tu ne modifies pas garde l'original.
4. Clique sur Continuer : le GPU recolle les clips avec ta vraie voix${st.job?.options?.background ? ", change le fond" : ""} puis Claude fait le storyboard.`}</div>
          <div className="links">
            <a href={`https://drive.google.com/drive/folders/${st.cut.to_omni}`} target="_blank" rel="noreferrer">Clips à modifier</a>
            {st.cut.from_omni && <a href={`https://drive.google.com/drive/folders/${st.cut.from_omni}`} target="_blank" rel="noreferrer">Résultats Omni (dépose ici)</a>}
            {st.cut.decisions && <a href={`https://drive.google.com/file/d/${st.cut.decisions}/view`} target="_blank" rel="noreferrer">Prises retenues</a>}
          </div>
          <button className="btn wide" disabled={busy} onClick={() => act({ action: "continue" }, "C'est parti : GPU Kaggle")}>Continuer</button>
          {msg && <div className="msg">{msg}</div>}
        </div>
      )}

      {st.post?.compare && (
        <div className="links" style={{ marginTop: 14 }}>
          <a href={`https://drive.google.com/file/d/${st.post.compare}/view`} target="_blank" rel="noreferrer">Avant / après du fond</a>
        </div>
      )}

      {st.storyboard?.png && (
        <div className="section">
          <h3>Storyboard</h3>
          <img className="sb-img" alt="storyboard" src={`https://drive.google.com/thumbnail?id=${st.storyboard.png}&sz=w2400`} />
          <div className="links">
            <a href={`https://drive.google.com/file/d/${st.storyboard.png}/view`} target="_blank" rel="noreferrer">Ouvrir en grand</a>
            {st.storyboard.folder_id && <a href={`https://drive.google.com/drive/folders/${st.storyboard.folder_id}`} target="_blank" rel="noreferrer">Dossier Drive</a>}
          </div>
          {md && <div className="md" style={{ marginTop: 12 }}>{md}</div>}
          {reviewing && (
            <div style={{ marginTop: 14 }}>
              <label className="label">Tes modifications (vide = j'accepte tel quel)</label>
              <textarea className="input" rows={5} value={notes} onChange={(e) => setNotes(e.target.value)}
                placeholder="ex. la caption à 0:12 c'est « Stack Overflow », enlève la carte à 0:40, plus de punch au début…" />
              <div className="row" style={{ marginTop: 10 }}>
                <button className="btn" disabled={busy} onClick={() => act({ action: "review", notes: "" }, "Accepté : le montage final démarre")}>Accepter</button>
                <button className="btn ghost" disabled={busy || !notes.trim()} onClick={() => act({ action: "review", notes }, "Envoyé : Claude applique tes notes")}>Envoyer mes modifications</button>
              </div>
            </div>
          )}
          {msg && <div className="msg">{msg}</div>}
        </div>
      )}

      {st.final?.video && (
        <div className="section">
          <h3>Vidéo finale</h3>
          <iframe className={`player ${st.prep?.orientation === "vertical" ? "v" : ""}`} src={`https://drive.google.com/file/d/${st.final.preview || st.final.video}/preview`} allow="autoplay" />
          <div className="links">
            <a href={`https://drive.google.com/uc?export=download&id=${st.final.video}`} target="_blank" rel="noreferrer">Télécharger (1080p)</a>
            <a href={`https://drive.google.com/file/d/${st.final.video}/view`} target="_blank" rel="noreferrer">Ouvrir dans Drive</a>
            {st.final.folder_id && <a href={`https://drive.google.com/drive/folders/${st.final.folder_id}`} target="_blank" rel="noreferrer">Dossier (SRT, rapport)</a>}
          </div>
        </div>
      )}
    </div>
  );
}
