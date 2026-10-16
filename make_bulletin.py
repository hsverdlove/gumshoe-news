#!/usr/bin/env python3
"""Gumshoe News Radio bulletin builder: script.txt -> one MP3 with ID3 chapters -> feed.xml (+ optional publish).
See README.md."""
import argparse, datetime as dt, email.utils, json, os, re, subprocess, sys, tempfile, shutil, urllib.request
from xml.sax.saxutils import escape
ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = "https://hsverdlove.github.io/gumshoe-news"
TZ = dt.timezone(dt.timedelta(hours=-4))  # America/New_York (EDT); fine for feed timestamps
VOICES = {"ava": "en-US-AvaMultilingualNeural", "andrew": "en-US-AndrewMultilingualNeural", "brian": "en-US-BrianMultilingualNeural"}
# sting = notes (Hz) ; each section type gets its own self-synthesized jingle
STINGS = {"open": [392, 523, 659, 784, 1047], "weather": [523, 659, 784], "us": [392, 494, 587], "world": [440, 554, 659],
          "markets": [330, 415, 494, 659], "tech": [587, 880, 740], "ai": [659, 988, 831], "cyber": [294, 370, 294, 440],
          "x": [494, 740, 988], "local": [587, 740, 880], "feel": [659, 784, 1047], "factoid": [1047, 1319], "close": [784, 659, 523, 392]}
SR = 24000
def sh(cmd): subprocess.run(cmd, check=True)
def dur(f): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))

