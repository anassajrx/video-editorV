import { NextResponse } from "next/server";
import { guard } from "@/lib/auth";
import { list } from "@/lib/drive";

export const dynamic = "force-dynamic";

// The newest videos in the user's Drive (for the picker).
export async function GET() {
  const no = await guard(); if (no) return no;
  try {
    const files = await list("mimeType contains 'video/' and trashed = false", "files(id,name,size,mimeType,createdTime,modifiedTime)", "modifiedTime desc", 40);
    return NextResponse.json({ files });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
