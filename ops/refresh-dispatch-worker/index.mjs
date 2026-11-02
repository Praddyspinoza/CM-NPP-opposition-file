// Cloudflare scheduled Worker: independent trigger, never an HTTP endpoint.
// Requires the secret GITHUB_TOKEN with Actions:write and Contents:read on both repositories.
export const TARGETS = Object.freeze([
  { repo: 'Praddyspinoza/CM-NPP-opposition-file', workflow: 'daily-update.yml', file: 'data/feed.json' },
  { repo: 'Praddyspinoza/all-opposition-to-Meghalaya-government', workflow: 'daily-sources.yml', file: 'daily_sources.json' },
]);

const IST_OFFSET_MS = 330 * 60_000;
const FRESH_AFTER_IST = '05:00:00';

export function freshnessCutoff(now = new Date()) {
  const dayInIST = new Date(now.getTime() + IST_OFFSET_MS).toISOString().slice(0, 10);
  return Date.parse(`${dayInIST}T${FRESH_AFTER_IST}+05:30`);
}

export function isFresh(lastCommitDate, now = new Date()) {
  if (typeof lastCommitDate !== 'string') return false;
  const committed = Date.parse(lastCommitDate);
  return Number.isFinite(committed) && committed >= freshnessCutoff(now);
}

export function isLateWindow(now = new Date()) {
  const local = new Date(now.getTime() + IST_OFFSET_MS);
  return (local.getUTCHours() * 60 + local.getUTCMinutes()) >= 400; // 06:40 IST
}

async function githubRequest(url, env, request, options = {}) {
  return request(url, {
    ...options,
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      'X-GitHub-Api-Version': '2022-11-28',
      ...(options.headers || {}),
    },
  });
}

export async function refreshTarget(target, env, now = new Date(), request = fetch) {
  if (!env.GITHUB_TOKEN) throw new Error('Missing GITHUB_TOKEN Worker secret');
  const base = `https://api.github.com/repos/${target.repo}`;
  const commitsUrl = `${base}/commits?sha=main&path=${encodeURIComponent(target.file)}&per_page=1`;
  let lastCommit = null;
  try {
    const response = await githubRequest(commitsUrl, env, request);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const commits = await response.json();
    lastCommit = commits[0]?.commit?.committer?.date || commits[0]?.commit?.author?.date || null;
  } catch (error) {
    // A failed check must not prevent the scheduled retry from being dispatched.
    console.warn(`Unable to check ${target.repo}: ${String(error)}`);
  }
  if (isFresh(lastCommit, now)) return { repo: target.repo, status: 'fresh', lastCommit };
  const response = await githubRequest(`${base}/actions/workflows/${encodeURIComponent(target.workflow)}/dispatches`, env, request, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ref: 'main' }),
  });
  if (response.status !== 204) throw new Error(`Dispatch failed for ${target.repo}: HTTP ${response.status}`);
  return { repo: target.repo, status: 'dispatched', lastCommit };
}

export async function runCheck(env, now = new Date(), request = fetch) {
  const settled = await Promise.allSettled(TARGETS.map(t => refreshTarget(t, env, now, request)));
  const results = settled.map((r, i) => r.status === 'fulfilled'
    ? r.value : { repo: TARGETS[i].repo, status: 'error', error: String(r.reason) });
  for (const result of results) console.log(JSON.stringify({ at: now.toISOString(), ...result }));
  const alertable = results.filter(r => r.status === 'error' || (isLateWindow(now) && r.status === 'dispatched'));
  if (alertable.length && env.ALERT_WEBHOOK_URL) {
    try {
      const message = `Meghalaya 7 AM refresh needs attention: ${alertable.map(r => r.repo + ' (' + r.status + ')').join(', ')}`;
      const response = await request(env.ALERT_WEBHOOK_URL, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: message }),
      });
      if (!response.ok) console.error(`Alert webhook returned HTTP ${response.status}`);
    } catch (error) { console.error('Alert webhook failed:', String(error)); }
  }
  if (settled.some(r => r.status === 'rejected')) throw new Error('One or more refresh dispatches failed');
  return results;
}

export default {
  async scheduled(_controller, env) {
    await runCheck(env, new Date());
  },
};
