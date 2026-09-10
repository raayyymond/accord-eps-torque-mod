---
name: fetch-rlogs
description: Download the N latest drive routes' rlogs from comma connect (dongle 75604b0a432fdc89) into analysis-2020accord/rlogs/. Drives Chrome — opens connect.comma.ai, triggers the log upload on each route, waits for the device to finish uploading, downloads every segment's rlog.zst from the useradmin page, and moves them from Downloads into the repo rlogs folder. Use when the operator says "grab the latest route(s)", "download the last N drives", "pull the rlogs", or names a route that is not yet in analysis-2020accord/rlogs/.
model: sonnet
argument-hint: "[N] — how many of the latest routes to fetch (default 1)"
---

# Fetch the latest route rlogs from comma connect

**You are a subagent running on Sonnet.** Do exactly this task and report back; do not
propose firmware work, do not open Ghidra, do not read the golden model.

**`$ARGUMENTS` is `N`, the number of most-recent routes to fetch. If empty, `N = 1`.**

## Constants

| thing | value |
|---|---|
| dongle / device id | `75604b0a432fdc89` |
| connect URL | `https://connect.comma.ai/75604b0a432fdc89` |
| useradmin URL | `https://useradmin.comma.ai/?onebox=<ROUTE_ID>` (reached via **More info → View in useradmin**) |
| download landing dir | `C:\Users\dudei\Downloads` |
| destination | `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\rlogs\` |
| segment filename | `75604b0a432fdc89_000000XX--<hash>--<seg>--rlog.zst` |

A **route id** looks like `75604b0a432fdc89_000000a6` on connect and
`75604b0a432fdc89|000000a6--28ef595061` (or `...|2026-09-08--14-31-02`) in useradmin URLs.
Route counters are **hex** and monotonically increasing — `a7` is newer than `a6`.

## Step 0 — know what you already have (do this BEFORE opening a browser)

```bash
ls C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs \
  | sed 's/--.*//' | sort -u | tail -10
```

That is the list of route ids already downloaded. **Skip any route whose segments are already
present** — re-downloading a full route is ~15 min of upload time on the device for nothing.
If the N latest routes on connect are all already local, say so and stop; do not fetch older
ones to make up the count unless the operator asked for a specific route.

## Step 1 — open connect

Invoke the **`claude-in-chrome`** skill first (its own contract requires it), then:

1. `tabs_context_mcp` — see what tabs exist. **Do not reuse a tab id from another session.**
2. `tabs_create_mcp` a new tab at `https://connect.comma.ai/75604b0a432fdc89`.
3. `read_page` to get the route list. The newest route is at the **top** of the left-hand list.
   Each entry shows a date/time and duration. Screenshot with `computer` if the DOM read is
   ambiguous — this page is canvas/React-heavy and text extraction can be partial.

Record the route id and the date/time of each of the N newest routes before clicking anything.

## Step 2 — per route: trigger the upload

For each of the N routes, newest first:

1. Click the route in the list. The right pane loads that route's detail view.
2. Find the **"All logs"** row in the *Files* / *Upload* section. Next to it is a button that
   reads **"upload N logs"** (N is however many segments are not yet on the server) — click it.
   - If it instead reads **"all uploaded"** / shows no pending count, the logs are already on
     the server; skip straight to Step 3.
   - The button is a no-op if the device is offline. If connect shows the device as **offline**,
     **stop and tell the operator** — the car has to be awake and on wifi. Do not sit in a
     retry loop.
3. Note that this only *queues* the upload. The device uploads over wifi and it is slow:
   **budget ~30–60 s per segment**, so a 20-segment route can take 10–20 minutes.

## Step 3 — go to useradmin

On the route detail pane, open **More info → View in useradmin**. That opens
`useradmin.comma.ai` for this route, which is the only page that exposes direct
`rlog.zst` links per segment.

`read_page` there. You get a table with one row per segment, each row carrying links like
`qlog.bz2`, `rlog.zst`, `qcamera.ts`, `fcamera.hevc`. **Only `rlog.zst` matters.**

## Step 4 — wait for the uploads to land

