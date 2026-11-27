import sys, asyncio, pathlib, shutil, subprocess, time, base64
from playwright.async_api import async_playwright

# usage: record_book.py <index.html> <out.mp4> [max_pages]
# 1) records the real intro (tap to open), 2) screenshots each screen of the invitation,
# 3) plays the screens as book pages that turn like a real book, 4) joins both into one 1080x1920 MP4.
# Dates, times, venues and countdowns are blurred (same rules as record.py).
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from blur import BLUR_JS

src = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(sys.argv[2]).resolve()
scan_pages = 8
keep_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 3   # hero + the most striking sections only
W, H = 540, 960
INTRO = 3.0      # seconds of real intro animation kept
HOLD, FLIP = 1.7, 0.9

BOOK = """<!doctype html><html><head><style>
html,body{margin:0;height:100%;background:#1b1714;overflow:hidden}
#book{position:absolute;inset:0;perspective:1800px}
.pg{position:absolute;inset:0;background-size:cover;background-position:center;transform-origin:left center;
    transform-style:preserve-3d;backface-visibility:hidden;box-shadow:0 0 0 rgba(0,0,0,0)}
.pg::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.0),rgba(0,0,0,.0));pointer-events:none}
.turn{transition:transform %FLIP%s cubic-bezier(.45,.05,.35,1), filter %FLIP%s;transform:rotateY(-178deg);filter:brightness(.75)}
.shade{position:absolute;top:0;bottom:0;left:0;width:28px;background:linear-gradient(90deg,rgba(0,0,0,.35),rgba(0,0,0,0));z-index:999}
</style></head><body><div id="book">%PAGES%</div><div class="shade"></div><script>
const pgs=[...document.querySelectorAll('.pg')];
pgs.forEach((p,i)=>p.style.zIndex=pgs.length-i);
window.play=()=>new Promise(res=>{let i=0;const step=()=>{if(i>=pgs.length-1)return setTimeout(res,%HOLDMS%);
 setTimeout(()=>{pgs[i].classList.add('turn');i++;setTimeout(step,%FLIPMS%)},%HOLDMS%)};step();});
</script></body></html>"""

def pick(shots, k):
    """Keep the hero plus the k-1 most visually rich, mutually different screens, in page order."""
    from PIL import Image, ImageStat
    if len(shots) <= k: return shots
    def sig(p):
        im = Image.open(p).convert("RGB").resize((24, 42))
        return im, sum(ImageStat.Stat(im).stddev)
    info = [(p,) + sig(p) for p in shots]
    rest = sorted(info[1:], key=lambda x: -x[2])
    chosen = [info[0]]
    def diff(a, b):
        return sum(abs(x - y) for pa, pb in zip(list(a.getdata()), list(b.getdata())) for x, y in zip(pa, pb))
    for c in rest:
        if len(chosen) >= k: break
        if all(diff(c[1], o[1]) > 24 * 42 * 3 * 18 for o in chosen): chosen.append(c)
    for c in rest:
        if len(chosen) >= k: break
        if c not in chosen: chosen.append(c)
    keep = {c[0] for c in chosen}
    return [p for p in shots if p in keep]

