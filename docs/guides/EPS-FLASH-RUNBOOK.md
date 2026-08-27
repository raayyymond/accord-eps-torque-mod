# EPS Flash Runbook — Red Panda + Laptop

> **This is the PRIMARY workflow.** `CLAUDE.md` also describes a Comma 4 SSH workflow (Option B), but the red panda + laptop approach is what we're using. The Comma 4 path is documented as a future alternative.

> **Topology correction (2026-05-28, per operator):** the red panda connects **through the comma Bosch harness** (installed in the car; the comma powers it), NOT directly into the OBD-II port. OBD-II-direct wording below has been corrected. See `memory/reference/tooling/reference_operator_flash_hardware_topology.md`.

## Status
- **Red panda**: Recovered from brick, running good firmware (VID:PID `3801:ddcc`)
- **eps-update.py**: Found and validated — from `hdlineage/sunnypilot_eps` repo (`release-c3-eps` branch)
- **Modified .rwd firmware**: Candidate files live under `../accord-firmware/flashing-2020accord/rwd/` by default
- **Desktop setup complete** (WSL Ubuntu, panda libs, firmware built) — but flash must happen from the **laptop** near the car
- **User's laptop may NOT have WSL installed yet**

The tracked Accord flasher source is `flashing-2020accord/eps-update-tva.py`.
Python build tools use `../accord-firmware` by default and honor
`ACCORD_FIRMWARE_ROOT` for another artifact root.

## What This Agent Needs To Do

Set up the laptop environment and execute the EPS flash via red panda over USB + OBD-II.

## Laptop Setup (if WSL not already configured)

### 1. Install WSL + Ubuntu
```powershell
# In admin PowerShell
wsl --install -d Ubuntu
# Reboot if prompted, then launch Ubuntu to finish setup
```

### 2. Install usbipd-win
```powershell
# In admin PowerShell
winget install usbipd
```

### 3. Install dependencies in WSL Ubuntu
```bash
sudo apt-get update
sudo apt-get install -y gcc-arm-none-eabi scons python3-pip libusb-1.0-0-dev
pip3 install --break-system-packages opendbc pycryptodome libusb1
```

### 4. Clone repos and build panda firmware
```bash
cd ~
# Clone openpilot (sparse — just panda + opendbc submodules)
git clone --depth 1 --filter=blob:none --sparse https://github.com/commaai/openpilot.git
cd openpilot
git sparse-checkout set panda/ third_party/
git submodule update --init --depth 1 panda
git submodule update --init --depth 1 opendbc_repo

# Install Python packages from submodules
pip3 install --break-system-packages -e opendbc_repo
pip3 install --break-system-packages -e panda

# Build panda firmware
cd panda && scons -j$(nproc) board/
cd ~

# Clone the eps-update.py repo
git clone --depth 1 -b release-c3-eps https://github.com/hdlineage/sunnypilot_eps.git
```

### 5. Verify setup

**Important**: `eps-update.py` must be run from within `~/sunnypilot_eps/` — it has its own bundled `panda/` fork that includes `panda/format/x5a.py` (Honda .rwd parser). The upstream `openpilot/panda` does NOT have this module. The upstream panda install (step 4) is only needed for the `Panda()` USB/SPI driver and firmware builds.

```bash
cd ~/sunnypilot_eps
python3 -c "from panda import Panda; print('panda OK')"
python3 -c "from panda.format.x5a import x5a; print('x5a parser OK')"
ls eps-update.py && echo "eps-update.py OK"
```

## Flash Procedure

### Prerequisites
- Car ignition ON (engine off is fine — CAN bus must be active)
- Red panda connected to the car **through the comma Bosch harness** (comma powers it), NOT directly into OBD-II
- openpilot/pandad killed on the comma (`tmux kill-server`) so its internal panda isn't contending on the bus
- Red panda connected to laptop via USB
- Laptop running WSL Ubuntu

### Step 1: Forward red panda USB to WSL

