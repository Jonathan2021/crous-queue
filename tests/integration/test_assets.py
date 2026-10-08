import json
from hashlib import sha256

from crous_queue.api.pages import ROOT, worker_source


def test_vendored_assets_packaged_hashes_and_worker_revision(tmp_path):
    root = ROOT / "static/vendor/leaflet"
    manifest = json.loads((root / "provenance.json").read_text())
    assert manifest["version"] == "1.9.4"
    for item in manifest["files"]:
        assert sha256((root / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    assert "Redistribution and use" in (root / "LICENSE").read_text()
    # Nested map assets must change the worker revision too.
    (tmp_path / "vendor").mkdir()
    (tmp_path / "sw.js").write_text('const version="__ASSET_REVISION__";')
    (tmp_path / "vendor/map.js").write_text("v1")
    before = worker_source(tmp_path)
    (tmp_path / "vendor/map.js").write_text("v2")
    assert worker_source(tmp_path) != before
