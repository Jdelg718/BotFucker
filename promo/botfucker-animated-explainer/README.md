# BotFucker Animated Explainer

HyperFrames source and rendered first cut for a branded BotFucker product explainer using the FF2K/comic inbox-defense design system.

## Files

- `index.html` — main 1920x1080 HyperFrames composition.
- `VIDEO_BRIEF.md` — storyboard, product claims, safety boundaries, and Codex prompt.
- `assets/botfucker-ff2k-hero.png` — local FF2K hero art.
- `assets/gsap.min.js` — local GSAP runtime for deterministic/offline rendering.
- `narration-v2.txt` — approved narration script for the first narrated cut.
- `assets/narration-v2.ogg` — generated narration audio.
- `renders/botfucker-animated-explainer_narrated-final.mp4` — current rendered deliverable.

## Run / preview

```bash
npm run dev
```

Open the preview URL printed by HyperFrames.

## Validate

```bash
npm run check
```

Expected: lint, validation, and layout inspection pass. Brand-color contrast notes are acceptable if they do not fail layout/rendering.

## Render

```bash
npm run render
```

To rebuild the narrated deliverable after rendering a fresh silent MP4, mux the narration with FFmpeg:

```bash
ffmpeg -y \
  -i renders/<silent-render>.mp4 \
  -i assets/narration-v2.ogg \
  -filter_complex "[1:a]asetpts=PTS-STARTPTS,atempo=1.065,adelay=250:all=1,apad=pad_dur=2,volume=1.12[a]" \
  -map 0:v:0 -map "[a]" \
  -c:v copy -c:a aac -b:a 160k -t 35 -movflags +faststart \
  renders/botfucker-animated-explainer_narrated-final.mp4
```

## Safety copy constraints

Do not imply live provider automation exists today. The explainer must preserve the current product truth:

- no live sends
- no deletes
- no OAuth in the BotFucker core
- human review first
- provider bridge later
