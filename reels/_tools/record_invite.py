import sys, asyncio, pathlib, shutil, subprocess, time
from playwright.async_api import async_playwright

# usage: record_invite.py <index.html> <out.mp4> [n_sections]
# "Invitation feel" clip: the real invitation as a guest sees it on the phone —
# tap-to-open intro, then smooth real scrolling that stops on the hero and the most
# striking whole sections. 10-15 s, 1080x1920, dates/venues/countdowns blurred, @devetify mark.
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from blur import BLUR_JS
from record_book import pick   # same "most striking sections" choice as the book style

src = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(sys.argv[2]).resolve()
n_keep = int(sys.argv[3]) if len(sys.argv) > 3 else 3
W, H = 540, 960
INTRO = 3.0          # seconds after the tap for the opening animation
HOLD = 1.8           # pause on each section
SCROLL_MS = 900      # smooth scroll duration between sections

FIND_SECTIONS = """() => {
  const vis = e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return r.height > 160 && r.width > 200 && cs.display !== 'none' && cs.visibility !== 'hidden' && cs.position !== 'fixed'; };
  const rsvp = e => /rsvp|count|timer|anket|cavab/i.test((e.className||'') + ' ' + (e.id||'')) || e.querySelector('form,input,textarea,select');
  let secs = [...document.querySelectorAll('section')].filter(vis);
  secs = secs.filter(e => !secs.some(o => o !== e && o.contains(e)));
  const nonR = secs.filter(e => !rsvp(e)); if (nonR.length >= 2) secs = nonR;
  secs.forEach((e, i) => e.dataset.dvSec = i);
  return secs.length; }"""

# smooth-scroll the element's top (or centre, if it fits) into view over `ms`
SCROLL_TO = """async ([i, ms, vh]) => {
  const el = document.querySelector('[data-dv-sec="' + i + '"]'); if (!el) return;
  const scroller = (() => { let p = el.parentElement;
    while (p && p !== document.body) { const s = getComputedStyle(p).overflowY;
      if ((s === 'auto' || s === 'scroll') && p.scrollHeight > p.clientHeight) return p; p = p.parentElement; }
    return document.scrollingElement || document.documentElement; })();
  const r = el.getBoundingClientRect();
  const base = scroller === (document.scrollingElement || document.documentElement) ? 0 : scroller.getBoundingClientRect().top;
  let delta = r.top - base;
  if (r.height < vh) delta -= (vh - r.height) / 2;
  const start = scroller.scrollTop, t0 = performance.now();
  await new Promise(res => { const step = now => { const k = Math.min(1, (now - t0) / ms);
      const e = k < .5 ? 2*k*k : 1 - Math.pow(-2*k + 2, 2) / 2;
      scroller.scrollTop = start + delta * e; k < 1 ? requestAnimationFrame(step) : res(); };
    requestAnimationFrame(step); });
}"""

async def open_page(b, rec_dir=None):
    kw = dict(viewport={"width": W, "height": H}, is_mobile=True, has_touch=True)
    if rec_dir: kw.update(record_video_dir=str(rec_dir), record_video_size={"width": W, "height": H})
    ctx = await b.new_context(**kw)
    await ctx.add_init_script(BLUR_JS)
    return ctx

async def tap_open(pg):
    await pg.mouse.click(W / 2, H / 2)
    await pg.wait_for_timeout(1500)
    await pg.mouse.click(W / 2, H / 2)
    await pg.wait_for_timeout(int(INTRO * 1000))

async def main():
    work = out.parent / ("_inv_" + out.stem)
    shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        # pass 1: find and rank sections
        ctx = await open_page(b)
        pg = await ctx.new_page()
        await pg.goto(src.as_uri(), wait_until="load"); await pg.wait_for_timeout(1200)
        await tap_open(pg)
        n = await pg.evaluate(FIND_SECTIONS)
        chosen = []
        if n >= 2:
            shots = []
            for i in range(min(n, 8)):
                loc = pg.locator(f'[data-dv-sec="{i}"]')
                await loc.evaluate("e => e.scrollIntoView({block:'start'})"); await pg.wait_for_timeout(700)
                f = work / f"s{i}.png"
                try: await loc.screenshot(path=str(f), timeout=8000); shots.append(f)
                except Exception: pass
            keep = pick(shots, n_keep)
            chosen = [int(f.stem[1:]) for f in keep]
        await ctx.close()
        # pass 2: record the real experience
        ctx = await open_page(b, work / "v")
        t0 = time.monotonic()
        pg = await ctx.new_page()
        await pg.goto(src.as_uri(), wait_until="load"); await pg.wait_for_timeout(1500)
        t_tap = time.monotonic() - t0
        await tap_open(pg)
        await pg.evaluate(FIND_SECTIONS)
        if chosen:
            for k, i in enumerate(chosen):
                if k == 0 and i == 0:            # hero is already on screen after the intro
                    await pg.wait_for_timeout(int(HOLD * 1000)); continue
                await pg.evaluate(SCROLL_TO, [i, SCROLL_MS, H])
                await pg.wait_for_timeout(int(HOLD * 1000))
        else:                                    # no <section> markup: gentle scroll
            for _ in range(int(HOLD * 3 * 4)):
                await pg.mouse.wheel(0, 40); await pg.wait_for_timeout(250)
        t_end = time.monotonic() - t0
        await ctx.close(); await b.close()
    webm = next((work / "v").glob("*.webm"))
    a0 = max(t_tap - 0.4, 0); dur = min(t_end - a0, 15.0)
    wm = "drawtext=text='@devetify':font='Cormorant Garamond':fontsize=46:fontcolor=white@0.55:shadowcolor=black@0.35:shadowx=2:shadowy=2:x=(w-text_w)/2:y=h-150"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a0:.2f}", "-t", f"{dur:.2f}", "-i", str(webm),
                    "-vf", f"scale=1080:1920:flags=lanczos,fps=30,setsar=1,{wm}", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(work, ignore_errors=True)
    print(f"sections={chosen}")

asyncio.run(main())
