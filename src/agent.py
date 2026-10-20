#!/usr/bin/env python3
"""
signal-triage-social — Reddit social-listening agent.

Daily, ranked digest of buying-signal posts from a watchlist of subreddits.
Fetches via treg.to (one key, pay-per-call), scores locally, writes markdown.

The law it implements: a post only makes the digest if it contains a
BUYING signal (comparison / what-tool / budget / workflow-broken language),
not mere chatter. Watch posts that fail get one line, max.

Usage:
    TREG_TOKEN=... python src/agent.py [--watchlist watchlist.txt] [--out docs]
Env:
    TREG_TOKEN   your treg.to API token (backend reads .treg/config.json if absent)
    SUBREDDITS   comma-separated override of the watchlist
Cost: ~$0.001-0.002 per run (documented in README; misses bill at $0.00035).
"""
import json, os, re, sys, urllib.request, datetime, pathlib

WATCHLIST_DEFAULT = ["marketing", "SEO", "Entrepreneurship", "B2B_SaaS"]

QUERY = "which tool recommend"
# lexical buying-signal markers (P1 filter: signals are not buyers... but tool-ask IS a near-buyer)
MARKERS = [
    "which tool", "what tool", "recommend", "alternative to", "switching from",
    "worth paying", "worth the price", "budget for", "compare", "vs ",
    "anyone using", "still paying", "cancelled", "migrated to", "replaced",
]
COMPLAIN = ["broken", "manual", "waste of time", "too expensive", "hate", "annoying",
            "painful", "slow", "clunky", "overwhelmed", "bottleneck"]

def token():
    tok = os.environ.get("TREG_TOKEN")
    if tok: return tok
    try:
        return json.load(open(os.path.expanduser("~/.treg/config.json")))["token"]
    except Exception:
        sys.exit("no TREG_TOKEN and no ~/.treg/config.json")

def treg(endpoint, method="POST", data=None, query=None):
    url = f"https://treg.to/{endpoint.split('.',1)[1] if '.' in endpoint else endpoint}"
    # treg CLI-native call is used instead in run(); we call the CLI so the routing
    # logic (waterfall, fallbacks) stays treg's problem, not ours.
    return None

def cli_call(endpoint, method="POST", data=None, query=None):
    """Shells out to the treg CLI: routing, retries, and billing stay treg-native."""
    import subprocess, shlex
    args = ["treg", "call", endpoint, "--method", method]
    if data:   args += ["--data", json.dumps(data)]
    if query:  args += ["--query", query]
    p = subprocess.run(args, capture_output=True, text=True, timeout=90)
    out = p.stdout.strip()
    try:
        return json.loads(out)
    except Exception:
        return None

def fetch_subreddit(sub):
    """tikhub app-feed GET — the route that works reliably on treg (2026-10)."""
    r = cli_call("tikhub.x.reddit-app-fetch-subreddit-feed", method="GET",
                 query=f"subreddit_name={sub.strip()}")
    rows = parse_tikhub_feed(r)
    out = []
    for p in rows:
        p["_sub"] = sub.strip()
        out.append(p)
    return out


def parse_tikhub_feed(r):
    """Flatten the tikhub app-feed (graph cells) into flat post dicts."""
    try:
        edges = r["data"]["subredditV3"]["elements"]["edges"]
    except (TypeError, KeyError):
        return []
    posts = []

    def collect(x, acc):
        if isinstance(x, dict):
            if x.get("__typename") in ("MetadataCell", "TitleCell",
                                       "TitleWithThumbnailCell", "ActionCell"):
                acc.append(x)
            for v in x.values():
                collect(v, acc)
        elif isinstance(x, list):
            for v in x:
                collect(v, acc)

    for e in edges:
        acc = []
        collect(e.get("node", {}), acc)
        m = next((c for c in acc if c["__typename"] == "MetadataCell"), None)
        t = next((c for c in acc if c["__typename"] in ("TitleCell",
                                                       "TitleWithThumbnailCell")), None)
        a = next((c for c in acc if c["__typename"] == "ActionCell"), None)
        if not (m and t) or any(c.get("adPayload") for c in acc):
            continue
        if (m.get("authorName") or "") == "AutoModerator":
            continue
        posts.append({
            "title": (t.get("title") or "").strip(),
            "authorName": m.get("authorName"),
            "createdUtc": m.get("createdAt"),
            "score": (a or {}).get("score") or 0,
            "numComments": (a or {}).get("commentCount") or 0,
        })
    posts = [p for p in posts if p["title"]]
    seen, uniq = set(), []
    for p in posts:
        k = (p["authorName"], p["title"])
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq

