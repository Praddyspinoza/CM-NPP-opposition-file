# Meghalaya Opposition Tracker
Private public-source dashboard for Mukul Sangma, Ardent Miller Basaiawmoit and Saleng A. Sangma.

## Automatic update
GitHub Actions runs `scripts/update.py` daily at 01:30 UTC = 07:00 IST. It collects Google News RSS immediately. Optional official-source adapters activate when repository secrets are present:
- `YOUTUBE_API_KEY` — YouTube Data API
- `X_BEARER_TOKEN` — X API v2
- `META_ACCESS_TOKEN` — Meta Graph API for Facebook/Instagram accounts configured in `config/sources.json`

The social account IDs/handles in `config/sources.json` must be verified before adding them. Empty arrays are intentionally ignored rather than guessing at official accounts.

## Privacy / deployment
A private GitHub repository protects source code but does not itself make a static website private. Deploy the repo to Cloudflare Pages and put Cloudflare Access in front of the Pages hostname/custom domain. Allow only approved email addresses. The Personal Secretary only needs the protected URL and login, not GitHub.

## Source integrity
The dashboard is descriptive, not a political scorecard. Allegations and criticisms remain attributed. Every item keeps its original URL and source. Google News RSS links may redirect through Google News to the publisher.
