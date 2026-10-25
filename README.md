# signal-triage-social

Reddit social-listening agent for marketing / GTM engineers: one command,
one digest of posts that contain **buying signals** — not chatter.

Pulls recent posts from a subreddit watchlist via [treg.to](https://treg.to)
pay-per-call platform APIs, scores each post against buying-signal markers
locally, and writes a markdown digest + JSON.

Built around the [signal-triage](https://github.com/dissi-00/signal-triage) law:
a single soft hit is a breadcrumb, not demand. Stack signals before acting.

## Run

```bash
pip install -r requirements.txt
treg login                 # once; writes ~/.treg/config.json
python3 src/agent.py --watchlist "marketing,SEO,Entrepreneurship"
# → docs/<date>-digest.md  (+ .json)
```

## How it filters

Buying signals it looks for in title+body (lexical rules, no LLM):

- `which tool / what tool` — explicit tool seeking
- `recommend / alternative to / switching from` — churn & comparison language
- `worth paying / budget for` — budget language
- `broken / manual / waste of time / too expensive` — pain language
- engagement weighting: comment-volume and upvote floor

Every kept post is listed with its why-line. Posts that fail stay out.

## Tested

Command: `python3 src/agent.py --watchlist "marketing,Entrepreneurship"`
→ see [`docs/`](docs/) for the committed digest output (15 posts scanned · 10 kept).

## Disciplines

- **One command, reproducible.** No notebook, no API keys to manage beyond the CLI login.
- **Stack > single.** A lone marker hit is a breadcrumb; the ranking requires both a
  signal *and* an engagement floor to surface.
- **Silence is a valid result.** A digest with zero qualifying posts still ships —
  chasing nothing is better than inventing signal.

## Roadmap

- [ ] diff consecutive digests for rising signals
- [ ] weekly digest email
- [ ] configurable marker sets per niche (dev tools, HR tech, martech)

MIT licensed. Built by [Assis Devassy](https://assisdevassy.netlify.app) —
marketing engineer building the machines that run modern GTM.
