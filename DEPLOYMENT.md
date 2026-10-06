# Deployment target
1. Upload this folder's CONTENTS to the root of a PRIVATE GitHub repository.
2. In GitHub repository Settings > Secrets and variables > Actions, add any API credentials you possess: YOUTUBE_API_KEY, X_BEARER_TOKEN, META_ACCESS_TOKEN.
3. Verify leader/party social handles and IDs and add them to config/sources.json. Do not add credentials to that file.
4. Connect the private GitHub repo to Cloudflare Pages. Build command: none. Output directory: `/` (repository root).
5. In Cloudflare Zero Trust > Access > Applications, protect the Pages/custom-domain URL and allow only approved email addresses (one-time PIN or your chosen identity provider).
6. In GitHub Actions, run `Daily 7AM IST update` manually once to test. Thereafter it runs at 07:00 IST daily.

Note: GitHub scheduled workflows can occasionally start a few minutes late under load. The schedule is set for 07:00 IST.
