# BotFucker Animated Explainer — HyperFrames Brief

## Objective
Create a punchy animated explainer video for BotFucker using the FF2K/comic/security UI design language already in the repo.

Target first cut:
- Duration: 25–35 seconds
- Format: 1920x1080 landscape
- Output: `dist/botfucker-animated-explainer.mp4` or the default HyperFrames render output
- Style: high-energy comic-book cybersecurity cockpit, not generic SaaS oatmeal
- Audience: people drowning in cold outreach, AI sales spam, and robotic CRM follow-ups

## Product message
BotFucker is a local-first inbox defense cockpit. It filters unsolicited sales outreach and generic AI-generated pitches while keeping provider credentials and live mailbox actions out of the core app.

Core claims to show:
1. Cold outreach floods the inbox.
2. BotFucker classifies suspicious mail locally.
3. The human reviews the queue in the Battle Board.
4. Nothing sends, moves, deletes, or touches providers without explicit future bridge approval.
5. Result: less inbox sludge, more control.

## Safety boundaries — do not violate these
- Do **not** imply BotFucker currently auto-sends replies.
- Do **not** imply it deletes, archives, moves, or modifies live mail today.
- Do **not** include OAuth/provider credentials.
- Do **not** add external tracking scripts or non-deterministic network fetches.
- Keep all assets local inside this HyperFrames project.

## Visual design tokens
Use the same branding as `../../web/styles.css`:
- Ink / outline: `#101820`
- Bitcoin orange: `#f7931a`
- Orange light: `#ffb23a`
- Orange dark: `#a94700`
- Security blue: `#1da9ff`
- Security blue dark: `#0b2f4f`
- Paper: `#f8f4ec`
- White cards: `#ffffff`

Visual language:
- thick black comic outlines
- offset shadows
- halftone/radial bursts
- orange/blue alert badges
- UI cards that feel like the local Battle Board
- use `assets/botfucker-ff2k-hero.png` prominently

## Suggested storyboard

### 0–4s — Hook
Text: `YOUR INBOX IS UNDER ATTACK`
Visual: envelopes and bot pitch cards fly in; orange warning burst.

### 4–9s — Problem
Text: `quick call? following up? scale your business?`
Visual: repeated spam cards pile up, stamp labels like `AI SLOP`, `CRM LOOP`, `COLD PITCH`.

### 9–15s — Mascot / product reveal
Text: `BOTFUCKER`
Subtext: `Local-first inbox defense`
Visual: FF2K hero art slides/punches into frame, crushing a spam-bot card.

### 15–22s — How it works
Text beats:
- `Classify locally`
- `Review in the Battle Board`
- `Keep provider keys outside the cockpit`
Visual: 3 comic panels/cards animate in sequence.

### 22–29s — Safety rails
Text: `No live sends. No deletes. No OAuth in core.`
Visual: locked toggle / shield / red disabled provider bridge.

### 29–35s — CTA / ending
Text: `FILTER THE BOT NOISE.`
Subtext: `Review first. Automate later.`
Visual: hero art + branded dashboard frame + final orange/blue punch.

## Implementation notes for Codex + HyperFrames
- Use `/hyperframes` and `/gsap` skills.
- Keep one main `index.html` unless sub-compositions make it cleaner.
- Register `window.__timelines["main"]`.
- Every visible timed element needs `class="clip"`, `data-start`, `data-duration`, and `data-track-index`.
- Prefer CSS/GSAP transforms over heavy video assets.
- Run `npm run check` after changes.
- Render with `npm run render` when check passes.

## Codex Desktop prompt

Copy/paste this into Codex Desktop while opened in this project folder:

```text
Using /hyperframes and /gsap, build the first cut of the BotFucker animated explainer described in VIDEO_BRIEF.md.

Read VIDEO_BRIEF.md, AGENTS.md, ../../web/styles.css, and ../../README.md first. Use local asset assets/botfucker-ff2k-hero.png. Create a 25–35 second 1920x1080 HyperFrames composition in index.html with comic-book FF2K styling: thick ink outlines, Bitcoin orange/security blue accents, halftone bursts, animated spam cards, and a clear safety-rails section.

Do not imply live provider actions exist today. Do not add external data fetches or tracking scripts. Keep all media local/deterministic. After editing, run npm run check and then npm run render. Fix issues until the checks pass. Report the output mp4 path.
```
