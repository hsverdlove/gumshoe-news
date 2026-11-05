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

PRONUNCIATIONS = [(re.compile(r"\bAnthropic", re.I), "An-thropic"), (re.compile(r"\brobo-?taxi", re.I), "robo-taxi"), (re.compile(r"\bDouai\b"), "Doo-ay"), (re.compile(r"\bDelhaize\b"), "Del-haze"), (re.compile(r"\bOVHcloud\b"), "O V H cloud"), (re.compile(r"\beMudhra\b"), "ee-Mudra"), (re.compile(r"\bLiteLLM\b"), "Lite L L M"), (re.compile(r"\bIndyke\b"), "In-dike"), (re.compile(r"\bPokke\b"), "Pock-keh"), (re.compile(r"\bPROLED XDR\b"), "Pro O L E D X D R"), (re.compile(r"\bQwen\b"), "Chwen"), (re.compile(r"\bBr\u010dko\b"), "Burch-ko"), (re.compile(r"\bHuachuca\b"), "Wah-choo-kah"), (re.compile(r"\bSohlberg\b"), "Sole-berg"), (re.compile(r"\bHe Ziqi\b"), "Huh Dzuh-chee"), (re.compile(r"\bStoughton\b"), "Stow-tun"), (re.compile(r"\bKhasab\b"), "Kha-sahb"), (re.compile(r"\bChouinard\b"), "Shwee-nard"), (re.compile(r"\bNawrocki\b"), "Nah-rots-kee"), (re.compile(r"\bBundibugyo\b"), "Boon-dee-boog-yo"), (re.compile(r"\bBeilock\b"), "Buy-lock"), (re.compile(r"\bHidari\b"), "Hee-dah-ree"), (re.compile(r"\bKardashev\b"), "Kar-da-shev"), (re.compile(r"\bJunova\b"), "Joo-no-va"), (re.compile(r"\bKuaishou\b"), "Kwai-show"), (re.compile(r"\bHolownia\b"), "Ho-wov-nya"), (re.compile(r"\bKosiniak-Kamysz\b"), "Ko-shin-yak Ka-mish"), (re.compile(r"\bSwieczkowski\b"), "Shvyench-kov-skee"), (re.compile(r"\bKorwin-Piotrowska\b"), "Kor-veen Pyo-trov-ska"), (re.compile(r"\bDubuque\b"), "Duh-byook"), (re.compile(r"\bSalina\b"), "Suh-lie-nuh"), (re.compile(r"\bAraghchi\b"), "Ah-rahg-chee"), (re.compile(r"\bBosak\b"), "Bo-sock"), (re.compile(r"\bRazem\b"), "Rah-zem"), (re.compile(r"\bFourier\b"), "Foo-ree-ay"), (re.compile(r"\bPorte de Charenton\b"), "Port duh Sha-ron-tone"), (re.compile(r"\bGen Z regelt\b"), "Gen Z ray-gelt"), (re.compile(r"\bSMLib\b"), "S M Lib"), (re.compile(r"\bQuerna\b"), "Kwer-nuh"), (re.compile(r"\bPalazzolo\b"), "Pal-uh-zoh-lo"), (re.compile(r"\bChainalysis\b"), "Chain-alysis"), (re.compile(r"\bLa Plaine\b"), "La Plen"), (re.compile(r"\blevelsio\b"), "levels I O"), (re.compile(r"\bGayles\b"), "Gales"), (re.compile(r"\bSchwalb\b"), "Shwalb"), (re.compile(r"\bMojtaba\b"), "Moj-tah-bah"), (re.compile(r"\bFebres\b"), "Feb-ress"), (re.compile(r"\bDracut\b"), "Dray-cut"), (re.compile(r"\bKentintton\b"), "Ken-tin-ton"), (re.compile(r"\bMeroe\b"), "Meh-ro-ee"), (re.compile(r"\bTraderTraitor\b"), "Trader Traitor"), (re.compile(r"\bZeil\b"), "Tsile"), (re.compile(r"\bRamlila Maidan\b"), "Ram-lee-la May-dahn"), (re.compile(r"\bkimmonismus\b"), "kim-mon-iss-mus"), (re.compile(r"\bCremieux\b"), "Crem-yuh"), (re.compile(r"\bBybit\b"), "By-bit"), (re.compile(r"\bOleshky\b"), "Oh-lesh-kee"), (re.compile(r"\bNakilat\b"), "Nah-kee-laht"), (re.compile(r"\bAl Mayeda\b"), "Al My-ee-dah"), (re.compile(r"\bVucic\b"), "Voo-chitch"), (re.compile(r"\bFrimpong\b"), "Frim-pong"), (re.compile(r"\bteortaxes\b"), "tee-or-taxes"), (re.compile(r"\bmemetic sisyphus\b"), "meh-meh-tic sis-ih-fus"), (re.compile(r"\bMamdani\b"), "Mahm-dah-nee"), (re.compile(r"\bRezaei\b"), "Reh-zah-ee"), (re.compile(r"\bEl-Sayed\b"), "El Sah-yed"), (re.compile(r"\bAlmgren\b"), "Alm-gren"), (re.compile(r"\bChepkirui\b"), "Chep-kee-roo-ee"), (re.compile(r"\bYemaneberhan\b"), "Yeh-mah-neh-ber-hahn"), (re.compile(r"\bObiri\b"), "Oh-bee-ree"), (re.compile(r"\bShirka\b"), "Sheer-kah"), (re.compile(r"\bMurasu\b"), "Moo-rah-soo"), (re.compile(r"\bVerzini\b"), "Ver-zee-nee"), (re.compile(r"\bClough\b"), "Cluff"), (re.compile(r"\bRentokil\b"), "Rento-kill"), (re.compile(r"\bPeltola\b"), "Pel-toe-la"), (re.compile(r"\bEleuthera\b"), "Eh-loo-ther-ah"), (re.compile(r"\bPolisario\b"), "Po-lee-sah-ree-oh"), (re.compile(r"\bNorvell\b"), "Nor-vell"), (re.compile(r"\bGlisson\b"), "Gliss-un"), (re.compile(r"\bGuterres\b"), "Goo-TEH-resh"), (re.compile(r"\bDe Wever\b"), "Duh Vay-ver"), (re.compile(r"\bTaiz\b"), "Tah-iz"), (re.compile(r"\bArchuleta\b"), "Ar-choo-let-ah"), (re.compile(r"\bPagosa\b"), "Puh-go-sah"), (re.compile(r"\bEst\u00e9e Lauder\b"), "Ess-tay Lauder"), (re.compile(r"\bOmarchy\b"), "Oh-mar-key"), (re.compile(r"\bC3RB3R\b"), "Ser-ber"), (re.compile(r"\bGadelha\b"), "Gah-del-ya"), (re.compile(r"\bIzium\b"), "Ee-zyoom"), (re.compile(r"\bSabcobel\b"), "Sab-co-bel"), (re.compile(r"\bPiedra\b"), "Pee-ay-drah"), (re.compile(r"\bBushby\b"), "Bush-bee"), (re.compile(r"\bDari\u00e9n\b"), "Dah-ree-en"), (re.compile(r"\bLumentum\b"), "Loo-men-tum"), (re.compile(r"\bFilgueiras\b"), "Fil-gay-rus"), (re.compile(r"\bPezeshkian\b"), "Peh-zesh-kee-ahn"), (re.compile(r"\bBaghaei\b"), "Bah-gah-ee"), (re.compile(r"\bKhamenei\b"), "Kha-meh-nay"), (re.compile(r"\bMrauk-U\b"), "Mrauk-oo"), (re.compile(r"\bLoikaw\b"), "Loy-kaw"), (re.compile(r"\bRakhine\b"), "Ruh-kine"), (re.compile(r"\bChuvakin\b"), "Choo-vah-kin"), (re.compile(r"\bInovio\b"), "In-oh-vee-oh"), (re.compile(r"\bEffingham\b"), "Eff-ing-ham"), (re.compile(r"\bKomyshuvakha\b"), "Ko-mee-shoo-vah-kha"), (re.compile(r"\bZaporizhzhia\b"), "Zah-po-reezh-zhyah"), (re.compile(r"\bVideostrong\b"), "Video-strong"), (re.compile(r"\bVrountas\b"), "Vroon-tus"), (re.compile(r"\bRiney\b"), "Rye-nee"), (re.compile(r"\bArgote\b"), "Ar-go-tay"), (re.compile(r"\bKerrville\b"), "Ker-vill"), (re.compile(r"\bMonville\b"), "Mon-vill"), (re.compile(r"\bTernus\b"), "Ter-nus"), (re.compile(r"\bMECOOL\b"), "Me-cool"), (re.compile(r"\bWeissmann\b"), "Wice-man"), (re.compile(r"\bCreegan\b"), "Kree-gun"), (re.compile(r"\bQeshm\b"), "Keshm"), (re.compile(r"\bYaroslavl\b"), "Yah-ro-slah-vul"), (re.compile(r"\bKrentsel\b"), "Krent-sel"), (re.compile(r"\bHYBE\b"), "Hybe"), (re.compile(r"\bKatseye\b"), "Cats-eye"), (re.compile(r"\bDeFilippo\b"), "Deh-fil-ip-oh"), (re.compile(r"\bSoko\b"), "So-ko"), (re.compile(r"\bBTCPay\b"), "B T C Pay"), (re.compile(r"\bRothke\b"), "Roth-key"), (re.compile(r"\bYangwang\b"), "Yahng-wahng"), (re.compile(r"\bRoemmele\b"), "Rom-uh-lee"), (re.compile(r"\bFragnesia\b"), "Frag-nee-zha"), (re.compile(r"\bPHP2Shell\b"), "P H P to Shell"), (re.compile(r"\bNode-RED\b"), "Node Red"), (re.compile(r"\bLodi\b"), "Low-dye"), (re.compile(r"\bBrayla\b"), "Bray-la"), (re.compile(r"\bEntra\b"), "En-tra"), (re.compile(r"\bEisenkot\b"), "Eye-zen-coat"), (re.compile(r"\bDnipro\b"), "Dnee-pro"), (re.compile(r"\bNavier\b"), "Nav-yay"), (re.compile(r"\bRivne\b"), "Reev-neh"), (re.compile(r"\bMostyn\b"), "Moss-tin"), (re.compile(r"\bDiLorenzo\b"), "Dee-lo-ren-zo"), (re.compile(r"\bRaffensperger\b"), "Raff-ens-per-ger"), (re.compile(r"\bFiserv\b"), "Fy-serve"), (re.compile(r"\bSununu\b"), "Suh-noo-noo"), (re.compile(r"\bPlatner\b"), "Plat-ner"), (re.compile(r"\bTalarico\b"), "Tal-uh-ree-ko"), (re.compile(r"\bHinojosa\b"), "Ee-no-ho-sah"), (re.compile(r"\bTurek\b"), "Tur-ek"), (re.compile(r"\bColom\b"), "Co-lome"), (re.compile(r"\bGhalibaf\b"), "Gah-lee-bahf"), (re.compile(r"\bMedinsky\b"), "Meh-din-skee"), (re.compile(r"\bSekoia\b"), "Seh-koy-ah"), (re.compile(r"\bAyotte\b"), "Eye-ot"), (re.compile(r"\bJakhiwal\b"), "Jock-ee-vahl"), (re.compile(r"\bPunawal\b"), "Poon-ah-vahl"), (re.compile(r"\bUmarpura\b"), "Oo-mar-poo-rah"), (re.compile(r"\bKaur\b"), "Kore"), (re.compile(r"\bSprouse\b"), "Sprowss"), (re.compile(r"\bGoodlander\b"), "Good-lander"), (re.compile(r"\bHyde-Smith\b"), "Hide Smith"), (re.compile(r"\bLundgren\b"), "Lund-gren"), (re.compile(r"\bMusandam\b"), "Moo-san-dam"), (re.compile(r"\bWordfence\b"), "Word-fence"), (re.compile(r"\bHeinemeier\b"), "Hi-neh-my-er"), (re.compile(r"\bChenghong\b"), "Cheng-hong"), (re.compile(r"\bYiliang\b"), "Yee-lyahng"), (re.compile(r"\bIsbell\b"), "Iz-bel"), (re.compile(r"\bmSecure\b"), "M Secure"), (re.compile(r"\bmSeven\b"), "M Seven"), (re.compile(r"\bRudenko\b"), "Roo-den-ko"), (re.compile(r"\bAmdocs\b"), "Am-docs"), (re.compile(r"\bScalise\b"), "Skuh-leese"), (re.compile(r"\bPuente\b"), "Pwen-tay"), (re.compile(r"\bCuerpo\b"), "Kwer-po"), (re.compile(r"\bMawakana\b"), "Mah-wah-kah-nah"), (re.compile(r"\bTekedra\b"), "Teh-keh-drah"), (re.compile(r"\bLiot Hill\b"), "Lee-oh Hill"), (re.compile(r"\bTula-Tu\b"), "Too-lah Too"), (re.compile(r"\bRose-Tu\b"), "Rose Too"), (re.compile(r"\bHy4\b"), "H Y four"), (re.compile(r"\bSWE-2\b"), "S W E two"), (re.compile(r"\bPashinyan\b"), "Pah-shin-yahn"), (re.compile(r"\bMasadykov\b"), "Mah-sah-dee-kov"), (re.compile(r"\bHeilman\b"), "Hile-man"), (re.compile(r"\bLainhart\b"), "Lane-hart"), (re.compile(r"\bMacee\b"), "May-see"), (re.compile(r"\bUlysses\b"), "You-liss-eez"), (re.compile(r"\bGorham\b"), "Gor-um"), (re.compile(r"\bShelburne\b"), "Shel-burn"), (re.compile(r"\bVisegrad24\b"), "Vish-eh-grad twenty-four"), (re.compile(r"\bAl\-Nassr\b"), "Al Nasser"), (re.compile(r"\bSottiaux\b"), "So-tee-oh"), (re.compile(r"\bBitdefender\b"), "Bit-defender"), (re.compile(r"\bAppLovin\b"), "App-Lovin"), (re.compile(r"\bYerevan\b"), "Yeh-reh-vahn"), (re.compile(r"\bNIKKE\b"), "Nikkie"), (re.compile(r"\bPagham\b"), "Pag-um"), (re.compile(r"\bRatcliffe\b"), "Rat-cliff"), (re.compile(r"\bD H H\b"), "D. H. H."), (re.compile(r"\bMassie\b"), "Mass-ee"), (re.compile(r"\bCWPdoor\b"), "C W P door"), (re.compile(r"\bcwpsrv\b", re.I), "C W P serve"), (re.compile(r"\bPlovdiv\b"), "Plov-div"), (re.compile(r"\bQiAnXin\b"), "Chee-ahn-shin"), (re.compile(r"\bOobah\b"), "Oo-bah"), (re.compile(r"\bAGLT\b"), "A G L T"), (re.compile(r"\bChong Pang\b"), "Chong Pang"), (re.compile(r"\bYoani\b"), "Yo-ah-nee"), (re.compile(r"\bSánchez\b"), "San-chez"), (re.compile(r"\bSanchez\b"), "San-chez"), (re.compile(r"\b14ymedio\b", re.I), "fourteen y medio"), (re.compile(r"\bFourteen Y Medio\b"), "fourteen y medio"), (re.compile(r"\bDhillon\b"), "Dill-on"), (re.compile(r"\bHarmeet\b"), "Har-meet"), (re.compile(r"\bGippsland\b"), "Gips-land"), (re.compile(r"\bSmadja\b"), "Smad-yah"), (re.compile(r"\bTruffleHog\b"), "Truffle Hog"), (re.compile(r"\bTruffle Security\b"), "Truffle Security")]  # "ah" as in father, not an-THROP-ic

