import { NextResponse } from "next/server";
import { guard } from "@/lib/auth";
import { jobsRoot, list, readStatus } from "@/lib/drive";

export const dynamic = "force-dynamic";

export async function GET() {
  const no = await guard(); if (no) return no;
  try {
    const root = await jobsRoot();
    const folders = await list(`'${root}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false`, "files(id,name,createdTime)", "createdTime desc", 20);
    const jobs = await Promise.all(folders.map(async (f) => {
      const st = (await readStatus(f.id).catch(() => null)) || {};
      return { id: f.id, name: f.name, created: f.createdTime, stage: st.stage, state: st.state, percent: st.percent, message: st.message, heartbeat: st.heartbeat };
    }));
    return NextResponse.json({ jobs });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
