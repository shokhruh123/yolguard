from app.services.rules import evaluate, Triage, completeness

def test_red_on_injury():
    c, _ = evaluate(Triage(has_injury=True))
    assert c == "red"

def test_red_single_vehicle_rule():
    c, _ = evaluate(Triage(vehicle_count=1, responsibility_accepted=True, docs_valid=True, sober=True, damage_agreed=True))
    assert c == "red"

def test_green_happy_path():
    c, _ = evaluate(Triage(responsibility_accepted=True, docs_valid=True, sober=True, damage_agreed=True))
    assert c == "green"

def test_completeness():
    r = completeness(["scene_overview", "both_vehicles"])
    assert r["percent"] < 100 and "plate_a" in r["missing"]
