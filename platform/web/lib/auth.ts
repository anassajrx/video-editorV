// One-user login: APP_PASSWORD -> HMAC-signed cookie (APP_SECRET). Server-only.
import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const COOKIE = "ve_session";
const DAYS = 30;

function sign(v: string) {
  return createHmac("sha256", process.env.APP_SECRET || "missing-secret").update(v).digest("hex");
}

export function checkPassword(p: string): boolean {
  const want = Buffer.from(process.env.APP_PASSWORD || "");
  const got = Buffer.from(p || "");
  return want.length > 0 && want.length === got.length && timingSafeEqual(want, got);
}

export function sessionCookie() {
  const exp = String(Date.now() + DAYS * 864e5);
  return { name: COOKIE, value: `${exp}.${sign(exp)}`, httpOnly: true, secure: true, sameSite: "lax" as const, path: "/", maxAge: DAYS * 86400 };
}

export async function isAuthed(): Promise<boolean> {
  const v = (await cookies()).get(COOKIE)?.value || "";
  const [exp, sig] = v.split(".");
  if (!exp || !sig || Number(exp) < Date.now()) return false;
  const a = Buffer.from(sig), b = Buffer.from(sign(exp));
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function guard(): Promise<NextResponse | null> {
  return (await isAuthed()) ? null : NextResponse.json({ error: "login required" }, { status: 401 });
}

export const COOKIE_NAME = COOKIE;
