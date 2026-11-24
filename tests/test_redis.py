import pytest

import callscope

fakeredis = pytest.importorskip("fakeredis")


def test_commands_show_name_and_key_but_never_values():
    r = fakeredis.FakeRedis()
    with callscope.scope("t") as s:
        r.set("session:42", "top-secret-value")
        assert r.get("session:42") == b"top-secret-value"
    assert [c.target for c in s.calls] == ["SET session:42", "GET session:42"]
    assert all("top-secret" not in c.target for c in s.calls)


def test_pipeline_is_one_call():
    r = fakeredis.FakeRedis()
    with callscope.scope("t") as s:
        pipe = r.pipeline()
        pipe.set("a", 1).incr("a").get("a")
        assert pipe.execute()[-1] == b"2"
    assert s.count("redis") == 1
    # redis-py sends INCR as INCRBY; we show what actually goes over the wire.
    assert s.calls[0].target == "PIPELINE[3] SET, INCRBY, GET"