def speakable(text):
    for pat, rep in PRONUNCIATIONS: text = pat.sub(rep, text)
    return text

def tts(voice, text, out, rate="+0%"):
    text = speakable(text)
    mp3 = out + ".mp3"
    for attempt in range(6):
        if attempt: __import__("time").sleep(min(60, 5 * 2 ** (attempt - 1)))  # back off on flaky edge-tts
        try:
            r = subprocess.run(["edge-tts", "--voice", VOICES.get(voice, voice), f"--rate={rate}", "--text", text, "--write-media", mp3], capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as e:
            r = subprocess.CompletedProcess(e.cmd, 1, b"", b"edge-tts timed out"); continue
        if r.returncode == 0:
            sh(["ffmpeg", "-loglevel", "error", "-y", "-i", mp3, "-ar", str(SR), "-ac", "1", out])
            words = len(text.split())
            if words < 15 or dur(out) >= words / 4.0: break  # guard: edge-tts sometimes returns truncated audio with exit 0
            r = subprocess.CompletedProcess(r.args, 1, b"", f"truncated audio: {dur(out):.1f}s for {words} words".encode())
    else: sys.exit(f"edge-tts failed on {text[:80]!r}: {r.stderr.decode()[-400:]}")

def nws_weather(loc):
    ua = {"User-Agent": "gumshoe-news (harry)"}
    get = lambda u: json.load(urllib.request.urlopen(urllib.request.Request(u, headers=ua), timeout=30))
    p = get(f"https://api.weather.gov/points/{loc['lat']:.4f},{loc['lon']:.4f}")["properties"]
    per = get(p["forecast"])["properties"]["periods"]
    hourly = get(p["forecastHourly"])["properties"]["periods"][:4]
    lines = [f"Here's your {loc.get('place','local')} forecast from the National Weather Service."]
    h = hourly[0]
    lines.append(f"Right now it's about {h['temperature']} degrees and {h['shortForecast'].lower()}, and over the next few hours it's {', then '.join(dict.fromkeys(x['shortForecast'].lower() for x in hourly))}.")
    # First bulletin of the day gets the full 7-day; later ones only the next 24 hours.
    stamp = "/workspace/newsfeed-private/last_full_forecast_date"
    today = dt.date.today().isoformat()
    try: full = open(stamp).read().strip() != today
    except FileNotFoundError: full = True
    if full:
        for x in per[:3]: lines.append(f"{x['name']}: {x['detailedForecast']}")
        rest = [x for x in per[3:] if x["isDaytime"]][:5]
        lines.append("Looking further ahead. " + " ".join(f"{x['name']}, {x['shortForecast'].lower()}, high near {x['temperature']}." for x in rest))
        if "--dry-run" not in sys.argv: open(stamp, "w").write(today)
    else:
        for x in per[:2]: lines.append(f"{x['name']}: {x['detailedForecast']}")
    txt = " ".join(lines).replace("mph", "miles an hour")
    return txt, "NWS forecast for %s" % (loc.get("place") or "your location")

PRIVATE_LOC = os.environ.get("GUMSHOE_PRIVATE_LOC", os.path.join(os.path.dirname(ROOT), "newsfeed-private", "location.json"))
DEFAULT_LOC = {"lat": 42.8435, "lon": -71.3809, "place": "Londonderry, NH", "country": "US"}
def in_us(lat, lon):  # rough boxes: CONUS, Alaska, Hawaii, Puerto Rico
    return (24.4 <= lat <= 49.5 and -125 <= lon <= -66.8) or (51 <= lat <= 71.5 and -180 <= lon <= -129) or \
           (18.8 <= lat <= 22.4 and -160.5 <= lon <= -154.6) or (17.8 <= lat <= 18.6 and -67.4 <= lon <= -65.2)
def load_location():
    """Precise coords live ONLY in the private file (outside the public repo). Fallback: Londonderry, NH."""
    try:
        loc = json.load(open(PRIVATE_LOC))
        age = dt.datetime.now(TZ) - dt.datetime.fromisoformat(loc["updated_at"])
        if age > dt.timedelta(hours=24): raise ValueError("stale")
        loc["lat"], loc["lon"] = float(loc["lat"]), float(loc["lon"])
    except Exception as e:
        print(f"location: using default Londonderry, NH ({e.__class__.__name__}: {e})"); loc = dict(DEFAULT_LOC)
    loc["abroad"] = (loc.get("country", "US").upper() != "US") or not in_us(loc["lat"], loc["lon"])
    return loc
def write_public_location(loc):
    json.dump({"place": "" if loc["abroad"] else loc.get("place", ""), "updated_at": loc.get("updated_at", dt.datetime.now(TZ).isoformat())},
              open(os.path.join(ROOT, "location.json"), "w"), indent=2)
def drop_local(chapters):
    """Out of country: remove Weather and Local chapters entirely (and @weather lines in combined Open & Weather)."""
    out = []
    for ch in chapters:
        if ch["sting"] in ("weather", "local") or re.search(r"\blocal\b", ch["title"], re.I) or ch["title"].strip().lower() == "weather": continue
        ch["lines"] = [x for x in ch["lines"] if x[0] != "@weather"]
        ch["title"] = re.sub(r"\s*(&|and)\s*Weather\b", "", ch["title"], flags=re.I).strip() or "Open"
        out.append(ch)
    return out

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

def render(script, slug, minutes, force_abroad=False, dry=False):
    meta, chapters = parse_script(script)
    loc = load_location()
    if force_abroad: loc["abroad"] = True
    if loc["abroad"]:
        chapters = drop_local(chapters)
        meta["sources"] = [x for x in meta["sources"] if not re.search(r"weather|NWS|location", x, re.I)]
    if not dry: write_public_location(loc)
    if dry:
        print("DRY RUN abroad=%s chapters:" % loc["abroad"], [c["title"] for c in chapters]); print("sources:", meta["sources"]); return None
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

COORD = re.compile(r"-?\d{1,3}\.\d{3,}\s*,\s*-?\d{1,3}\.\d{3,}")
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
    if COORD.search(xml): sys.exit("refusing to write feed.xml: coordinate-like string found")
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
    ap.add_argument("--abroad", action="store_true", help="test: force out-of-country path (no Weather/Local)")
    ap.add_argument("--dry-run", action="store_true", help="parse + apply rules only; no audio, no feed, no publish")
    a = ap.parse_args(); slug = f"{a.date}-{a.edition}"
    if not a.feed_only:
        render(a.script or os.path.join(ROOT, "bulletins", slug, "script.txt"), slug, a.minutes, a.abroad, a.dry_run)
        if a.dry_run: sys.exit(0)
    prune(a.keep_hours); build_feed()
    if a.publish: publish(f"Bulletin {slug}")