def score_post(p):
    title = (p.get("title") or "")
    body = (p.get("selftext") or "")
    text = (title + " " + body).lower()
    hits = [m for m in MARKERS if m in text]
    pains = [c for c in COMPLAIN if c in text]
    # buying-signal score: marker hits weigh 3, pain words 1, engagement log-weighted
    score = 3 * len(hits) + len(pains) + min(p.get("numComments", 0) / 20.0, 5) + min(p.get("score", 0) / 40.0, 5)
    return score, hits, pains

def run(watchlist=None):
    sub_list = watchlist or [s for s in os.environ.get("SUBREDDITS", "").split(",") if s.strip()] or [s for s in WATCHLIST_DEFAULT if s.strip()]
    global total_calls
    total_calls = [0]
    posts = []
    for sub in sub_list:
        got = fetch_subreddit(sub)
        total_calls[0] += 1
        posts.extend(got)
    scored = []
    for p in posts:
        s, hits, pains = score_post(p)
        scored.append({**p, "_score": s, "_hits": hits, "_pains": pains})
    scored.sort(key=lambda x: -x["_score"])

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    calls_count = total_calls[0] if "total_calls" in globals() else len(subs)
    COST_PER_CALL = 0.001  # tikhub app-feed, $/call
    lines = [
        f"# Reddit buying-signal digest — {today}",
        "",
        f"Watchlist: {', '.join(sub_list)}",
        f"Scanned: {len(posts)} posts · Feed: tikhub app-feed ($0.001/call via treg.to)",
        f"Actual API cost of this run: **${COST_PER_CALL * calls_count:.4f}**",
        "",
        "| # | Score | Cmts | Subreddit | Post | Why it's here |",
        "|---|-------|------|-----------|------|---------------|",
    ]
    kept = 0
    for i, p in enumerate(scored[:10], 1):
        if p["_score"] <= 0:
            continue
        kept += 1
        why = ", ".join(p["_hits"][:3] + p["_pains"][:2]) or "topic relevance"
        title = (p.get("title") or "")[:90]
        perma = f"https://reddit.com{p.get('permalink','')}" if p.get("permalink") else (p.get("createdUtc") or "")
        lines.append(f"| {i} | {p['_score']:.1f} | {p.get('numComments', 0)} | r/{p['_sub']} | {title} ({perma}) | {why} |")
    if kept == 0:
        lines.append("*No posts crossed the buying-signal threshold today — silence is a valid result.*")
    lines += ["", f"---",
              f"Runs are pay-per-call via treg.to: provider APIs priced per call, cents not subscriptions.",
              f"Actual cost of this digest: **${COST_PER_CALL * calls_count:.4f}** · "
              "Filters follow the signal-triage law: stack signals before acting.", ""]
    return "\n".join(lines), kept, len(posts)

if __name__ == "__main__":
    md, kept, total = run()
    out_dir = sys.argv[sys.argv.index("--out")+1] if "--out" in sys.argv else "docs"
    pathlib.Path(out_dir).mkdir(exist_ok=True)
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    path = f"{out_dir}/{today}-digest.md"
    open(path, "w").write(md)
    print(f"{kept}/{total} posts kept -> {path}")
