from pathlib import Path

ROOT = Path("docs")


def test_single_main_landmark():
    html = (ROOT / "index.html").read_text()
    assert html.count("<main") == 1
    assert 'id="main"' in html
    assert 'type="module" src="./js/app.js' in html
    assert "0.668" not in html
    assert "58.0%" not in html
    assert "fonts.googleapis.com" not in html
    assert 'id="map-stage"' in html
    assert 'id="map-target"' in html
    for name in (
        "Overview",
        "Model Health",
        "Attack Lab",
        "Decision Twins",
        "Evidence Gap",
        "Remediation",
        "Integrity Watch",
        "Evidence Room",
    ):
        assert name in html


def test_reference_json_present():
    import json
    for name in ("findings.json", "model_health.json", "policy.json", "twins.json", "remediation.json", "watch.json"):
        assert (ROOT / "data" / name).exists(), name
    health = json.loads((ROOT / "data" / "model_health.json").read_text())
    assert health["core_metrics"]["roc_auc"]
    assert health["policy_id"] == "janus-default-credit-v1"
    assert health["rolling"]["skipped"] is True
    assert "observation date" in health["rolling"]["reason"]


def test_api_js_no_duplicate_exports():
    text = (ROOT / "js" / "api.js").read_text()
    assert text.count("export function apiDetail") == 1
    assert text.count("export async function pingApi") == 1
    assert text.count("export async function fetchJSON") == 1
    for name in (
        "format.js",
        "api.js",
        "state.js",
        "router.js",
        "charts.js",
        "app.js",
        "pages/overview.js",
        "pages/model-health.js",
        "pages/attack-lab.js",
        "pages/intake.js",
        "pages/assumptions.js",
        "pages/evidence-gap.js",
        "pages/remediation.js",
        "pages/integrity-watch.js",
        "pages/evidence-room.js",
        "pages/decision-twins.js",
        "pages/overview.js",
        "pages/model-health.js",
    ):
        assert (ROOT / "js" / name).exists(), name
