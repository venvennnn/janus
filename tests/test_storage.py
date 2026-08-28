from janus.storage import MemoryStore


def test_memory_store_drops_raw():
    store = MemoryStore()
    rec = store.create({"name": "t", "estimator": object(), "holdout": [1], "status": "draft"})
    assert store.get(rec["id"])["estimator"] is not None
    store.drop_raw(rec["id"])
    again = store.get(rec["id"])
    assert "estimator" not in again
    assert "holdout" not in again
    assert again["name"] == "t"
