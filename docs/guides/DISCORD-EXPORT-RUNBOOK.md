# Discord Scrollback Export Runbook

Pull recent scrollback from the **"Honda Torque Mod Testing"** group DM (the EPS-firmware-hackers homie discord) using `tyrrrz/DiscordChatExporter`. This runbook is the prep-and-handoff doc — you do steps A–D, then hand the channel ID to Claude and the second agent runs the export.

---

## Pre-flight (already verified — no action needed)

- **DiscordChatExporter v2.47.1** already installed at `C:\claudecode\comma4epsflash\tools\dce\DiscordChatExporter.Cli.exe`
- **.NET 8 runtime present** (DCE requires .NET 8+; SDK not needed since DCE is a self-contained CLI)
- **Prior export found:** `C:\claudecode\comma4epsflash\discord-export\raw\dm-group.json` (last message timestamp **2026-05-21T00:06:56-04:00**) — this is the `--after` anchor for the next pull
- **Channel ID already known from prior export:** `1497734900713783438` (channel name: "Honda Torque Mod Testing", type: DirectGroupTextChat) — you can skip section **B** below unless you want to re-verify

The only thing the runbook actually needs you to do is **grab a fresh user token** (section **A**) and **drop it in `.discord.env`** (section **C**). Then tell Claude "token's in place, go" and the second agent will run the export with the anchor `--after 2026-05-21T00:06:56-04:00`.

---

## A. Grab your Discord user token (browser DevTools method)

Discord recently changed how it stores tokens — it's no longer sitting in plain Local Storage on modern builds. The reliable method is the **Network tab** approach.

1. Open **discord.com** in a browser (NOT the desktop app — the desktop app's DevTools are locked down). Log in.
2. Press **F12** to open DevTools.
3. Click the **Network** tab in DevTools.
4. In the filter box, type: `api`
5. In Discord itself, **click any channel or DM** (this triggers API calls so something shows up in Network).
6. In the Network tab, click any request with a URL like `https://discord.com/api/v9/...` (e.g. `messages`, `channels`, `science`).
7. In the right pane, switch to **Headers** (or "Request Headers").
8. Scroll to find the **`Authorization:`** header. The value of that header **is your token** — copy the entire value.
   - It will NOT have a `Bearer ` prefix (Discord user tokens are raw).
   - Format is three dot-separated base64 chunks: `XXXX.YYYY.ZZZZ`
   - Length is typically 70–90 characters.
9. **CRITICAL — security**:
   - This is a **USER token**. Anyone with this token can log into your Discord account, read every DM, post as you, etc.
   - **NEVER** commit it. **NEVER** paste it in a chat or anywhere logged.
   - Discord's TOS technically prohibits user-token automation — keep this private; risk is low for a one-shot read-only export but it's not zero.
   - If you ever leak it: change your Discord password, which invalidates all tokens.

---

## B. Grab the group DM channel ID  *(skip — already known)*

Channel ID is **`1497734900713783438`** — pulled from the prior `dm-group.json`. If you want to re-verify or the channel ID changed:

1. In Discord, enable Developer Mode: **User Settings → Advanced → Developer Mode = ON**
2. In the sidebar, right-click the group DM → **"Copy Channel ID"**

Or read it from the URL: when the DM is open in browser Discord, the URL is `https://discord.com/channels/@me/{CHANNEL_ID}` — copy the numeric ID after `@me/`.

---

## C. Put the token in `.discord.env`

1. Create the file at: `C:\claudecode\firmware-analysis-kit\.discord.env`
2. Contents — **one line, no quotes, no spaces around the `=`**:
   ```
   DISCORD_TOKEN=<paste_the_raw_token_here>
   ```
3. Sanity-check size:
   ```bash
   wc -c C:/claudecode/firmware-analysis-kit/.discord.env
   ```
   Should show roughly **85–105 bytes** (the `DISCORD_TOKEN=` prefix is 14 bytes, plus a newline, plus the 70–90 byte token).
4. `.discord.env` is already covered by the `.gitignore` `.env.*` rule — it will not be tracked. Confirmed during prep.

---

## D. Hand off to Claude

Once `.discord.env` is populated, tell Claude:

> "Token is in `.discord.env`. Channel ID is `1497734900713783438`. Run the export since 2026-05-21."

Claude will spawn the second agent which will:

1. Source the token from `.discord.env`
2. Run something equivalent to:
   ```
   C:\claudecode\comma4epsflash\tools\dce\DiscordChatExporter.Cli.exe export \
     -t "$DISCORD_TOKEN" \
     -c 1497734900713783438 \
     --after "2026-05-21T00:06:56-04:00" \
     -f Json \
     -o "C:\claudecode\firmware-analysis-kit\discord-export-incremental\dm-group-since-2026-05-21.json" \
     --media \
     --media-dir "C:\claudecode\firmware-analysis-kit\discord-export-incremental\media"
   ```
3. Report back with message count, date range covered, and output paths.

You do **not** need to run that command yourself — that's the second agent's job. You're only responsible for steps A and C above.

---

## Troubleshooting

- **"Cannot find token in Local Storage"** — expected. Use the Network tab method in section A.
- **DevTools won't open in Discord desktop app** — also expected. Use discord.com in a browser.
- **Token has 4 dots instead of 3** — you probably grabbed an `X-Super-Properties` or a cookie. Look for `Authorization:` specifically (case-sensitive in some views; check both).
- **Export errors with "Unauthorized"** — the token expired or was invalidated (happens if you logged out, changed password, or Discord rotated it). Re-grab from section A.
- **DCE complains about .NET version** — current .NET runtime is 8.0.27, DCE v2.47.1 supports it. If a newer DCE version is needed in the future, install via: `dotnet tool install --global DiscordChatExporter.Cli` (requires .NET SDK install first, which is NOT currently present — only the runtime is).