**Admin PowerShell:**
```powershell
usbipd list
# Find the red panda — should show as 3801:ddcc "panda"
usbipd bind --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

**WSL Ubuntu:**
```bash
sudo chmod 666 /dev/bus/usb/*/*
lsusb | grep -i panda  # Confirm it's visible
```

### Step 2: Copy .rwd firmware file into WSL
```bash
# From WSL, access Windows files via /mnt/c/
cp /mnt/c/path/to/accord-firmware/flashing-2020accord/rwd/firmware.rwd ~/sunnypilot_eps/
```

### Step 3: Dry run (SAFE — no writes, stops before flashing)
```bash
cd ~/sunnypilot_eps
python3 eps-update.py --bus 1 firmware.rwd
```

This will:
1. Connect to panda
2. Send tester present
3. Read current firmware ID (e.g., `39990-TGG-A120`)
4. Enter extended diagnostic session
5. Do security access (seed/key)
6. **STOP** — will NOT write anything without `--danger`

If this succeeds, the CAN connection is good and the EPS ECU is responding.

### Step 4: Flash for real (WRITES TO ECU — confirm with user first)

**NEVER run this without explicit user confirmation of the firmware file and parameters.**

```bash
python3 eps-update.py --bus 1 --danger firmware.rwd
```

This adds to the dry run:
1. Enter programming session
2. Erase flash memory
3. Set decryption key
4. Transfer firmware data (~311KB at ~9.34 kB/s — takes ~30 seconds)
5. Verify programming dependencies
6. Reset ECU

### Step 5: Verify flash
After flashing, the firmware ID should change. For modified firmware, the version string uses a comma instead of a dash:
- Stock: `39990-TGG-A120`
- Modified: `39990-TGG,A120`

Run the dry run again to read the new firmware ID and confirm the flash took.

## Script Details

### eps-update.py arguments
| Arg | Description |
|-----|-------------|
| `rwd` (positional) | Path to .rwd firmware file |
| `--bus N` | CAN bus number — use `1` for OBD-II |
| `--danger` | Required to actually write — without it, script aborts after security access |
| `--debug` | Enable debug output |
| `-o / --cipher-ops` | Cipher operations (default `+^-`) |
| `-c / --checksum-offsets` | Checksum block offsets (default `0xa000, 0x1d000, 0x4ff00`) |

### How it works internally
- Uses `SAFETY_ELM327` mode (whitelists all CAN TX, available on release firmware)
- UDS protocol over CAN bus 1 to EPS ECU at `0x18DA30F1`
- The `panda/format/x5a.py` module parses Honda .rwd files (header byte `b'Z'`)
- Security access key is calculated from constants embedded in the .rwd header + seed from ECU
- `--skip-checksum` flag from the jrdsgl article is NOT needed — checksum validation is already commented out in this version

### Dependencies NOT in vanilla openpilot
The script requires `panda/format/x5a.py` (Honda .rwd parser) which only exists in the `hdlineage/sunnypilot_eps` fork. You cannot just drop `eps-update.py` into a standard openpilot installation.

## Safety Rules
- **NEVER send the `--danger` flag without explicit user confirmation**
- Car ignition must be ON for CAN traffic to flow
- Do NOT interrupt the flash once started — partial write can brick the EPS ECU
- Run the dry run first EVERY time to verify connectivity
- The red panda flashes **through the comma Bosch harness**; kill openpilot/pandad on the comma first (`tmux kill-server`) so its internal panda isn't contending on the bus

## Troubleshooting

### Red panda not recognized by WSL
- Unplug/replug, re-run `usbipd list` (BUSID can change)
- Re-bind and re-attach with usbipd
- `sudo chmod 666 /dev/bus/usb/*/*` after each attach

### Red panda in DFU mode (bricked again)
- Shows as `0483:df11 "DFU in FS Mode"` in usbipd list
- Forward to WSL, then recover:
```bash
sudo chmod 666 /dev/bus/usb/*/*
cd ~/openpilot/panda
python3 -c 'from panda import PandaDFU; dfu = PandaDFU(None); dfu.recover(); print("Bootstub flashed")'
# Re-attach USB after reboot, then:
python3 -c 'from panda import Panda; p = Panda(); p.flash(); print("App firmware flashed"); p.close()'
```

### No CAN traffic / EPS not responding
- Verify ignition is ON (not just ACC)
- Check the comma Bosch harness + red panda connection is fully seated; confirm openpilot/pandad is killed on the comma (`tmux kill-server`)
- Try `--debug` flag for verbose output
- Confirm red panda shows `Bootstub: False` (app firmware running, not stuck in bootstub)

### autoecu.io doesn't recognize red panda
Known issue — autoecu filters for USB VID `0xbbaa`, but the red panda uses `0x3801`. Use eps-update.py instead.

## Reference
- [hdlineage/sunnypilot_eps](https://github.com/hdlineage/sunnypilot_eps) — eps-update.py source
- [How to modify your Civic's EPS firmware with a comma3x](https://jrdsgl.com/how-to-modify-your-civics-eps-firmware-with-a-comma3x/)
- [commaai/panda](https://github.com/commaai/panda) — panda firmware and Python library
- `flashing-2020accord/EPS_UPDATE_TVA_README.md` in this repo — the current Accord flashing workflow
