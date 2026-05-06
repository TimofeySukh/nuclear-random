from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .settings import settings


@dataclass(frozen=True)
class ArchiveStatus:
    current_file: str
    current_file_size: int
    total_archived_bytes: int
    file_count: int


class EntropyArchive:
    def __init__(self) -> None:
        self._enabled = settings.archive_enabled
        self._lock = threading.Lock()
        self._dir = Path(settings.archive_dir)
        self._manifest_path = self._dir / "manifest.json"
        if not self._enabled:
            return

        self._dir.mkdir(parents=True, exist_ok=True)
        self._ensure_manifest()

    def append(self, entropy: bytes) -> None:
        if not self._enabled or not entropy:
            return

        with self._lock:
            manifest = self._read_manifest()
            file_name = str(manifest["current_file"])
            file_path = self._dir / file_name
            if int(manifest["current_file_size"]) + len(entropy) > settings.archive_rotate_bytes:
                file_name = self._next_file_name(int(manifest["file_count"]))
                file_path = self._dir / file_name
                manifest["current_file"] = file_name
                manifest["current_file_size"] = 0
                manifest["file_count"] = int(manifest["file_count"]) + 1
                manifest["files"].append(
                    {
                        "name": file_name,
                        "started_at_unix": time.time(),
                        "bytes": 0,
                    }
                )

            with file_path.open("ab") as archive_file:
                archive_file.write(entropy)
                archive_file.flush()
                os.fsync(archive_file.fileno())

            manifest["current_file_size"] = int(manifest["current_file_size"]) + len(entropy)
            manifest["total_archived_bytes"] = int(manifest["total_archived_bytes"]) + len(entropy)
            manifest["updated_at_unix"] = time.time()
            manifest["files"][-1]["bytes"] = int(manifest["files"][-1]["bytes"]) + len(entropy)
            self._write_manifest(manifest)

    def status(self) -> ArchiveStatus | None:
        if not self._enabled:
            return None
        manifest = self._read_manifest()
        return ArchiveStatus(
            current_file=str(manifest["current_file"]),
            current_file_size=int(manifest["current_file_size"]),
            total_archived_bytes=int(manifest["total_archived_bytes"]),
            file_count=int(manifest["file_count"]),
        )

    def _ensure_manifest(self) -> None:
        if self._manifest_path.exists():
            return
        first_file = self._next_file_name(0)
        manifest = {
            "version": 1,
            "created_at_unix": time.time(),
            "updated_at_unix": time.time(),
            "extractor": "von_neumann",
            "raw_bits_per_click": settings.raw_bits_per_click,
            "rotate_bytes": settings.archive_rotate_bytes,
            "current_file": first_file,
            "current_file_size": 0,
            "total_archived_bytes": 0,
            "file_count": 1,
            "files": [
                {
                    "name": first_file,
                    "started_at_unix": time.time(),
                    "bytes": 0,
                }
            ],
        }
        self._write_manifest(manifest)

    def _read_manifest(self) -> dict[str, Any]:
        return json.loads(self._manifest_path.read_text(encoding="utf-8"))

    def _write_manifest(self, manifest: dict[str, Any]) -> None:
        self._manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    def _next_file_name(self, index: int) -> str:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        return f"entropy_{stamp}_{index:06d}.bin"
