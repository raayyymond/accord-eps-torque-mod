# Flashing the 2020 Accord EPS (39990-TVA-A160) from a comma 4 — Onboarding

The flash runs **on the comma 4 / comma 3X itself**, through its internal panda and the
stock Honda harness. No red panda, no laptop on the OBD port, no WSL, no custom panda
fork. The script uses the standard `panda` + `opendbc` libraries that are already inside
`/data/openpilot` on the device.

Six steps: SSH key → connect → copy files → stop openpilot → dry run → flash.

## 1. Create a GitHub SSH key (once)
Follow GitHub's guide: [Generating a new SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)

## 2. Add the key to your GitHub account (once)
GitHub → **Settings** → **SSH and GPG keys** → **New SSH key** → paste your public key
(`id_ed25519.pub`) → **Add SSH key**. Then on the comma device enable SSH
(Settings → Network → Enable SSH) and enter your GitHub username; it fetches the key.

## 3. SSH into the comma device
Any SSH client works (MobaXterm, Windows Terminal, macOS Terminal):
```bash
ssh -i ~/.ssh/id_ed25519 comma@<device-ip>
```
- Host: the device's IP (Settings → Network on the device, or your router's client list)
- User: `comma`
- Key: your private key file

## 4. Copy the script and the `.rwd` onto the device
With scp (or MobaXterm's SFTP panel), put both files in the same folder:
```bash
ssh comma@<device-ip> 'mkdir -p /data/eps-flash'
scp eps-update-tva.py <firmware>.rwd comma@<device-ip>:/data/eps-flash/
```

## 5. Stop openpilot — REQUIRED
openpilot's `pandad` owns the panda. The script refuses to run while it is up.
In the SSH terminal:
```bash
tmux kill-server
sleep 3
```
The device screen goes dark; that is expected. **Reboot the device when you are
finished** (step 7) to bring openpilot back.

Also: **turn the car's ignition on** (engine off is fine). The EPS does not answer
diagnostics with the car off.

## 6. Dry run, then flash
```bash
cd /data/eps-flash

# Optional: proves the inlined security-access maths, needs nothing else
python3 eps-update-tva.py --selftest

# DRY RUN (safe, the default). Talks to the real EPS: reads its part number,
# does the security-access handshake, then STOPS before any erase/write.
python3 eps-update-tva.py --bus 1 <firmware>.rwd

# REAL FLASH. Requires --danger and typing FLASH at the prompt.
python3 eps-update-tva.py --bus 1 --danger <firmware>.rwd
```
`python3` is fine: the script re-launches itself under the device's own Python
environment (`/usr/local/venv`) and finds `panda`/`opendbc` in `/data/openpilot` by itself.

**Always dry-run first.** A good dry run ends with
`DRY RUN COMPLETE - SA handshake succeeded` and shows
`ECU app ID : b'39990-TVA-A160...'` (or `TVA,A160`) matching the `.rwd`'s supported
parts. Double-check the `.rwd` filename and version before adding `--danger`.

### During the flash (about 3–5 minutes)
- Stay in the car. Do not touch the ignition, the harness, the device, or the SSH session.
- Do not interrupt the script. A partial write can leave the EPS unbootable.
- It ends with `[flash] DONE`. Then turn the ignition off for 10 s and back on.

## 7. Bring openpilot back
```bash
sudo reboot
```

## If something refuses to run
| Message | Meaning / fix |
|---|---|
| `openpilot/pandad is running and owns the panda` | Do step 5 (`tmux kill-server`), wait 3 s, retry. |
| `panda reports ignition OFF` | Turn the ignition on, retry. |
| `could not open the panda` | openpilot still shutting down (wait and retry), or the device is not a comma 3X/4. |
| `ECU app id ... does not match any supported part` | Wrong `.rwd` for this car. Stop. |
| `0x7F 0x27 0x36` during the handshake | The ECU rate-limits security access. Ignition off 10 s, on, retry. |
| `MOCK FLOW CHECK COMPLETE` | You passed `--mock`. Nothing was tested on the car. |

## Notes
- `--bus 1` is the bus the Accord EPS sits on from the comma harness (the same bus
  openpilot fingerprints it on). It is also bus 1 on a red panda on OBD-II, if you
  ever use one instead.
- Back on a laptop with a red panda, the script works the same provided an openpilot
  checkout (for `panda` and `opendbc`) is on `PYTHONPATH`; set `OPENPILOT_ROOT` to it.
- `--mock` runs the flow with canned answers and no hardware. It is only for checking
  that the script itself runs; it proves nothing about the car.
