import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

ROOT = Path(__file__).resolve().parents[1]
OUT, TMP = ROOT / "output", ROOT / "output" / "tmp"
W, H = 1080, 1920
BG, CYAN, WHITE, MUTED = (5,7,12), (0,229,255), (239,246,255), (142,160,180)

def shape(s): return get_display(arabic_reshaper.reshape(str(s)))
def font(size, bold=False):
    paths = ["/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in paths:
        if Path(p).exists(): return ImageFont.truetype(p, size)
    return ImageFont.load_default()
def centered(draw, text, y, fnt, fill, max_width=920):
    txt, size = shape(text), fnt.size
    while draw.textbbox((0,0), txt, font=fnt)[2] > max_width and size > 28:
        size -= 2; fnt = font(size, size >= 50)
    box = draw.textbbox((0,0), txt, font=fnt)
    draw.text(((W-(box[2]-box[0]))/2,y), txt, font=fnt, fill=fill)
def make_scene(scene, index, total):
    im = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(im)
    d.rounded_rectangle((54,70,1026,1850),radius=42,outline=(25,61,78),width=3)
    d.rounded_rectangle((88,115,992,128),radius=6,fill=CYAN)
    d.ellipse((W//2-115,390,W//2+115,620),outline=(0,110,145),width=5)
    d.ellipse((W//2-82,423,W//2+82,587),outline=CYAN,width=3)
    centered(d,"أبو محمد المساوى",190,font(42,True),CYAN)
    centered(d,scene["headline"],790,font(76,True),WHITE)
    centered(d,scene["subheadline"],930,font(45),MUTED)
    d.rounded_rectangle((160,1480,920,1490),radius=5,fill=(28,52,68))
    d.rounded_rectangle((160,1480,int(160+760*(index+1)/total),1490),radius=5,fill=CYAN)
    centered(d,f"{index+1:02d} / {total:02d}",1540,font(34),MUTED)
    centered(d,"تابع للمزيد من المحتوى التقني",1680,font(34),WHITE)
    p=TMP/f"scene_{index:02d}.png"; im.save(p,optimize=True); return p
def voice(text, cfg, path):
    wav = path.with_suffix(".wav")
    speed = int(cfg.get("speech_rate", 145))
    run(["espeak-ng", "-v", "ar", "-s", str(speed), "-w", str(wav), text])
    run(["ffmpeg", "-y", "-i", str(wav), "-codec:a", "libmp3lame", "-q:a", "3", str(path)])
    if not path.exists() or path.stat().st_size < 1024:
        raise RuntimeError("Arabic speech engine did not create a valid audio file")
def run(cmd):
    print("+"," ".join(map(str,cmd)),flush=True); subprocess.run(cmd,check=True)
def stamp(sec):
    h,r=divmod(sec,3600); m,s=divmod(r,60); return f"{h:02}:{m:02}:{s:02},000"
def main():
    cfgpath=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/"content/video_001.json"
    cfg=json.loads(cfgpath.read_text(encoding="utf-8")); OUT.mkdir(exist_ok=True); TMP.mkdir(parents=True,exist_ok=True)
    scenes=cfg["scenes"]; narration=" ".join(x["narration"] for x in scenes)
    audio=OUT/f"video_{cfg['episode']}_voice.mp3"; voice(narration,cfg,audio)
    concat=TMP/"scenes.txt"; lines=[]
    for i,s in enumerate(scenes):
        p=make_scene(s,i,len(scenes)); lines.extend([f"file '{p.as_posix()}'",f"duration {int(s['duration'])}"])
    lines.append(f"file '{(TMP/f'scene_{len(scenes)-1:02d}.png').as_posix()}'")
    concat.write_text("\n".join(lines)+"\n",encoding="utf-8")
    silent=TMP/"silent.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-vf","fps=30,format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","23",str(silent)])
    video=OUT/f"ABU_MOHAMMED_{cfg['episode']}.mp4"
    run(["ffmpeg","-y","-i",str(silent),"-i",str(audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(video)])
    subs=[]; t=0
    for i,s in enumerate(scenes,1):
        end=t+int(s["duration"]); subs += [str(i),f"{stamp(t)} --> {stamp(end)}",s["narration"],""]; t=end
    (OUT/f"video_{cfg['episode']}.srt").write_text("\n".join(subs),encoding="utf-8")
    pub={"title":cfg["title"],"channel":cfg["channel"],"description":cfg.get("description",""),"hashtags":["#"+x for x in cfg.get("hashtags",[])],"video":video.name}
    (OUT/f"publish_{cfg['episode']}.json").write_text(json.dumps(pub,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"VIDEO_READY={video}"); print(f"VIDEO_SIZE={video.stat().st_size}")
if __name__=="__main__": main()