Segments that have not finished uploading show **no `rlog.zst` link** (or a greyed/absent
cell) on useradmin.

Poll: reload the useradmin page and `read_page`, then count the rows that have an `rlog.zst`
link versus total rows.

- Wait **60 s between reloads**. Use a `Bash` sleep, not a tool-call spin.
- Report progress to the operator every few polls: `"14/22 segments uploaded"`.
- **Stall rule:** if the count does not increase across **5 consecutive polls (~5 min)**, stop
  polling and report how many landed. Do not keep waiting silently. Partial is fine — download
  what is there and say which segments are missing.
- Hard ceiling: **25 minutes per route.**

## Step 5 — download every segment's rlog.zst

Click each `rlog.zst` hyperlink in row order. Chrome downloads to `C:\Users\dudei\Downloads`
with the canonical filename, so no renaming is needed.

- Click them **one at a time** and give each ~1–2 s; firing 20 clicks in a burst makes Chrome
  drop some of them.
- **Never** click `fcamera.hevc` or `qcamera.ts` — those are hundreds of MB and useless here.
- If a click opens a viewer tab instead of downloading, close it and move on; note the segment.

## Step 6 — move them into the repo

```bash
DEST="C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs"
DL="C:/Users/dudei/Downloads"
mv "$DL"/75604b0a432fdc89_*--rlog.zst "$DEST"/ 2>/dev/null
ls -la "$DEST" | grep '<ROUTE_COUNTER>'   # e.g. 000000a7
```

Then verify, and **do not report success until this passes**:

1. **Every moved file is non-zero and plausibly sized** — a real segment rlog is **3–16 MB**.
   Anything under ~500 KB is a truncated download or an HTML error page; delete it and re-click
   that segment's link.
2. **Segment numbers are contiguous from 0**, with the last one usually short (partial segment).
   Name any gaps explicitly.
3. Nothing matching `*rlog.zst*` (`.crdownload`, `rlog (1).zst`) is left in `Downloads`.
   A `(1)` copy means the file already existed — the route was already local; delete the copy.

```bash
python - <<'EOF'
import os,re,collections
d=r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\rlogs"
ROUTE="000000a7"   # <-- set to the route counter you just fetched
segs={}
for f in os.listdir(d):
    m=re.match(r"75604b0a432fdc89_%s--([0-9a-f]+)--(\d+)--rlog\.zst$"%ROUTE,f)
    if m: segs[int(m.group(2))]=os.path.getsize(os.path.join(d,f))
if not segs: print("NO SEGMENTS FOUND for",ROUTE); raise SystemExit(1)
n=max(segs)
missing=[i for i in range(n+1) if i not in segs]
small=[i for i,s in sorted(segs.items()) if s<500_000 and i!=n]
print(f"{ROUTE}: {len(segs)} segments, 0..{n}")
print("  missing :", missing or "none")
print("  runt    :", small or "none")
print("  total MB: %.1f"%(sum(segs.values())/1e6))
EOF
```

## Step 7 — close out

Close the tabs you opened (`tabs_close_mcp`). Report, in this shape:

```
Fetched <N> route(s) into analysis-2020accord/rlogs/

  75604b0a432fdc89_000000a7  2026-09-09 14:31  22 segments (0..21)  268 MB   OK
  75604b0a432fdc89_000000a6  2026-09-08 09:02  18/20 segments       211 MB   segments 18,19 never uploaded

Already local, skipped: 000000a5
```

State plainly anything that did not work: a route whose device was offline, segments that
stalled, a link that opened a viewer. **Do not paper over a partial fetch** — a route with
holes in it silently corrupts every downstream rlog analysis, and the analysis scripts will
not tell you a segment is missing.

## Rabbit-hole rules

- Browser tool fails 2–3 times on the same action → **stop and ask the operator**. Do not
  keep retrying or wander the site.
- **Never click anything that could pop a JS dialog** (delete, "preserve" toggles, account
  settings). A modal freezes the extension.
- Do not change any setting on connect or useradmin. This skill is read-and-download only,
  plus the one "upload logs" button.
- If connect asks you to log in, **stop** — the operator has to authenticate. Tell them to run
  the login themselves.
