# ZORO-F — Abu Mohammed Al-Masawi Video Factory

Cloud video production for the Arabic technology channel **أبو محمد المساوى**.

## What it does
- Creates Arabic narration with Edge TTS.
- Renders vertical 1080×1920 scenes with Arabic text.
- Combines scenes and narration into an MP4 using FFmpeg.
- Uploads the finished video, narration, subtitles and publish metadata as a GitHub Actions artifact.

## Run
Open **Actions** → **Produce Arabic Video** → **Run workflow**. Download the `zoro-video-output` artifact when complete.

The workflow also runs on pushes to `main` that change content or scripts. Edit `content/video_001.json` to change the episode.

The first version uses generated graphic scenes and an Arabic neural voice. It requires no API keys or repository secrets.
