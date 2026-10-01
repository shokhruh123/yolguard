from app.services.ai import heuristic_reason, heuristic_svg

def test_heuristic_no_injury():
    r = heuristic_reason({"has_injury": False, "eligibility": "green"}, ["scene_overview"])
    assert "нет" in r["casualties_note"].lower()
    assert len(r["actions"]) > 0

def test_heuristic_injury_priority():
    r = heuristic_reason({"has_injury": True, "eligibility": "red"}, [])
    assert "103" in " ".join(r["actions"])

def test_svg_present():
    assert heuristic_svg().startswith("<svg")