async def main():
    work = out.parent / ("_book_" + out.stem)
    shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        # pass 1: intro video + page screenshots
        ctx = await b.new_context(viewport={"width": W, "height": H}, is_mobile=True, has_touch=True,
                                  record_video_dir=str(work / "v1"), record_video_size={"width": W, "height": H})
        await ctx.add_init_script(BLUR_JS)
        t0 = time.monotonic()
        pg = await ctx.new_page()
        await pg.goto(src.as_uri(), wait_until="load")
        await pg.wait_for_timeout(1500)
        t_tap = time.monotonic() - t0
        await pg.mouse.click(W / 2, H / 2)
        await pg.wait_for_timeout(1500)
        await pg.mouse.click(W / 2, H / 2)
        await pg.wait_for_timeout(int(INTRO * 1000))
        shots = []
        # capture whole sections so no page is cut in half
        n_sec = await pg.evaluate("""() => {
            const vis = e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
                return r.height > 160 && r.width > 200 && cs.display !== 'none' && cs.visibility !== 'hidden' && cs.position !== 'fixed'; };
            const rsvp = e => /rsvp|count|timer|anket|cavab/i.test((e.className||'') + ' ' + (e.id||'')) || e.querySelector('form,input,textarea,select');
            let secs = [...document.querySelectorAll('section')].filter(vis);
            const nonR = secs.filter(e => !rsvp(e)); if (nonR.length >= 2) secs = nonR;
            secs = secs.filter(e => !secs.some(o => o !== e && o.contains(e)));
            secs.forEach((e, i) => e.dataset.dvSec = i);
            return secs.length; }""")
        if n_sec >= 2:
            for i in range(min(n_sec, scan_pages)):
                loc = pg.locator(f'[data-dv-sec="{i}"]')
                await loc.evaluate("e => e.scrollIntoView({block: 'start'})")
                await pg.wait_for_timeout(1000)
                f = work / f"p{i}.png"
                try:
                    await loc.screenshot(path=str(f), timeout=8000)
                    shots.append(f)
                except Exception:
                    pass
        if len(shots) < 2:
            shots, last = [], None
            for i in range(scan_pages):
                await pg.wait_for_timeout(900)
                f = work / f"p{i}.png"
                await pg.screenshot(path=str(f))
                data = f.read_bytes()
                if data == last: f.unlink(); break
                shots.append(f); last = data
                y0 = await pg.evaluate("window.scrollY + (document.scrollingElement||document.body).scrollTop")
                await pg.mouse.wheel(0, H * 0.92)
                await pg.wait_for_timeout(400)
                y1 = await pg.evaluate("window.scrollY + (document.scrollingElement||document.body).scrollTop")
                if y1 == y0 and i > 0: break
        await ctx.close()
        shots = pick(shots, keep_pages)
        # pass 2: book flip of the screenshots
        def page_div(path):
            from PIL import Image
            im = Image.open(path).convert("RGB"); w, h = im.size
            if h > w * (H / W) * 1.5:            # very tall section: keep its top part only
                im = im.crop((0, 0, w, int(w * H / W * 1.15))); im.save(path); w, h = im.size
            bg = "rgb(%d,%d,%d)" % im.getpixel((2, 2))
            b64 = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
            return (f'<div class="pg" style="background:{bg} url(data:image/png;base64,{b64}) center/contain no-repeat"></div>')
        pages = "".join(page_div(s_) for s_ in shots)
        html = (BOOK.replace("%PAGES%", pages).replace("%FLIP%", str(FLIP))
                .replace("%HOLDMS%", str(int(HOLD * 1000))).replace("%FLIPMS%", str(int(FLIP * 1000))))
        (work / "book.html").write_text(html)
        ctx2 = await b.new_context(viewport={"width": W, "height": H},
                                   record_video_dir=str(work / "v2"), record_video_size={"width": W, "height": H})
        t1 = time.monotonic()
        pg2 = await ctx2.new_page()
        await pg2.goto((work / "book.html").as_uri(), wait_until="load")
        await pg2.wait_for_timeout(300)
        t_play = time.monotonic() - t1
        await pg2.evaluate("play()")
        await ctx2.close(); await b.close()
    v1 = next((work / "v1").glob("*.webm")); v2 = next((work / "v2").glob("*.webm"))
    a0 = max(t_tap - 0.4, 0); a_len = 0.4 + 1.5 + INTRO
    vf = "scale=1080:1920:flags=lanczos,fps=30,setsar=1"
    wm = "drawtext=text='@devetify':font='Cormorant Garamond':fontsize=46:fontcolor=white@0.55:shadowcolor=black@0.35:shadowx=2:shadowy=2:x=(w-text_w)/2:y=h-150"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-ss", f"{a0:.2f}", "-t", f"{a_len:.2f}", "-i", str(v1),
                    "-ss", f"{t_play:.2f}", "-t", f"{len(shots)*HOLD + (len(shots)-1)*FLIP - 0.3:.2f}", "-i", str(v2),
                    "-filter_complex", f"[0:v]{vf}[a];[1:v]{vf}[b];[a][b]concat=n=2:v=1[c];[c]{wm}[v]",
                    "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(work, ignore_errors=True)
    print(f"pages={len(shots)}")

if __name__ == "__main__":
    asyncio.run(main())
