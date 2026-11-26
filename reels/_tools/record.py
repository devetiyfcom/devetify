import sys, asyncio, pathlib, shutil, subprocess, time
from playwright.async_api import async_playwright

# usage: record.py <index.html> <out.mp4> [seconds]
# Records a 1080x1920 vertical clip of an invitation site: taps open the intro, scrolls slowly,
# and blurs any dates, times and venue/address text so they cannot be read.
src = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(sys.argv[2]).resolve()
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 18
W, H = 540, 960

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from blur import BLUR_JS

async def main():
    tmp = out.parent / ("_vid_" + out.stem)
    shutil.rmtree(tmp, ignore_errors=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, device_scale_factor=1,
                                  is_mobile=True, has_touch=True,
                                  record_video_dir=str(tmp), record_video_size={"width": W, "height": H})
        await ctx.add_init_script(BLUR_JS)
        t0 = time.monotonic()
        pg = await ctx.new_page()
        await pg.goto(src.as_uri(), wait_until="load")
        await pg.wait_for_timeout(1500)
        t_tap = time.monotonic() - t0
        await pg.mouse.click(W / 2, H / 2)
        await pg.wait_for_timeout(1500)
        await pg.mouse.click(W / 2, H / 2)
        await pg.wait_for_timeout(3500)
        steps = int((secs - 5) * 4)
        for _ in range(max(steps, 1)):
            await pg.mouse.wheel(0, 45)
            await pg.wait_for_timeout(250)
        await ctx.close(); await b.close()
    webm = next(tmp.glob("*.webm"))
    start = max(t_tap - 0.4, 0)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", str(webm), "-t", str(secs),
                    "-vf", "scale=1080:1920:flags=lanczos,fps=30", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)

asyncio.run(main())
