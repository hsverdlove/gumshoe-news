import os,sys,subprocess,uuid,email.utils,datetime
from xml.sax.saxutils import escape
base=sys.argv[1].rstrip('/') if len(sys.argv)>1 else "https://REPLACE_ME"
titles={"01-weather":"Londonderry Weather","02-us-news":"Top US News","03-world-news":"World News","04-x-feed":"From Your X Feed","05-local":"Local News & Events","06-uplifting":"Uplifting Story"}
now=datetime.datetime(2026,10,14,20,45,tzinfo=datetime.timezone(datetime.timedelta(hours=-4)))
items=[]
for i,(k,t) in enumerate(titles.items()):
    f=f"audio/{k}.mp3";d=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f]))
    desc=open(f"txt/{k}.txt").read().strip()
    pub=email.utils.format_datetime(now+datetime.timedelta(minutes=6-i))  # earlier segments newer so app lists in order
    items.append(f"""<item><title>{escape(f"Oct 14 Evening - {i+1}. {t}")}</title><description>{escape(desc)}</description>
<enclosure url="{base}/{f}?v=3" length="{os.path.getsize(f)}" type="audio/mpeg"/><guid isPermaLink="false">gumshoe-20261014-eve-{k}-v3</guid>
<pubDate>{pub}</pubDate><itunes:duration>{int(round(d))}</itunes:duration><itunes:episode>{i+1}</itunes:episode><itunes:explicit>false</itunes:explicit></item>""")
open("feed.xml","w").write(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom"><channel>
<itunes:image href="{base}/cover.jpg"/><image><url>{base}/cover.jpg</url><title>Gumshoe News</title><link>{base}/</link></image>
<title>Gumshoe News Radio (Harry)</title><link>{base}/</link><language>en-us</language>
<atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
<description>Private AM-radio-style news bulletins for Londonderry, NH.</description>
<itunes:author>Gumshoe</itunes:author><itunes:explicit>false</itunes:explicit><itunes:block>Yes</itunes:block>
<itunes:category text="News"/><itunes:type>episodic</itunes:type>
{''.join(items)}
</channel></rss>""")
