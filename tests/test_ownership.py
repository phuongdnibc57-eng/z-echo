# tests/test_ownership.py
from zecho import ownership

TABLE = "data/ownership.md"

def test_parse(tmp_path):
    p = tmp_path / "own.md"
    p.write_text(
        "| squad | components | feedback_group_id | oncall |\n"
        "|--|--|--|--|\n"
        "| payment | payment, qr | zalo:group:squad-payment | @oncall_pay |\n",
        encoding="utf-8")
    squads = ownership.parse_ownership(p)
    assert squads[0].name == "payment"
    assert "qr" in squads[0].components
    assert squads[0].feedback_group_id == "zalo:group:squad-payment"
    assert squads[0].oncall == "@oncall_pay"

def test_route(tmp_path):
    p = tmp_path / "own.md"
    p.write_text(
        "| squad | components | feedback_group_id | oncall |\n"
        "|--|--|--|--|\n"
        "| payment | payment, qr | g1 | @a |\n"
        "| messaging | chat | g2 | @b |\n", encoding="utf-8")
    squads = ownership.parse_ownership(p)
    assert ownership.route(squads, "qr").name == "payment"
    assert ownership.route(squads, "chat").name == "messaging"
    assert ownership.route(squads, "unknown") is None
