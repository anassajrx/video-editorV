// Starts the GitHub Actions workflows (fine-grained token with "Actions: write" on the repo). Server-only.
export async function dispatch(workflow: string, inputs: Record<string, string>) {
  const repo = process.env.GITHUB_REPO || "anassajrx/video-editorV";
  const ref = process.env.GITHUB_REF || "main";
  const r = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref, inputs }),
    cache: "no-store",
  });
  if (r.status !== 204) throw new Error(`GitHub dispatch ${workflow} failed (${r.status}): ${(await r.text()).slice(0, 300)}`);
}
