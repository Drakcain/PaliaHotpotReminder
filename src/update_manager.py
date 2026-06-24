from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from app_version import APP_VERSION_NUMBER

LATEST_RELEASE_API = "https://api.github.com/repos/Drakcain/PaliaHotpotReminder/releases/latest"
INSTALLER_PREFIX = "PaliaHotpotReminder-Setup-v"


def _parse_version(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lstrip("vV")
    parts = []
    for segment in cleaned.split("."):
        digits = "".join(ch for ch in segment if ch.isdigit())
        parts.append(int(digits or "0"))
    return tuple(parts)


def get_latest_release() -> Dict[str, Any]:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "PaliaHotpotReminder-Updater",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_update_offer(current_version: str = APP_VERSION_NUMBER) -> Optional[Dict[str, Any]]:
    release = get_latest_release()
    latest_tag = str(release.get("tag_name") or "").strip()
    latest_version = latest_tag.lstrip("vV")
    if not latest_version:
        raise RuntimeError("Latest GitHub release did not include a tag name.")

    if _parse_version(latest_version) <= _parse_version(current_version):
        return None

    assets = release.get("assets") or []
    installer = next(
        (
            asset
            for asset in assets
            if str(asset.get("name") or "").startswith(INSTALLER_PREFIX)
            and str(asset.get("name") or "").endswith(".exe")
        ),
        None,
    )
    if installer is None:
        raise RuntimeError("Latest release does not include an installer asset.")

    checksum = next(
        (
            asset
            for asset in assets
            if str(asset.get("name") or "") == f"{installer['name']}.sha256"
        ),
        None,
    )

    return {
        "latest_tag": latest_tag,
        "latest_version": latest_version,
        "installer": installer,
        "checksum": checksum,
        "html_url": release.get("html_url") or "https://github.com/Drakcain/PaliaHotpotReminder/releases",
        "body": str(release.get("body") or "").strip(),
    }


def download_and_launch_update(offer: Dict[str, Any]) -> Path:
    installer = offer["installer"]
    checksum_asset = offer.get("checksum")
    temp_dir = Path(tempfile.mkdtemp(prefix="hpr-update-"))
    installer_path = temp_dir / str(installer["name"])

    urllib.request.urlretrieve(str(installer["browser_download_url"]), installer_path)

    if checksum_asset:
        checksum_path = temp_dir / str(checksum_asset["name"])
        urllib.request.urlretrieve(str(checksum_asset["browser_download_url"]), checksum_path)
        checksum_text = checksum_path.read_text(encoding="utf-8", errors="replace").strip()
        expected_hash = checksum_text.split()[0].strip()
        actual_hash = hashlib.sha256(installer_path.read_bytes()).hexdigest().upper()
        if actual_hash != expected_hash.upper():
            raise RuntimeError(
                f"Installer checksum mismatch. Expected {expected_hash.upper()}, got {actual_hash}."
            )

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([str(installer_path)], close_fds=True, creationflags=creation_flags)
    return installer_path


def open_releases_page() -> None:
    url = "https://github.com/Drakcain/PaliaHotpotReminder/releases"
    os.startfile(url)  # type: ignore[attr-defined]
