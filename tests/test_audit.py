from janus.audits import evidence_recourse, unexplained_exclusion
from janus.data_gen import DEMO_ID, generate_portfolio
from janus.scorecard import calibrate_demo_applicant, train_scorecard


def test_reference_book_invariants():
    port = generate_portfolio()
    card = train_scorecard(port)
    holdout = calibrate_demo_applicant(port.holdout, card)
    assert 0.62 < card.auc_holdout < 0.78
    assert 0.40 < card.approval_holdout < 0.56
    heaviest = max(card.coefficients, key=lambda k: abs(card.coefficients[k]))
    assert heaviest == "debt_to_income"

    demo = holdout.loc[holdout["applicant_id"] == DEMO_ID].iloc[0]
    p = float(card.predict_proba(holdout.loc[holdout["applicant_id"] == DEMO_ID])[0])
    assert p >= card.cutoff
    assert int(demo["default"]) == 0
    assert abs(float(demo["debt_to_income"]) - 1.07) < 1e-6

    excl = unexplained_exclusion(holdout, card)
    assert excl["approval_gap_pp"] > 10
    assert abs(excl["default_gap_pp"]) < 6

    ev = evidence_recourse(holdout, card)
    assert ev["cross_rate_full_documentation"] > 0.15
    assert ev["cost_jpy"] == 0
