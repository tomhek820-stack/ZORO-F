import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features
from gtts import gTTS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
TMP = OUT / "tmp"
FONTS = ROOT / "assets" / "fonts"
W, H = 1080, 1920
BG, CYAN, WHITE, MUTED = (5, 7, 12), (0, 229, 255), (239, 246, 255), (142, 160, 180)
RAQM = features.check_feature("raqm")

if not RAQM:
    raise RuntimeError("Pillow RAQM is required for correct Arabic shaping and RTL layout")

def font(size, bold=False):
    names = (
        ["ReemKufi.ttf", "Amiri-Bold.ttf", "Cairo.ttf", "NotoNaskhArabic-Regular.ttf"]
        if bold else
        ["NotoNaskhArabic-Regular.ttf", "Amiri-Regular.ttf", "Gulzar-Regular.ttf", "Cairo.ttf"]
    )
    for name in names:
        path = FONTS / name
        if path.is_file():
            return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)
    raise FileNotFoundError("No bundled Arabic font found in assets/fonts")

def text_bbox(draw, text, fnt):
    return draw.textbbox((0, 0), text, font=fnt, direction="rtl", language="ar")

def centered(draw, text, y, fnt, fill, max_width=920):
    value = str(text)
    size = fnt.size
    box = text_bbox(draw, value, fnt)
    while (box[2] - box[0]) > max_width and size > 28:
        size -= 2
        fnt = font(size, size >= 50)
        box = text_bbox(draw, value, fnt)
    width = box[2] - box[0]
    draw.text(((W - width) / 2 - box[0], y), value, font=fnt, fill=fill,
              direction="rtl", language="ar", anchor=None)

def make_scene(scene, index, total):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((54, 70, 1026, 1850), radius=42, outline=(25, 61, 78), width=3)
    d.rounded_rectangle((88, 115, 992, 128), radius=6, fill=CYAN)
    d.ellipse((W//2-115, 390, W//2+115, 620), outline=(0, 110, 145), width=5)
    d.ellipse((W//2-82, 423, W//2+82, 587), outline=CYAN, width=3)
    centered(d, "أبو محمد المساوى", 190, font(42, True), CYAN)
    centered(d, scene["headline"], 790, font(76, True), WHITE)
    centered(d, scene["subheadline"], 930, font(45), MUTED)
    d.rounded_rectangle((160, 1480, 920, 1490), radius=5, fill=(28, 52, 68))
    d.rounded_rectangle((160, 1480, int(160 + 760 * (index + 1) / total), 1490), radius=5, fill=CYAN)
    centered(d, f"{index+1:02d} / {total:02d}", 1540, font(34), MUTED)
    centered(d, "تابع للمزيد من المحتوى التقني", 1680, font(34), WHITE)
    path = TMP / f"scene_{index:02d}.png"
    im.save(path, optimize=True)
    return path

def run(cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)

def voice(text, cfg, path):
    """Generate Arabic speech with the free Google Translate TTS endpoint via gTTS.

    gTTS does not expose a voice-gender selector; the Arabic voice is selected
    automatically by the service.
    """
    last_error = None
    for attempt in range(1, 4):
        try:
            # Remove any partial output left by an interrupted request.
            path.unlink(missing_ok=True)
            print(f"Generating Arabic narration with gTTS (attempt {attempt}/3)...", flush=True)
            gTTS(text=text, lang="ar", slow=False).save(str(path))
            if path.is_file() and path.stat().st_size > 4096:
                print(f"Arabic narration ready: {path.stat().st_size} bytes", flush=True)
                return
            raise RuntimeError("gTTS returned an empty or invalid audio file")
        except Exception as exc:
            last_error = exc
            print(f"gTTS attempt {attempt}/3 failed: {exc}", flush=True)
            if attempt < 3:
                import time
                time.sleep(3 * attempt)
    raise RuntimeError(
        "Arabic gTTS generation failed after 3 attempts. "
        "Check GitHub Actions network access and retry. "
        f"Last error: {last_error}"
    )

def stamp(sec):
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h:02}:{m:02}:{s:02},000"

def main():
    cfgpath = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "content/video_001.json"
    cfg = json.loads(cfgpath.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    scenes = cfg["scenes"]
    narration = " ".join(item["narration"] for item in scenes)
    audio = OUT / f"video_{cfg['episode']}_voice.mp3"
    voice(narration, cfg, audio)

    concat = TMP / "scenes.txt"
    lines = []
    for i, scene in enumerate(scenes):
        path = make_scene(scene, i, len(scenes))
        lines.extend([f"file '{path.as_posix()}'", f"duration {int(scene['duration'])}"])
    lines.append(f"file '{(TMP / f'scene_{len(scenes)-1:02d}.png').as_posix()}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")

    silent = TMP / "silent.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
         "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "23", str(silent)])
    video = OUT / f"ABU_MOHAMMED_{cfg['episode']}.mp4"
    run(["ffmpeg", "-y", "-i", str(silent), "-i", str(audio), "-map", "0:v:0",
         "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", str(video)])

    subtitles = []
    elapsed = 0
    for i, scene in enumerate(scenes, 1):
        end = elapsed + int(scene["duration"])
        subtitles += [str(i), f"{stamp(elapsed)} --> {stamp(end)}", scene["narration"], ""]
        elapsed = end
    (OUT / f"video_{cfg['episode']}.srt").write_text("\n".join(subtitles), encoding="utf-8")
    publish = {
        "title": cfg["title"], "channel": cfg["channel"],
        "description": cfg.get("description", ""),
        "hashtags": ["#" + item for item in cfg.get("hashtags", [])],
        "video": video.name
    }
    (OUT / f"publish_{cfg['episode']}.json").write_text(
        json.dumps(publish, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"VIDEO_READY={video}")
    print(f"VIDEO_SIZE={video.stat().st_size}")

if __name__ == "__main__":
    main()
