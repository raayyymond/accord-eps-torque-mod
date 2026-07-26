"""Paths for proprietary firmware artifacts kept outside the repository."""

from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIRMWARE_ROOT = REPO_ROOT.parent / "accord-firmware"
FIRMWARE_ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", DEFAULT_FIRMWARE_ROOT)).expanduser().resolve()
ARTIFACT_ROOT = FIRMWARE_ROOT
FIRMWARE_ARTIFACT_ROOT = FIRMWARE_ROOT

ANALYSIS_ROOT = FIRMWARE_ROOT / "analysis-2020accord"
STOCK_FW_DUMP = ANALYSIS_ROOT / "stock_fw_dump"
GHIDRA_PROJECT = ANALYSIS_ROOT / "ghidra_project"
OTHER_BINS = ANALYSIS_ROOT / "other bins"

FLASHING_ROOT = FIRMWARE_ROOT / "flashing-2020accord"
RWD_DIR = FLASHING_ROOT / "rwd"
ARCHIVE_DIR = FLASHING_ROOT / "archive"

IHDS_RWDS = FIRMWARE_ROOT / "iHDS_rwds"
CALIB_FILES = IHDS_RWDS / "CalibFiles"

# Explicit aliases make the layout readable at call sites while keeping the
# shorter names convenient for the small standalone analysis scripts.
ANALYSIS_DIR = ANALYSIS_ROOT
FLASHING_DIR = FLASHING_ROOT
STOCK_FW_DUMP_DIR = STOCK_FW_DUMP
GHIDRA_PROJECT_DIR = GHIDRA_PROJECT
OTHER_BINS_DIR = OTHER_BINS
IHDS_RWDS_DIR = IHDS_RWDS
CALIB_FILES_DIR = CALIB_FILES


def artifact_path(*parts: str) -> Path:
    """Return a path relative to the configured firmware artifact root."""
    return FIRMWARE_ROOT.joinpath(*parts)


def stock_fw_path(name: str = "code.bin") -> Path:
    return STOCK_FW_DUMP / name


def ghidra_path(*parts: str) -> Path:
    return GHIDRA_PROJECT.joinpath(*parts)


def other_bin_path(name: str) -> Path:
    return OTHER_BINS / name


def plain_image_path(name: str) -> Path:
    return ANALYSIS_ROOT / name


def rwd_path(name: str) -> Path:
    return RWD_DIR / name


def archive_path(name: str) -> Path:
    return ARCHIVE_DIR / name


def calib_file_path(name: str) -> Path:
    return CALIB_FILES / name
