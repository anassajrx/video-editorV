import { isAuthed } from "@/lib/auth";
import Studio from "./studio";
import Login from "./login";

export const dynamic = "force-dynamic";

export default async function Page() {
  return (await isAuthed()) ? <Studio /> : <Login />;
}
