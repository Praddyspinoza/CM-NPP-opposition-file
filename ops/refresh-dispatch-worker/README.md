# Independent scheduled trigger for both Meghalaya dashboards

GitHub Actions `schedule` is **best effort**, and can be delayed by hours or dropped.
This optional Cloudflare Cron Worker checks whether the source JSON file in each
repository has been committed since **05:00 IST today**. If not, it calls
that repository's existing `workflow_dispatch` endpoint.

It does not modify either dashboard, source record, or feed directly.
GitHub Actions performs collection, validation and committing as before.

## Activate the external scheduler

1. Merge both companion dashboard PRs first. This Worker is **not deployed**
   automatically when you merge code into GitHub.
2. Create a fine-grained GitHub token restricted to the **two repositories only**,
   with **Actions: write** and **Contents: read** permissions. Do not check it
   into either repository. A GitHub App installation token with equivalent
   permissions is also suitable.
3. Install Node.js and Wrangler, authenticate with your Cloudflare account,
   then run from this directory:

   ```sh
   npx wrangler login
   npx wrangler secret put GITHUB_TOKEN --config wrangler.toml
   npx wrangler deploy --config wrangler.toml
   ```

4. Optional: set `ALERT_WEBHOOK_URL` using `npx wrangler secret put ALERT_WEBHOOK_URL`.
   The target must accept a Slack-compatible JSON POST with `{ "text": "..." }`.
   Check Cloudflare logs for dispatch status and GitHub's Actions tab for outcomes.
5. Test first: `node --test index.test.mjs`.

The UTC cron entries are **05:15, 05:45, 06:15 and 06:40 IST**.
The GitHub fallback cron schedules are **04:43 and 05:47 IST**.
A completed source JSON commit at or after 05:00 IST prevents unnecessary
dispatch. Concurrency controls serialize refresh runs within each repository.
The Workflow validation step rejects an empty feed or invalid timestamp.

## Important limitation

The external dispatcher avoids relying on GitHub's unreliable *scheduled*
event queue, but still relies on GitHub accepting and running workflow_dispatch
jobs and publishing the generated files. Neither GitHub nor Cloudflare offers
a strict completion-time guarantee for this pipeline.

For a contractual or truly hard **07:00 IST** deadline, run the existing
Python collectors on independent scheduled compute (for example Cloud Run
Jobs or a managed VPS), validate the JSON there, and push the resulting JSON
files to GitHub directly, with Actions as a fallback. This requires separate
cloud account access and secure repository credentials; it is not provisioned
by this PR.

Freshness here means a recent commit of a validated output, **not** that every
news source produced a new article, or that every publisher responded.
