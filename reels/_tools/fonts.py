import sys, re, urllib.parse, subprocess, pathlib, shutil

# usage: fonts.py <index.html> <gfonts sparse clone dir>  -> installs page's Google Fonts into ~/.fonts
html = pathlib.Path(sys.argv[1]).read_text(errors="ignore")
gf = pathlib.Path(sys.argv[2])
fams = set()
for url in re.findall(r'fonts\.googleapis\.com/css2?\?[^"\')\s]+', html):
    q = urllib.parse.parse_qs(urllib.parse.urlparse("https://" + url.replace("&amp;", "&")).query)
    for f in q.get("family", []):
        for part in f.split("|"):
            fams.add(part.split(":")[0].replace("+", " ").strip())
dirs = [f"{lic}/{f.lower().replace(' ', '')}" for f in fams for lic in ("ofl", "apache", "ufl")]
if dirs:
    subprocess.run(["git", "-C", str(gf), "sparse-checkout", "add", *dirs], capture_output=True)
dest = pathlib.Path.home() / ".fonts"; dest.mkdir(exist_ok=True)
for fam in sorted(fams):
    d = fam.lower().replace(" ", "")
    ttfs = [p for lic in ("ofl", "apache", "ufl") for p in (gf / lic / d).glob("*.ttf")]
    for p in ttfs:
        shutil.copy(p, dest / p.name)
    print(("ok   " if ttfs else "MISS ") + fam)
subprocess.run(["fc-cache", "-f"], capture_output=True)
