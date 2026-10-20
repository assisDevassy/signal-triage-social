# signal-triage-social

Reddit social-listening agent for marketing / GTM engineers: one command,
one daily digest of posts that contain **buying signals** — not chatter.

Pulls recent posts from a subreddit watchlist via [treg.to](https://treg.to)
(one API key, pay-per-call platform APIs — cents, not subscriptions), scores
each post against buying-signal markers locally, and writes a dated markdown
digest + JSON.

Built around the [signal-triage](https://github.com/dissi-00/signal-triage) law:
a single soft hit is a breadcrumb, not demand. Stack signals before acting.

## Run

```bash
pip install treg           # or: pip install -r requirements.txt
treg login                 # once; writes ~/.treg/config.json
python3 src/agent.py --watchlist "marketing,SEO,Entrepreneurship"
# → docs/2026-10-20-digest.md  (+ .json)
```

Cost: **$0.001 per subreddit per run** (tikhub app-feed route; ~4 posts/digest
for 4 subreddits = ≈ $0.12/month if run daily). No minimums, no subscription.
A $5 prepaid credit lasts months at this rate.

## How it filters

 Buying signals it looks for in title+body (lexical rules, no LLM):

- `which tool / what tool` — explicit tool seeking
- `recommend / alternative to / switching from` — churn & comparison language
- `worth paying / budget for` — budget language
- `broken / manual / waste of time / too expensive` — pain language
- engagement weighting: comment-volume and upvote floor

Every kept post is listed with its why-line. Posts that fail stay out.

## Real run — 2026-10-20

Command: `python3 src/agent.py --watchlist "marketing,Entrepreneurship"`
→ see [`docs/2026-10-20-digest.md`](docs/2026-10-20-digest.md)
(15 posts scanned · 10 kept · API cost $0.0050 · balance after: $0.0002)

## Disciplines

- **One command, reproducible.** No notevcode, no notebook, no API keys besides the treg CLI.
- **Cost-visible.** Every digest prints its own actual dollar cost.
- **Stack > single.** A lone marker hit is a breadcrumb; the ranking requires both a
  signal *and* an engagement floor to surface.

## Roadmap

- [ ] persist yesterday's digest, diff for "rising signals"
- [ ] weekly digest email via SMTP
- [ ] configurable marker sets per niche (dev tools, HR tech, martech)

MIT licensed. Built by [@assis devassy](https://assisdevassy.netlify.app) —
marketing engineer building the machines that run modern GTM.
