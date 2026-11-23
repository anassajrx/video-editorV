// Server-only Google Drive helpers (the user's own OAuth client + refresh token, from Vercel env vars).
const API = "https://www.googleapis.com/drive/v3";
const UPLOAD = "https://www.googleapis.com/upload/drive/v3";
const FOLDER = "application/vnd.google-apps.folder";

let cached: { token: string; exp: number } | null = null;

async function token(): Promise<string> {
  if (cached && Date.now() < cached.exp - 120_000) return cached.token;
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: process.env.GOOGLE_CLIENT_ID!,
      client_secret: process.env.GOOGLE_CLIENT_SECRET!,
      refresh_token: process.env.GOOGLE_REFRESH_TOKEN!,
      grant_type: "refresh_token",
    }),
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`Google token refresh failed (${r.status})`);
  const j = await r.json();
  cached = { token: j.access_token, exp: Date.now() + j.expires_in * 1000 };
  return cached.token;
}

async function api(url: string, init: RequestInit = {}): Promise<Response> {
  const r = await fetch(url, {
    ...init,
    headers: { ...(init.headers || {}), Authorization: `Bearer ${await token()}` },
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`Drive ${r.status}: ${(await r.text()).slice(0, 300)}`);
  return r;
}

export type DFile = { id: string; name: string; size?: string; mimeType: string; createdTime?: string; modifiedTime?: string };

export async function list(q: string, fields = "files(id,name,size,mimeType,createdTime,modifiedTime)", orderBy = "createdTime desc", pageSize = 50): Promise<DFile[]> {
  const p = new URLSearchParams({ q, fields, orderBy, pageSize: String(pageSize), supportsAllDrives: "true", includeItemsFromAllDrives: "true" });
  return (await (await api(`${API}/files?${p}`)).json()).files;
}

const esc = (s: string) => s.replace(/\\/g, "\\\\").replace(/'/g, "\\'");

export async function find(name: string, parent: string, folder = false): Promise<string | null> {
  const fs = await list(`name = '${esc(name)}' and '${parent}' in parents and trashed = false${folder ? ` and mimeType = '${FOLDER}'` : ""}`, "files(id,name,mimeType)", "createdTime desc", 5);
  return fs[0]?.id ?? null;
}

export async function folder(name: string, parent: string): Promise<string> {
  const id = await find(name, parent, true);
  if (id) return id;
  const r = await api(`${API}/files?supportsAllDrives=true&fields=id`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, mimeType: FOLDER, parents: [parent] }),
  });
  return (await r.json()).id;
}

export async function meta(id: string): Promise<DFile> {
  return (await api(`${API}/files/${id}?fields=id,name,size,mimeType,createdTime&supportsAllDrives=true`)).json();
}

export async function readText(id: string): Promise<string> {
  return (await api(`${API}/files/${id}?alt=media&supportsAllDrives=true`)).text();
}

export async function writeText(name: string, parent: string, text: string, mime = "application/json"): Promise<string> {
  const id = await find(name, parent);
  if (id) {
    await api(`${UPLOAD}/files/${id}?uploadType=media&supportsAllDrives=true`, { method: "PATCH", headers: { "Content-Type": mime }, body: text });
    return id;
  }
  const b = "vebnd" + Date.now();
  const body = `--${b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${JSON.stringify({ name, parents: [parent] })}\r\n--${b}\r\nContent-Type: ${mime}\r\n\r\n${text}\r\n--${b}--`;
  const r = await api(`${UPLOAD}/files?uploadType=multipart&supportsAllDrives=true&fields=id`, {
    method: "POST", headers: { "Content-Type": `multipart/related; boundary=${b}` }, body,
  });
  return (await r.json()).id;
}

export async function jobsRoot(): Promise<string> {
  const root = (await (await api(`${API}/files/root?fields=id`)).json()).id;
  return folder("jobs", await folder("video-editor", root));
}

export async function readStatus(jobFolder: string): Promise<Record<string, unknown> | null> {
  const id = await find("status.json", jobFolder);
  if (!id) return null;
  try { return JSON.parse(await readText(id)); } catch { return null; }
}

export async function patchStatus(jobFolder: string, patch: Record<string, unknown>) {
  const st = (await readStatus(jobFolder)) || {};
  Object.assign(st, patch, { heartbeat: new Date().toISOString().replace(/\.\d+Z$/, "Z") });
  await writeText("status.json", jobFolder, JSON.stringify(st, null, 1));
  return st;
}

export function fileIdFromLink(s: string): string | null {
  const m = s.match(/\/d\/([\w-]{20,})/) || s.match(/[?&]id=([\w-]{20,})/) || s.trim().match(/^([\w-]{20,})$/);
  return m ? m[1] : null;
}
