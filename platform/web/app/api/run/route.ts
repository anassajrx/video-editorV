import { NextResponse } from "next/server";
import { guard } from "@/lib/auth";
import { fileIdFromLink, folder, jobsRoot, meta, writeText } from "@/lib/drive";
import { dispatch } from "@/lib/github";

export const dynamic = "force-dynamic";

// Run: create the job folder + status.json in Drive, then start the GitHub workflow (Kaggle prep -> storyboard).
export async function POST(req: Request) {
  const no = await guard(); if (no) return no;
  const b = await req.json();
  const vid = fileIdFromLink(String(b.video || ""));
  if (!vid) return NextResponse.json({ error: "Pick a video or paste a Drive link" }, { status: 400 });
  try {
    const m = await meta(vid);
    const base = (String(b.name || "").trim() || m.name.replace(/\.[^.]+$/, ""))
      .toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "video";
    const d = new Date();
    const slug = `${base}-${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(d.getUTCDate()).padStart(2, "0")}-${String(d.getUTCHours()).padStart(2, "0")}${String(d.getUTCMinutes()).padStart(2, "0")}`;
    const background = !!b.background;
    const bgId = background ? fileIdFromLink(String(b.background_image || "")) : null;
    if (background && !bgId) return NextResponse.json({ error: "Change background: paste the Drive link of your background image" }, { status: 400 });
    if (bgId) {
      const bm = await meta(bgId);
      if (!bm.mimeType.startsWith("image/")) return NextResponse.json({ error: `The background link is not an image (${bm.mimeType})` }, { status: 400 });
    }
    const options = {
      context: String(b.context || "").slice(0, 500),
      script: String(b.script || "").slice(0, 20000),
      background,
      background_file_id: bgId,
      background_has_me: b.background_has_me !== false,
      omni: !!b.omni,
    };
    const jf = await folder(slug, await jobsRoot());
    const now = new Date().toISOString().replace(/\.\d+Z$/, "Z");
    await writeText("status.json", jf, JSON.stringify({
      slug, video: { id: vid, name: m.name, size: m.size }, job: { slug, video_file_id: vid, options },
      stage: "queued", state: "waiting", message: "Starting a Kaggle GPU", percent: 0, created: now, heartbeat: now, history: [],
    }, null, 1));
    // the script/context stay in Drive (status.json), only ids go to GitHub (public logs)
    await dispatch("ve-prep.yml", { video_file_id: vid, slug, job_folder_id: jf, options: "{}" });
    return NextResponse.json({ id: jf, slug });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
