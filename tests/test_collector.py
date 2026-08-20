from __future__ import annotations

import json

from kpl_analytics.collector.pipeline import RawStore


def test_raw_store_writes_utf8_json_atomically(tmp_path):
    store = RawStore(tmp_path)
    target = store.write("details", "battle-1", {"hero": "公孙离"})

    assert json.loads(target.read_text(encoding="utf-8")) == {"hero": "公孙离"}
    assert not target.with_suffix(".json.tmp").exists()
