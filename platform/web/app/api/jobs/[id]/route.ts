import { NextResponse } from "next/server";
import { guard } from "@/lib/auth";
import { patchStatus, readStatus, writeText } from "@/lib/drive";
import { dispatch } from "@/lib/github";

export const dynamic = "force-dynamic";
type Ctx = { params: Promise<{ id: string }> };

export async function GET(_: Request, { params }: Ctx) {
  const no = await guard(); if (no) return no;
  const { id } = await params;
  try {
    const st = await readStatus(id);
    if (!st) return NextResponse.json({ error: "No status yet" }, { status: 404 });
    return NextResponse.json(st);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

// actions: review {accepted, notes} | retry
export async function POST(req: Request, { params }: Ctx) {
  const no = await guard(); if (no) return no;
  const { id } = await params;
  const b = await req.json();
  try {
    const st = (await readStatus(id)) as Record<string, any> | null;
    if (!st) return NextResponse.json({ error: "Unknown job" }, { status: 404 });
    if (b.action === "review") {
      const notes = String(b.notes || "").slice(0, 20000);
      await writeText("review.json", id, JSON.stringify({ accepted: !notes.trim(), notes, at: new Date().toISOString() }, null, 1));
      await patchStatus(id, { stage: "final", state: "waiting", message: notes.trim() ? "Notes sent: Claude starts the final edit" : "Accepted: Claude starts the final edit", error: null, percent: 0 });
      await dispatch("ve-claude.yml", { stage: "final", job_folder_id: id });
      return NextResponse.json({ ok: true });
    }
    if (b.action === "retry") {
      const stage = String(st.stage || "prep");
      await patchStatus(id, { state: "waiting", error: null, message: "Retrying…" });
      if (stage === "prep" || stage === "queued") {
        const job = st.job || {};
        await dispatch("ve-prep.yml", { video_file_id: String(job.video_file_id || st.video?.id || ""), slug: String(st.slug || ""), job_folder_id: id, options: "{}" });
      } else {
        await dispatch("ve-claude.yml", { stage: stage === "final" ? "final" : "storyboard", job_folder_id: id });
      }
      return NextResponse.json({ ok: true });
    }
    return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
