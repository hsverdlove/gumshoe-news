# Gumshoe News Radio — Harry's private podcast feed

Feed: https://hsverdlove.github.io/gumshoe-news/feed.xml  (GitHub Pages, repo hsverdlove/gumshoe-news, branch main)

## One command
```
cd /workspace/newsfeed && export PATH=$HOME/.local/bin:$PATH
python3 make_bulletin.py --edition drive --minutes 20 --date 2026-10-15 --publish
```
This renders `bulletins/<date>-<edition>/script.txt` into ONE MP3 with ID3 CHAP/CTOC chapters
(`episodes/<date>-<edition>.mp3`) plus Podcasting 2.0 chapters JSON, prunes bulletins older than 24h
(newest always kept; audio deleted), rebuilds `feed.xml` (newest on top, new GUID + `?v=` cache-buster each build),
commits as hsverdlove, pushes, waits for Pages, and prints HTTP codes for the feed, MP3s and chapter files.
Re-running the same date+edition replaces that episode. Takes ~5 min for 20 min of audio (edge-tts is network-bound).
Options: `--feed-only` (no render), `--keep-hours N`, `--script PATH`. Omit `--publish` to build locally only.

## Scheduled morning refresh (e.g. 9:00 AM ET)
1. Gather fresh facts (never invent; source everything):
   - US/world: x namespace `search_news` (query "news", max_age_hours 12) + WebSearch to verify (AP, Reuters, WSJ...).
   - Markets: futures/pre-market, prior close (indexes, sectors, 2y/10y, DXY, oil, gold, BTC), today's earnings & data.
   - Tech, AI, cyber (BleepingComputer, The Hacker News, CISA), local (location.json; londonderrytimes.net, londonderryhistory.org, town site), one uplifting story, 1-2 verified factoids.
   - X feed: user-X `get_users_me` -> `get_users_timeline` (id 1286417251, exclude retweets,replies, max_results 100, page with pagination_token to cover 12-24h).
2. Copy last script to `bulletins/<date>-<edition>/script.txt` and rewrite every section. Keep `@weather` (auto-filled live from NWS for location.json).
3. Run the one command above with `--publish`. Verify: `ffprobe -v error -show_chapters episodes/<slug>.mp3`.

Editorial rules: neutral own-words summaries; for slanted/accusatory items give the facts plus the strongest counter-view; flag unverified claims;
say X handles naturally ("Mike Lee posted"); no story repeated across sections; skip anything stale.

## script.txt format
```
# title: Thursday Drive Edition, Oct 15
# description: one-paragraph episode summary
## Chapter Title | sting=weather          <- new chapter + its music sting
[ava] Line spoken by Ava (en-US-AvaMultilingualNeural, rate +0%)
[andrew] Line spoken by Andrew (en-US-AndrewMultilingualNeural); [brian] also available
@weather                                   <- auto NWS forecast from location.json
> source: Outlet, headline (goes into the episode description)
// comment
```
Stings (self-synthesized with ffmpeg, no licensing): open, weather, us, world, markets, tech, ai, cyber, x, local, feel, factoid, close.

Files: make_bulletin.py (pipeline), build_feed.py (legacy shim -> --feed-only), episodes.json (feed registry),
episodes/ (MP3 + chapters JSON), bulletins/ (scripts), location.json, cover.jpg, index.html.
Requires: ffmpeg, edge-tts (`pip install --break-system-packages edge-tts`), gh/git logged in as hsverdlove.
