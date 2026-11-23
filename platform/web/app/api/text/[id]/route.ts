import { NextResponse } from "next/server";
import { guard } from "@/lib/auth";
import { meta, readText } from "@/lib/drive";

export const dynamic = "force-dynamic";

// Small text files (storyboard.md, report.md) for display.
export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const no = await guard(); if (no) return no;
  const { id } = await params;
  try {
    const m = await meta(id);
    if (Number(m.size || 0) > 500_000) return NextResponse.json({ error: "too big" }, { status: 413 });
    return new NextResponse(await readText(id), { headers: { "Content-Type": "text/plain; charset=utf-8" } });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
