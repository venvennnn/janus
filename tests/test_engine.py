from janus.data_gen import DEMO_ID, FEATURES, documented_dti, generate_portfolio
from janus.levers import MUTABILITY_MODEL, mutability_table
from janus.scorecard import train_scorecard


def test_portfolio_shape_and_mechanisms():
    port = generate_portfolio(n=2000, seed=7)
    assert len(port.features) == 13
    assert set(FEATURES) <= set(port.frame.columns)
    assert port.frame["is_informal"].mean() > 0.15
    informal = port.frame["is_informal"] == 1
    assert port.frame.loc[informal, "debt_to_income"].median() > port.frame.loc[informal, "dti_true"].median()
    rural = port.frame["is_rural"] == 1
    assert port.frame.loc[rural, "postal_density"].mean() < port.frame.loc[~rural, "postal_density"].mean()


def test_demo_applicant_injected():
    port = generate_portfolio(n=500, seed=3)
    row = port.frame.loc[port.frame["applicant_id"] == DEMO_ID].iloc[0]
    assert int(row["age"]) == 21
    assert int(row["is_informal"]) == 1
    assert abs(float(row["debt_to_income"]) - 1.07) < 1e-6
    assert abs(float(row["dti_true"]) - 0.50) < 1e-6
    assert int(row["default"]) == 0
    assert row["split"] == "holdout"


def test_documented_dti_closes_the_gap():
    dti = documented_dti(
        income_true=__import__("numpy").array([100.0]),
        income_recorded=__import__("numpy").array([50.0]),
        dti_recorded=__import__("numpy").array([1.0]),
        share=1.0,
    )
    assert abs(float(dti[0]) - 0.5) < 1e-6


def test_scorecard_trains():
    port = generate_portfolio(n=3000, seed=11)
    card = train_scorecard(port)
    assert 0.55 < card.auc_holdout < 0.95
    assert 0.15 < card.cutoff < 0.5
    p = card.predict_proba(port.holdout)
    assert p.shape == (len(port.holdout),)


def test_mutability_table_covers_features():
    table = mutability_table()
    names = {row["feature"] for row in table}
    assert names == set(FEATURES)
    assert MUTABILITY_MODEL["savings_balance"].attack is not None
    assert MUTABILITY_MODEL["debt_to_income"].attack is None
