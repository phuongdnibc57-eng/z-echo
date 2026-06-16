# tests/test_frontmatter.py
from zecho import frontmatter as fm

def test_parse_roundtrip(tmp_path):
    text = "---\nid: ISS-0001\nfreq: 3\n---\n# Title\nbody line\n"
    meta, body = fm.parse(text)
    assert meta["id"] == "ISS-0001"
    assert meta["freq"] == 3
    assert body == "# Title\nbody line\n"

def test_serialize_roundtrip():
    meta = {"id": "ISS-0002", "component": "payment, qr"}
    body = "# T\nx\n"
    out = fm.serialize(meta, body)
    meta2, body2 = fm.parse(out)
    assert meta2["id"] == "ISS-0002"
    assert meta2["component"] == "payment, qr"
    assert body2 == body

def test_load_save(tmp_path):
    p = tmp_path / "x.md"
    fm.save(p, {"id": "ISS-0003"}, "body\n")
    meta, body = fm.load(p)
    assert meta["id"] == "ISS-0003"
    assert body == "body\n"

def test_parse_no_frontmatter():
    meta, body = fm.parse("just body\n")
    assert meta == {}
    assert body == "just body\n"
