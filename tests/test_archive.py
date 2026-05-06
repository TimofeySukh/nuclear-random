from __future__ import annotations

import json

from nuclear_random_api.archive import EntropyArchive
from nuclear_random_api.settings import settings


def test_archive_writes_manifest_and_entropy(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "archive_enabled", True)
    monkeypatch.setattr(settings, "archive_dir", str(tmp_path))
    monkeypatch.setattr(settings, "archive_rotate_bytes", 1024)

    archive = EntropyArchive()
    archive.append(b"\x01\x02\x03")
    status = archive.status()

    assert status is not None
    assert status.total_archived_bytes == 3
    assert (tmp_path / status.current_file).read_bytes() == b"\x01\x02\x03"
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["extractor"] == "von_neumann"
    assert manifest["raw_bits_per_click"] == settings.raw_bits_per_click


def test_archive_rotates_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "archive_enabled", True)
    monkeypatch.setattr(settings, "archive_dir", str(tmp_path))
    monkeypatch.setattr(settings, "archive_rotate_bytes", 4)

    archive = EntropyArchive()
    archive.append(b"\x00\x01\x02\x03")
    archive.append(b"\x04")
    status = archive.status()

    assert status is not None
    assert status.file_count == 2
    assert len(list(tmp_path.glob("entropy_*.bin"))) == 2
