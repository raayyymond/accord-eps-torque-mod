# Red Panda EPS Flash Setup Guide

> **Topology correction (2026-05-28, per operator):** flashing goes **through the comma Bosch harness**, NOT red-panda-direct-to-OBD-II. The original OBD-II-direct wording was wrong for the operator's actual rig and has been corrected throughout. The exact harness connector path is the operator's known setup — see `memory/reference_operator_flash_hardware_topology.md`.

## Overview

Flash modified Honda EPS (Electric Power Steering) firmware using a **red panda** USB CAN adapter connected to a Windows laptop running **WSL Ubuntu**. The red panda connects to the car **through the comma Bosch harness** (installed in the car; the comma powers the harness) — it does **not** plug directly into the OBD-II port. This reaches the harness-tapped CAN buses; the EPS ECU responds on bus 1.

## Architecture

```
Laptop (Windows + WSL Ubuntu)
  │
  │ USB  (forwarded to WSL via usbipd-win)
  ▼
Red Panda  (STM32H725, VID:PID 3801:ddcc)
  │
  │ CAN via the comma Bosch harness (installed in car; comma powers it)
  ▼
EPS ECU  (CAN addr 0x18DA30F1, bus 1)
  │
  └── UDS flash protocol (eps-update.py)
```

## What You Need

### Hardware
- Red panda (comma.ai USB CAN adapter)
- Comma Bosch harness installed in the car — the red panda connects **through** it, and the comma powers the harness (operator's rig; see `memory/reference_operator_flash_hardware_topology.md`)
- USB cable (red panda → laptop)
- Car with ignition ON (engine off is fine)

### Software (on laptop)
- Windows 10/11 with WSL2 Ubuntu
- `usbipd-win` (forwards USB devices into WSL)
- Python 3.10+ in WSL
- Python packages: `pycryptodome`, `libusb1`, `tqdm`

### Files (on USB drive at `E:\comma4epsflash\`)
- `sunnypilot_eps/` — the flash script + bundled panda fork
  - `eps-update.py` — the flash script
  - `panda/` — fork with Honda .rwd parser (`format/x5a.py`) and UDS client (`python/uds.py`)
- `panda_firmware/` — prebuilt recovery binaries (if red panda bricks)
  - `bootstub.panda_h7.bin`
  - `panda_h7.bin.signed`
- `C120Civicsedan25xsteerto1.rwd` — modified 2.5x steering torque firmware
- `C120CivicsedanStock.rwd` — stock firmware (for reverting)

## Laptop Setup (One-Time)

### 1. Install WSL + Ubuntu (if not already installed)
```powershell
# Admin PowerShell
wsl --install -d Ubuntu
```

### 2. Install usbipd-win (if not already installed)
```powershell
# Admin PowerShell
winget install usbipd
```

### 3. Install Python dependencies in WSL
```bash
sudo apt-get update
sudo apt-get install -y python3-pip libusb-1.0-0-dev
pip3 install --break-system-packages pycryptodome libusb1 tqdm
```

### 4. Copy files from USB into WSL
```bash
cp -r /mnt/e/comma4epsflash/sunnypilot_eps ~/sunnypilot_eps
cp /mnt/e/comma4epsflash/*.rwd ~/sunnypilot_eps/
```

## Flash Procedure

### Step 1: Connect hardware
1. Connect the red panda **through the comma Bosch harness** (installed in car; comma powers it) — NOT directly into the OBD-II port
2. Connect red panda to laptop via USB
3. Turn car ignition ON (engine off is fine)
4. Kill openpilot/pandad on the comma first (`tmux kill-server`) so its internal panda isn't contending on the bus during the flash (iron safety rule)

### Step 2: Forward USB to WSL

**Admin PowerShell:**
```powershell
usbipd list
# Find red panda — shows as "panda" with VID:PID 3801:ddcc
usbipd bind --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

**WSL Ubuntu:**
```bash
sudo chmod 666 /dev/bus/usb/*/*
lsusb | grep panda   # confirm it's visible
```

### Step 3: Dry run (safe — reads only, no writes)
```bash
cd ~/sunnypilot_eps
python3 eps-update.py --bus 1 ../C120Civicsedan25xsteerto1.rwd
```

This connects to the EPS ECU, reads the current firmware ID, does security access, then **stops**. If it succeeds, CAN connectivity is confirmed and the ECU is responding.

### Step 4: Flash (writes to ECU)
```bash
python3 eps-update.py --bus 1 --danger ../C120Civicsedan25xsteerto1.rwd
```

The `--danger` flag enables actual writing. The script will:
1. Erase flash memory
2. Transfer firmware (~311KB, ~30 seconds)
3. Verify and reset ECU

**Do NOT interrupt this step once started.**

### Step 5: Verify
Run the dry run again — the firmware ID should now show a comma instead of a dash:
- Before: `39990-TGG-A120` (stock)
- After: `39990-TGG,A120` (modified)

## Reverting to Stock

Same process, just use the stock firmware file:
```bash
python3 eps-update.py --bus 1 --danger ../C120CivicsedanStock.rwd
```

## Troubleshooting

### Red panda not showing in `usbipd list`
- Unplug and replug USB
- Try a different USB port (avoid hubs)

### Red panda visible but WSL can't see it
- Re-run `usbipd attach --wsl --busid <BUSID>` (BUSID can change after replug)
- Run `sudo chmod 666 /dev/bus/usb/*/*` after each attach

### Dry run fails / no response from ECU
- Verify ignition is ON (not just ACC)
- Check OBD-II cable is fully seated
- Add `--debug` flag for verbose output
- Ensure the comma Bosch harness is fully seated and the red panda is properly connected through it; kill openpilot/pandad on the comma (`tmux kill-server`) so its internal panda isn't contending on the bus

### Red panda bricked (shows as `0483:df11 "DFU in FS Mode"`)
Recovery binaries are on the USB drive at `panda_firmware/`. Full recovery steps:

1. Forward DFU device to WSL via usbipd (same bind/attach flow)
2. Fix permissions: `sudo chmod 666 /dev/bus/usb/*/*`
3. Flash bootstub:
```bash
# Needs the openpilot panda library installed — see EPS-FLASH-RUNBOOK.md for full setup
python3 -c 'from panda import PandaDFU; dfu = PandaDFU(None); dfu.recover(); print("Bootstub OK")'
```
4. Unplug/replug, re-attach to WSL, then flash app firmware:
```bash
python3 -c 'from panda import Panda; p = Panda(); p.flash(); print("Firmware OK"); p.close()'
```

### autoecu.io doesn't recognize the red panda
Known issue — use eps-update.py instead. autoecu.io has a VID filter mismatch with the red panda.

## Key Technical Details

| Detail | Value |
|--------|-------|
| EPS ECU CAN address | `0x18DA30F1` |
| CAN bus | 1 (`--bus 1`) |
| Panda safety mode | `SAFETY_ELM327` (set by script) |
| Firmware format | Honda `.rwd` (header byte `0x5A`) |
| Flash size | ~311KB at ~9.34 kB/s |
| Modified FW marker | Comma in version string (`,` vs `-`) |
| Script source | `hdlineage/sunnypilot_eps` (`release-c3-eps` branch) |
| Script dependency | `panda/format/x5a.py` (only in that fork) |