def make_sting(kind, out):
    notes = STINGS.get(kind, STINGS["open"]); n = len(notes); step = 0.18
    ins, flt = [], []
    for i, f in enumerate(notes):
        d = step if i < n - 1 else 0.9
        ins += ["-f", "lavfi", "-i", f"sine=f={f}:d={d}"]
        flt.append(f"[{i}]volume={0.30 if i < n-1 else 0.35}[s{i}]")
    chain = ";".join(flt) + ";" + "".join(f"[s{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,aecho=0.8:0.55:110:0.3,afade=t=out:st={step*(n-1)+0.5}:d=0.6,aresample={SR}[o]"
    sh(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", chain, "-map", "[o]", "-ac", "1", out])

def silence(sec, out): sh(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", str(sec), out])

def tts(voice, text, out, rate="+0%"):
    mp3 = out + ".mp3"
    for attempt in range(3):
        try:
            r = subprocess.run(["edge-tts", "--voice", VOICES.get(voice, voice), f"--rate={rate}", "--text", text, "--write-media", mp3], capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as e:
            r = subprocess.CompletedProcess(e.cmd, 1, b"", b"edge-tts timed out"); continue
        if r.returncode == 0: break
    else: sys.exit(f"edge-tts failed: {r.stderr.decode()[:300]}")
    sh(["ffmpeg", "-loglevel", "error", "-y", "-i", mp3, "-ar", str(SR), "-ac", "1", out])

def nws_weather(loc):
    ua = {"User-Agent": "gumshoe-news (harry)"}
    get = lambda u: json.load(urllib.request.urlopen(urllib.request.Request(u, headers=ua), timeout=30))
    p = get(f"https://api.weather.gov/points/{loc['lat']:.4f},{loc['lon']:.4f}")["properties"]
    per = get(p["forecast"])["properties"]["periods"]
    hourly = get(p["forecastHourly"])["properties"]["periods"][:4]
    lines = [f"Here's your {loc.get('place','local')} forecast from the National Weather Service."]
    h = hourly[0]
    lines.append(f"Right now it's about {h['temperature']} degrees and {h['shortForecast'].lower()}, and over the next few hours it's {', then '.join(dict.fromkeys(x['shortForecast'].lower() for x in hourly))}.")
    for x in per[:3]: lines.append(f"{x['name']}: {x['detailedForecast']}")
    rest = [x for x in per[3:] if x["isDaytime"]][:5]
    lines.append("Looking further ahead. " + " ".join(f"{x['name']}, {x['shortForecast'].lower()}, high near {x['temperature']}." for x in rest))
    txt = " ".join(lines).replace("mph", "miles an hour")
    return txt, "NWS api.weather.gov forecast for %.4f,%.4f" % (loc["lat"], loc["lon"])

def parse_script(path):
    meta, chapters, cur = {"sources": []}, [], None
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("//"): continue
        if line.startswith("# "):
            k, _, v = line[2:].partition(":"); meta[k.strip()] = v.strip()
        elif line.startswith("> source:"): meta["sources"].append(line.split(":", 1)[1].strip())
        elif line.startswith("## "):
            title, _, opts = line[3:].partition("|")
            o = dict(kv.strip().split("=", 1) for kv in opts.split(",") if "=" in kv)
            cur = {"title": title.strip(), "sting": o.get("sting", "open"), "lines": []}; chapters.append(cur)
        elif line == "@weather": cur["lines"].append(("@weather", ""))
        elif m := re.match(r"\[(\w+)\]\s*(.*)", line): cur["lines"].append((m.group(1).lower(), m.group(2)))
        elif cur and cur["lines"]: v, t = cur["lines"][-1]; cur["lines"][-1] = (v, t + " " + line)
    return meta, chapters

def render(script, slug, minutes):
    meta, chapters = parse_script(script)
    loc = json.load(open(os.path.join(ROOT, "location.json")))
    work = tempfile.mkdtemp(prefix="bulletin-"); parts, marks, t = [], [], 0.0
    gap = os.path.join(work, "gap.wav"); silence(0.45, gap)
    for ci, ch in enumerate(chapters):
        marks.append((t, ch["title"]))
        s = os.path.join(work, f"sting{ci}.wav"); make_sting(ch["sting"], s); parts.append(s); t += dur(s)
        for li, (v, text) in enumerate(ch["lines"]):
            if v == "@weather":
                text, src = nws_weather(loc); v = "ava"; meta["sources"].insert(0, src)
            f = os.path.join(work, f"c{ci}_{li}.wav"); tts(v, text, f); parts += [f, gap]; t += dur(f) + dur(gap)
    lst = os.path.join(work, "list.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    md = os.path.join(work, "meta.txt")
    with open(md, "w") as m:
        m.write(f";FFMETADATA1\ntitle={meta['title']}\nartist=Gumshoe News Radio\nalbum=Gumshoe News Radio\n")
        ends = [x[0] for x in marks[1:]] + [t]
        for (st, ti), en in zip(marks, ends):
            m.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(st*1000)}\nEND={int(en*1000)}\ntitle={ti}\n")
    os.makedirs(os.path.join(ROOT, "episodes"), exist_ok=True)
    out = os.path.join(ROOT, "episodes", f"{slug}.mp3")
    sh(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", md, "-map_metadata", "1", "-map_chapters", "1",
        "-c:a", "libmp3lame", "-b:a", "64k", "-ac", "1", "-id3v2_version", "3", "-write_id3v1", "1", out])
    if os.path.exists(os.path.join(ROOT, "cover.jpg")):  # embed cover art
        tmp = out + ".tmp.mp3"
        sh(["ffmpeg", "-loglevel", "error", "-y", "-i", out, "-i", os.path.join(ROOT, "cover.jpg"), "-map", "0:a", "-map", "1:v", "-map_chapters", "0",
            "-c", "copy", "-id3v2_version", "3", "-metadata:s:v", "title=Cover", "-disposition:v", "attached_pic", tmp]); os.replace(tmp, out)
    total = dur(out)
    json.dump({"version": "1.2.0", "chapters": [{"startTime": round(s, 2), "title": ti} for s, ti in marks]},
              open(os.path.join(ROOT, "episodes", f"{slug}.chapters.json"), "w"), indent=1)
    shutil.rmtree(work)
    if minutes and abs(total / 60 - minutes) > minutes * 0.25: print(f"WARNING: {total/60:.1f} min vs target {minutes}")
    desc = meta.get("description", "") + "\n\nChapters:\n" + "\n".join(f"{int(s//60)}:{int(s%60):02d} {ti}" for s, ti in marks) + \
           "\n\nSources:\n" + "\n".join("- " + x for x in meta["sources"])
    reg = load_reg(); reg = [e for e in reg if e["slug"] != slug]
    reg.append({"slug": slug, "title": meta["title"], "pub": dt.datetime.now(TZ).isoformat(), "duration": round(total), "size": os.path.getsize(out), "description": desc})
    save_reg(reg); print(f"built {out} {total/60:.2f} min, {len(marks)} chapters"); return out

REG = os.path.join(ROOT, "episodes.json")
def load_reg(): return json.load(open(REG)) if os.path.exists(REG) else []
def save_reg(r): json.dump(r, open(REG, "w"), indent=1)

def prune(hours=24):
    reg = load_reg(); now = dt.datetime.now(TZ); keep = []
    for e in sorted(reg, key=lambda e: e["pub"], reverse=True):
        if keep and now - dt.datetime.fromisoformat(e["pub"]) > dt.timedelta(hours=hours):
            for ext in (".mp3", ".chapters.json"):
                p = os.path.join(ROOT, "episodes", e["slug"] + ext)
                if os.path.exists(p): os.remove(p)
            print("pruned", e["slug"])
        else: keep.append(e)
    save_reg(keep)

def build_feed(base=BASE):
    reg = sorted(load_reg(), key=lambda e: e["pub"], reverse=True); items = []
    for e in reg:
        ver = e["pub"][:16].replace(":", "").replace("-", "")
        items.append(f"""<item><title>{escape(e['title'])}</title><description>{escape(e['description'])}</description>
<content:encoded><![CDATA[{e['description'].replace(chr(10), '<br/>')}]]></content:encoded>
<enclosure url="{base}/episodes/{e['slug']}.mp3?v={ver}" length="{e['size']}" type="audio/mpeg"/>
<guid isPermaLink="false">gumshoe-{e['slug']}-{ver}</guid><pubDate>{email.utils.format_datetime(dt.datetime.fromisoformat(e['pub']))}</pubDate>
<itunes:duration>{e['duration']}</itunes:duration><itunes:explicit>false</itunes:explicit><itunes:episodeType>full</itunes:episodeType>
<podcast:chapters url="{base}/episodes/{e['slug']}.chapters.json?v={ver}" type="application/json+chapters"/></item>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:podcast="https://podcastindex.org/namespace/1.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<title>Gumshoe News Radio (Harry)</title><link>{base}/</link><language>en-us</language>
<atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
<description>Private AM-radio-style news bulletins for Harry.</description>
<itunes:author>Gumshoe</itunes:author><itunes:explicit>false</itunes:explicit><itunes:block>Yes</itunes:block>
<itunes:image href="{base}/cover.jpg"/><image><url>{base}/cover.jpg</url><title>Gumshoe News Radio (Harry)</title><link>{base}/</link></image>
<itunes:category text="News"/><itunes:type>episodic</itunes:type>
{chr(10).join(items)}
</channel></rss>"""
    open(os.path.join(ROOT, "feed.xml"), "w").write(xml)
    import xml.dom.minidom; xml.dom.minidom.parse(os.path.join(ROOT, "feed.xml")); print("feed.xml written,", len(items), "episodes")

def publish(msg):
    os.chdir(ROOT); sh(["git", "pull", "-q", "--rebase", "--autostash"]); sh(["git", "add", "-A"])
    subprocess.run(["git", "-c", "user.name=hsverdlove", "-c", "user.email=hsverdlove@users.noreply.github.com", "commit", "-qm", msg])
    sh(["git", "push", "-q"])
    import time
    reg = sorted(load_reg(), key=lambda e: e["pub"], reverse=True)
    for _ in range(40):
        try:
            feed = urllib.request.urlopen(BASE + "/feed.xml?nocache=%d" % time.time(), timeout=20).read().decode()
            if f"gumshoe-{reg[0]['slug']}-{reg[0]['pub'][:16].replace(':', '').replace('-', '')}" in feed:
                break
        except Exception: pass
        time.sleep(10)
    else: sys.exit("feed did not update within ~7 min")
    for path in ["feed.xml"] + [f"episodes/{e['slug']}.mp3" for e in reg] + [f"episodes/{e['slug']}.chapters.json" for e in reg]:
        code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{BASE}/{path}"], capture_output=True, text=True).stdout
        print(code, path)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", default="bulletin", help="slug part, e.g. drive")
    ap.add_argument("--minutes", type=float, default=0)
    ap.add_argument("--script", help="script.txt (default bulletins/<date>-<edition>/script.txt)")
    ap.add_argument("--date", default=dt.datetime.now(TZ).strftime("%Y-%m-%d"))
    ap.add_argument("--feed-only", action="store_true"); ap.add_argument("--publish", action="store_true")
    ap.add_argument("--keep-hours", type=float, default=24)
    a = ap.parse_args(); slug = f"{a.date}-{a.edition}"
    if not a.feed_only:
        render(a.script or os.path.join(ROOT, "bulletins", slug, "script.txt"), slug, a.minutes)
    prune(a.keep_hours); build_feed()
    if a.publish: publish(f"Bulletin {slug}")
