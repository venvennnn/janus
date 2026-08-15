window.JANUS_FINDINGS = {
  "product": "JANUS",
  "version": "0.3.0",
  "generated_at": "2026-08-15T05:01:45.991268+00:00",
  "seed": 20260811,
  "model": {
    "n_features": 13,
    "features": [
      "age",
      "employment_months",
      "savings_balance",
      "debt_to_income",
      "credit_inquiries_12m",
      "open_trade_lines",
      "credit_history_months",
      "postal_density",
      "credit_utilization",
      "requested_amount",
      "late_payments_24m",
      "residence_months",
      "bank_relationship_months"
    ],
    "protected_attributes": [],
    "cutoff": 0.275,
    "auc_holdout": 0.668,
    "approval_rate": 0.4798,
    "n_holdout": 8479,
    "default_rate_holdout": 0.2966,
    "default_rate_approved": 0.1947,
    "coefficients": {
      "age": 0.0985,
      "employment_months": -0.0292,
      "savings_balance": -0.294,
      "debt_to_income": 0.3882,
      "credit_inquiries_12m": 0.147,
      "open_trade_lines": 0.011,
      "credit_history_months": -0.0123,
      "postal_density": 0.0152,
      "credit_utilization": 0.2117,
      "requested_amount": -0.0012,
      "late_payments_24m": 0.1736,
      "residence_months": 0.004,
      "bank_relationship_months": 0.0259
    },
    "influence_rank": [
      {
        "feature": "debt_to_income",
        "coefficient": 0.3882
      },
      {
        "feature": "savings_balance",
        "coefficient": -0.294
      },
      {
        "feature": "credit_utilization",
        "coefficient": 0.2117
      },
      {
        "feature": "late_payments_24m",
        "coefficient": 0.1736
      },
      {
        "feature": "credit_inquiries_12m",
        "coefficient": 0.147
      },
      {
        "feature": "age",
        "coefficient": 0.0985
      },
      {
        "feature": "employment_months",
        "coefficient": -0.0292
      },
      {
        "feature": "bank_relationship_months",
        "coefficient": 0.0259
      },
      {
        "feature": "postal_density",
        "coefficient": 0.0152
      },
      {
        "feature": "credit_history_months",
        "coefficient": -0.0123
      },
      {
        "feature": "open_trade_lines",
        "coefficient": 0.011
      },
      {
        "feature": "residence_months",
        "coefficient": 0.004
      },
      {
        "feature": "requested_amount",
        "coefficient": -0.0012
      }
    ],
    "heaviest_feature": "debt_to_income"
  },
  "mutability_model": [
    {
      "feature": "savings_balance",
      "kind": "cosmetic",
      "direction": "up",
      "attack_cost_jpy": 20,
      "attack_days": 0.15,
      "genuine_cost_jpy": 14000,
      "genuine_days": 30,
      "legitimate_attack": false,
      "rationale": "Unverified snapshot. A same-day transfer presents a higher balance; earning it takes a pay cycle."
    },
    {
      "feature": "credit_inquiries_12m",
      "kind": "cosmetic",
      "direction": "down",
      "attack_cost_jpy": 24,
      "attack_days": 0.2,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": false,
      "rationale": "Timing artefact. Suppressing inquiries is cosmetic. Ageing them out is not a financial improvement."
    },
    {
      "feature": "credit_utilization",
      "kind": "mixed",
      "direction": "down",
      "attack_cost_jpy": 40,
      "attack_days": 0.4,
      "genuine_cost_jpy": 2200,
      "genuine_days": 22,
      "legitimate_attack": false,
      "rationale": "Balance can be parked on another card (cosmetic) or repaid (genuine)."
    },
    {
      "feature": "requested_amount",
      "kind": "cosmetic",
      "direction": "down",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": null,
      "rationale": "Applicant choice. Asking for less does not change capacity and is not an integrity lever."
    },
    {
      "feature": "debt_to_income",
      "kind": "genuine",
      "direction": "down",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": 1450,
      "genuine_days": 16,
      "legitimate_attack": null,
      "rationale": "Genuine path: earn more or retire debt. Documentation of existing income is Route C, not this lever."
    },
    {
      "feature": "employment_months",
      "kind": "genuine",
      "direction": "up",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": null,
      "rationale": "Tenure only moves with time. Not priced as an earn-it lever."
    },
    {
      "feature": "bank_relationship_months",
      "kind": "genuine",
      "direction": "up",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": null,
      "rationale": "Relationship length is calendar time."
    },
    {
      "feature": "late_payments_24m",
      "kind": "immutable",
      "direction": "down",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": null,
      "rationale": "Bureau history. Not legitimately editable inside an application window."
    },
    {
      "feature": "credit_history_months",
      "kind": "immutable",
      "direction": "up",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": null,
      "rationale": "Ages only with time beyond the audit horizon."
    },
    {
      "feature": "age",
      "kind": "immutable",
      "direction": "up",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": null,
      "rationale": "Immutable."
    },
    {
      "feature": "postal_density",
      "kind": "immutable",
      "direction": "up",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": null,
      "rationale": "Geography. The rural proxy. Moving house is outside the recourse window."
    },
    {
      "feature": "residence_months",
      "kind": "immutable",
      "direction": "up",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": null,
      "rationale": "Time at address. Not a one-cycle lever."
    },
    {
      "feature": "open_trade_lines",
      "kind": "mixed",
      "direction": "down",
      "attack_cost_jpy": null,
      "attack_days": null,
      "genuine_cost_jpy": null,
      "genuine_days": null,
      "legitimate_attack": null,
      "rationale": "Closing a trade to move a score is possible but weak on this book; left inert."
    }
  ],
  "battery": {
    "attack_surface": {
      "run_id": "run.attack_surface",
      "n_sampled": 300,
      "n_flipped": 174,
      "flip_rate": 0.58,
      "median_cost_jpy": 64.0,
      "p90_cost_jpy": 128.0,
      "budget_jpy": 60000,
      "flipped_default_rate": 0.3736,
      "baseline_default_rate": 0.2966,
      "gamed_worse_than_baseline": true,
      "would_not_have_defaulted": 0.6264,
      "flipped_applicant_ids": [
        "A-16143",
        "A-10869",
        "A-04322",
        "A-09926",
        "A-19776",
        "A-19659",
        "A-00076",
        "A-10529",
        "A-14233",
        "A-21250",
        "A-09380",
        "A-02507",
        "A-18973",
        "A-15486",
        "A-09162",
        "A-14624",
        "A-14273",
        "A-00026",
        "A-23345",
        "A-16611",
        "A-10493",
        "A-19869",
        "A-20933",
        "A-12124",
        "A-06441"
      ]
    },
    "proxy_audit": {
      "run_id": "run.proxy_audit",
      "target": "is_rural",
      "given_to_model": false,
      "probe_auc": 0.9952,
      "n": 8479,
      "base_rate": 0.3348,
      "carriers": [
        {
          "feature": "postal_density",
          "coefficient": -7.0919
        },
        {
          "feature": "residence_months",
          "coefficient": -0.886
        },
        {
          "feature": "age",
          "coefficient": 0.3332
        },
        {
          "feature": "credit_history_months",
          "coefficient": 0.2541
        },
        {
          "feature": "bank_relationship_months",
          "coefficient": -0.2038
        }
      ],
      "chief_carrier": "postal_density"
    },
    "unexplained_exclusion": {
      "run_id": "run.unexplained_exclusion",
      "segment": "is_informal",
      "n_informal": 2227,
      "n_formal": 6252,
      "approval_informal": 0.225,
      "approval_formal": 0.5705,
      "approval_gap_pp": 34.56,
      "default_informal": 0.3107,
      "default_formal": 0.2916,
      "default_gap_pp": 1.91,
      "mechanism": "Cash income unrecorded \u2192 recorded DTI inflates \u2192 DTI is the heaviest feature."
    },
    "broken_segments": {
      "run_id": "run.discover_segments",
      "tree": "|--- debt_to_income <= 0.39\n|   |--- debt_to_income <= 0.30\n|   |   |--- savings_balance <= 8218.50\n|   |   |   |--- class: 0\n|   |   |--- savings_balance >  8218.50\n|   |   |   |--- class: 0\n|   |--- debt_to_income >  0.30\n|   |   |--- savings_balance <= 48602.00\n|   |   |   |--- class: 0\n|   |   |--- savings_balance >  48602.00\n|   |   |   |--- class: 0\n|--- debt_to_income >  0.39\n|   |--- credit_utilization <= 0.50\n|   |   |--- savings_balance <= 24504.00\n|   |   |   |--- class: 0\n|   |   |--- savings_balance >  24504.00\n|   |   |   |--- class: 0\n|   |--- credit_utilization >  0.50\n|   |   |--- debt_to_income <= 0.52\n|   |   |   |--- class: 0\n|   |   |--- debt_to_income >  0.52\n|   |   |   |--- class: 0\n",
      "leaves": [
        {
          "leaf": 4,
          "n": 1764,
          "predicted_default": 0.2118,
          "actual_default": 0.1202,
          "gap_pp": -9.16,
          "approval_rate": 0.8475,
          "kind": "overstated"
        },
        {
          "leaf": 14,
          "n": 1607,
          "predicted_default": 0.4546,
          "actual_default": 0.4935,
          "gap_pp": 3.89,
          "approval_rate": 0.0498,
          "kind": "calibrated"
        },
        {
          "leaf": 3,
          "n": 909,
          "predicted_default": 0.2471,
          "actual_default": 0.2112,
          "gap_pp": -3.58,
          "approval_rate": 0.7074,
          "kind": "calibrated"
        },
        {
          "leaf": 10,
          "n": 1756,
          "predicted_default": 0.3445,
          "actual_default": 0.3764,
          "gap_pp": 3.19,
          "approval_rate": 0.3007,
          "kind": "calibrated"
        },
        {
          "leaf": 7,
          "n": 143,
          "predicted_default": 0.1698,
          "actual_default": 0.1399,
          "gap_pp": -3.0,
          "approval_rate": 0.9301,
          "kind": "calibrated"
        },
        {
          "leaf": 11,
          "n": 689,
          "predicted_default": 0.2683,
          "actual_default": 0.2453,
          "gap_pp": -2.3,
          "approval_rate": 0.5936,
          "kind": "calibrated"
        },
        {
          "leaf": 13,
          "n": 617,
          "predicted_default": 0.316,
          "actual_default": 0.3371,
          "gap_pp": 2.12,
          "approval_rate": 0.2674,
          "kind": "calibrated"
        },
        {
          "leaf": 6,
          "n": 994,
          "predicted_default": 0.2641,
          "actual_default": 0.2616,
          "gap_pp": -0.25,
          "approval_rate": 0.6187,
          "kind": "calibrated"
        }
      ],
      "worst_understated": {
        "leaf": 14,
        "n": 1607,
        "predicted_default": 0.4546,
        "actual_default": 0.4935,
        "gap_pp": 3.89,
        "approval_rate": 0.0498,
        "kind": "calibrated"
      },
      "young_self_employed": {
        "n": 724,
        "predicted_default": 0.3033,
        "actual_default": 0.1685,
        "approval_rate": 0.5083
      }
    },
    "integrity_gap": {
      "run_id": "run.integrity_gap",
      "n_sampled": 250,
      "n_dual_flip": 146,
      "median_attack_cost_jpy": 64.0,
      "median_genuine_cost_jpy": 8800.0,
      "median_genuine_days": 88.0,
      "median_gap_ratio": 110.0,
      "note": "Median of per-applicant (genuine/attack) ratios. Not the ratio of medians. Not interchangeable with attack_surface.median_cost_jpy.",
      "attack_flip_rate": 0.584,
      "genuine_flip_rate": 0.78,
      "would_not_have_defaulted_among_gameable": 0.6233
    },
    "evidence_recourse": {
      "run_id": "run.evidence_recourse",
      "n_declined_informal": 1726,
      "median_recorded_dti": 1.0017,
      "median_true_dti": 0.4053,
      "cross_rate_full_documentation": 0.4143,
      "n_cross_full": 715,
      "cross_default_rate": 0.2713,
      "portfolio_default_rate": 0.2966,
      "cross_rate_among_non_default": 0.4715,
      "n_informal_non_default": 1105,
      "documentation_curve": [
        {
          "documented_share": 0.25,
          "cross_rate": 0.1448,
          "n_cross": 250
        },
        {
          "documented_share": 0.5,
          "cross_rate": 0.2509,
          "n_cross": 433
        },
        {
          "documented_share": 0.75,
          "cross_rate": 0.3349,
          "n_cross": 578
        },
        {
          "documented_share": 1.0,
          "cross_rate": 0.4143,
          "n_cross": 715
        }
      ],
      "priced_in": "documentation_months",
      "median_documentation_months": 6,
      "cost_jpy": 0,
      "mean_p_start": 0.4539,
      "mean_p_documented": 0.3116
    },
    "gap_attribution": {
      "run_id": "run.gap_attribution",
      "groups": [
        {
          "group": "leverage_and_income",
          "features": [
            "debt_to_income",
            "requested_amount"
          ],
          "abs_coefficient_share": 0.2758
        },
        {
          "group": "presentable_balances",
          "features": [
            "savings_balance",
            "credit_utilization"
          ],
          "abs_coefficient_share": 0.3582
        },
        {
          "group": "bureau_timing",
          "features": [
            "credit_inquiries_12m",
            "open_trade_lines",
            "late_payments_24m"
          ],
          "abs_coefficient_share": 0.2349
        },
        {
          "group": "tenure",
          "features": [
            "employment_months",
            "credit_history_months",
            "bank_relationship_months",
            "age",
            "residence_months"
          ],
          "abs_coefficient_share": 0.1204
        },
        {
          "group": "geography_proxy",
          "features": [
            "postal_density"
          ],
          "abs_coefficient_share": 0.0108
        }
      ],
      "note": "Share of |coefficient| mass. Real scorecards are not willingness/ability/macro."
    }
  },
  "demo_applicant": {
    "applicant_id": "A-7100",
    "age": 21,
    "is_informal": 1,
    "is_rural": 1,
    "self_employed": 1,
    "recorded_dti": 1.07,
    "true_dti": 0.5,
    "income_true": 48000.0,
    "income_recorded": 22429.91,
    "savings_balance": 4200.0,
    "credit_utilization": 0.48,
    "credit_inquiries_12m": 0,
    "default": 0
  },
  "recourse_menu": {
    "run_id": "run.recourse_menu",
    "applicant_id": "A-7100",
    "p_start": 0.34850271227340346,
    "cutoff": 0.275,
    "declined": true,
    "default": 0,
    "route_a_fake_it": {
      "flipped": true,
      "cost_jpy": 120.0,
      "days": 1.1,
      "steps": 4,
      "p_start": 0.34850271227340346,
      "p_final": 0.2709410222323441,
      "features": [
        "savings_balance",
        "credit_utilization"
      ],
      "first_feature": "savings_balance",
      "audience": "model_owner_only"
    },
    "route_b_earn_it": {
      "flipped": true,
      "cost_jpy": 10150.0,
      "days": 112.0,
      "steps": 7,
      "p_start": 0.34850271227340346,
      "p_final": 0.27286667715546775,
      "features": [
        "debt_to_income"
      ],
      "first_feature": "debt_to_income"
    },
    "route_b_alternatives": [
      {
        "flipped": true,
        "cost_jpy": 11000.0,
        "days": 110.0,
        "steps": 5,
        "p_start": 0.34850271227340346,
        "p_final": 0.2634415930439468,
        "features": [
          "credit_utilization"
        ],
        "first_feature": "credit_utilization"
      },
      {
        "flipped": true,
        "cost_jpy": 56000.0,
        "days": 120.0,
        "steps": 4,
        "p_start": 0.34850271227340346,
        "p_final": 0.2626856993029762,
        "features": [
          "savings_balance"
        ],
        "first_feature": "savings_balance"
      }
    ],
    "route_c_document_it": {
      "flipped": true,
      "cost_jpy": 0.0,
      "days": 180.0,
      "documentation_months": 6,
      "p_start": 0.34850271227340346,
      "p_final": 0.23095002722538804,
      "dti_start": 1.07,
      "dti_final": 0.5000000770833334,
      "dti_true": 0.5,
      "features": [
        "debt_to_income"
      ],
      "ask": "Change nothing. Make existing income visible."
    }
  },
  "investigation": {
    "objective": "Does this model reward genuine creditworthiness, or the ability to manipulate what it sees?",
    "human_gates": [
      {
        "id": "gate.mutability",
        "label": "Confirm feature mutability model",
        "status": "accepted",
        "why": "Lender-specific. Un-hardcodable. The agent proposes; a person signs."
      },
      {
        "id": "gate.findings",
        "label": "Accept or reject each finding",
        "status": "pending",
        "why": "Janus produces evidence. A person decides what enters the memo."
      }
    ],
    "hypotheses": [
      {
        "id": "H1",
        "from_run": "run.attack_surface",
        "statement": "A large share of declines flip on cosmetic change. Are those applicants actually lower risk?",
        "test": "Compare realised default of the flipped cohort to the portfolio baseline."
      },
      {
        "id": "H2",
        "from_run": "run.unexplained_exclusion",
        "statement": "Informal-income applicants are excluded far more than their default rate can explain. Is this measurement error in DTI?",
        "test": "Re-score after documenting the recorded/true income gap (evidence_recourse)."
      },
      {
        "id": "H3",
        "from_run": "run.proxy_audit",
        "statement": "Rural residence is recoverable at 0.9952 AUC from model-visible features, chiefly postal_density.",
        "test": "Name the carrier. Do not treat geography as an integrity lever."
      },
      {
        "id": "H4",
        "from_run": "run.integrity_gap",
        "statement": "The honest route is orders of magnitude more expensive than the cosmetic route. Why?",
        "test": "Attribute the gap and price Route C (documentation) separately from earning."
      }
    ],
    "follow_ups": [
      {
        "id": "E.H1",
        "hypothesis": "H1",
        "experiment": "cohort_compare flipped vs baseline default",
        "run_id": "run.attack_surface",
        "result": "Flipped cohort defaults at 0.3736 vs baseline 0.2966. Gamed approvals are not safer."
      },
      {
        "id": "E.H2",
        "hypothesis": "H2",
        "experiment": "evidence_recourse full documentation",
        "run_id": "run.evidence_recourse",
        "result": "0.4143 of declined informal-income applicants cross the cutoff on documentation alone. Those who cross default at 0.2713."
      },
      {
        "id": "E.H4",
        "hypothesis": "H4",
        "experiment": "route_c vs earn-it",
        "run_id": "run.evidence_recourse",
        "result": "The honest *financial* route is expensive because recorded DTI is wrong. The correct honest route is documentation: \u00a50."
      }
    ],
    "findings": [
      {
        "id": "F01",
        "title": "Gaming surface",
        "severity": "high",
        "accepted": true,
        "run_id": "run.attack_surface",
        "claim": "58.0% of declined applicants are flippable by cosmetic change (n=300, \u00a560k budget); median attack cost \u00a564.0. Flipped cohort defaults at 37.4% vs 29.7% baseline."
      },
      {
        "id": "F02",
        "title": "Proxy reconstruction",
        "severity": "high",
        "accepted": true,
        "run_id": "run.proxy_audit",
        "claim": "Rural residence is recoverable from model-visible features at 0.9952 AUC, carried chiefly by postal_density. The model was never given it."
      },
      {
        "id": "F03",
        "title": "Unexplained exclusion",
        "severity": "high",
        "accepted": true,
        "run_id": "run.unexplained_exclusion",
        "claim": "Undocumented-income applicants approved 34.56pp less often; realised default 31.1% vs 29.2%."
      },
      {
        "id": "F04",
        "title": "Broken segments",
        "severity": "medium",
        "accepted": true,
        "run_id": "run.discover_segments",
        "claim": "Worst understated leaf (n=1607): predicted 45.5% vs actual 49.4%. Young self-employed (n=724): predicted 30.3% vs actual 16.9%; approved 50.8% vs 48.0% overall."
      },
      {
        "id": "F05",
        "title": "Integrity gap",
        "severity": "high",
        "accepted": true,
        "run_id": "run.integrity_gap",
        "claim": "110.0\u00d7 median. Fake it: \u00a564.0. Earn it: \u00a58800.0 / 88.0 days. 62.3% of gameable declines would not have defaulted."
      },
      {
        "id": "F06",
        "title": "Evidence recourse",
        "severity": "high",
        "accepted": true,
        "run_id": "run.evidence_recourse",
        "claim": "41.4% of declined informal-income applicants (n=1726) cross the cutoff on documentation alone. Those who cross default at 27.1% vs 29.7% portfolio. Among non-defaulters, 47.1% cross."
      }
    ],
    "graph": {
      "nodes": [
        {
          "id": "obs.model",
          "kind": "observation",
          "label": "Scorecard AUC 0.668",
          "run_id": "run.inspect_model"
        },
        {
          "id": "obs.attack",
          "kind": "observation",
          "label": "Gaming surface",
          "run_id": "run.attack_surface"
        },
        {
          "id": "obs.proxy",
          "kind": "observation",
          "label": "Proxy probe",
          "run_id": "run.proxy_audit"
        },
        {
          "id": "obs.excl",
          "kind": "observation",
          "label": "Exclusion table",
          "run_id": "run.unexplained_exclusion"
        },
        {
          "id": "obs.seg",
          "kind": "observation",
          "label": "Segment calibration",
          "run_id": "run.discover_segments"
        },
        {
          "id": "obs.gap",
          "kind": "observation",
          "label": "Integrity gap",
          "run_id": "run.integrity_gap"
        },
        {
          "id": "obs.ev",
          "kind": "observation",
          "label": "Evidence recourse",
          "run_id": "run.evidence_recourse"
        },
        {
          "id": "H1",
          "kind": "hypothesis",
          "label": "A large share of declines flip on cosmetic change. Are those applicants actually lower risk?",
          "run_id": "run.attack_surface"
        },
        {
          "id": "H2",
          "kind": "hypothesis",
          "label": "Informal-income applicants are excluded far more than their default rate can explain. Is this measurement error in DTI?",
          "run_id": "run.unexplained_exclusion"
        },
        {
          "id": "H3",
          "kind": "hypothesis",
          "label": "Rural residence is recoverable at 0.9952 AUC from model-visible features, chiefly postal_density.",
          "run_id": "run.proxy_audit"
        },
        {
          "id": "H4",
          "kind": "hypothesis",
          "label": "The honest route is orders of magnitude more expensive than the cosmetic route. Why?",
          "run_id": "run.integrity_gap"
        },
        {
          "id": "E.H1",
          "kind": "experiment",
          "label": "cohort_compare flipped vs baseline default",
          "run_id": "run.attack_surface"
        },
        {
          "id": "E.H2",
          "kind": "experiment",
          "label": "evidence_recourse full documentation",
          "run_id": "run.evidence_recourse"
        },
        {
          "id": "E.H4",
          "kind": "experiment",
          "label": "route_c vs earn-it",
          "run_id": "run.evidence_recourse"
        },
        {
          "id": "F01",
          "kind": "conclusion",
          "label": "Gaming surface",
          "run_id": "run.attack_surface"
        },
        {
          "id": "F02",
          "kind": "conclusion",
          "label": "Proxy reconstruction",
          "run_id": "run.proxy_audit"
        },
        {
          "id": "F03",
          "kind": "conclusion",
          "label": "Unexplained exclusion",
          "run_id": "run.unexplained_exclusion"
        },
        {
          "id": "F04",
          "kind": "conclusion",
          "label": "Broken segments",
          "run_id": "run.discover_segments"
        },
        {
          "id": "F05",
          "kind": "conclusion",
          "label": "Integrity gap",
          "run_id": "run.integrity_gap"
        },
        {
          "id": "F06",
          "kind": "conclusion",
          "label": "Evidence recourse",
          "run_id": "run.evidence_recourse"
        }
      ],
      "edges": [
        [
          "obs.model",
          "obs.attack"
        ],
        [
          "obs.model",
          "obs.proxy"
        ],
        [
          "obs.model",
          "obs.excl"
        ],
        [
          "obs.model",
          "obs.seg"
        ],
        [
          "obs.attack",
          "H1"
        ],
        [
          "obs.excl",
          "H2"
        ],
        [
          "obs.proxy",
          "H3"
        ],
        [
          "obs.gap",
          "H4"
        ],
        [
          "H1",
          "E.H1"
        ],
        [
          "H2",
          "E.H2"
        ],
        [
          "H4",
          "E.H4"
        ],
        [
          "E.H1",
          "F01"
        ],
        [
          "obs.proxy",
          "F02"
        ],
        [
          "E.H2",
          "F03"
        ],
        [
          "obs.seg",
          "F04"
        ],
        [
          "obs.gap",
          "F05"
        ],
        [
          "E.H2",
          "F06"
        ],
        [
          "E.H4",
          "F06"
        ]
      ]
    },
    "memo_spine": [
      "Gaming surface",
      "Proxy reconstruction",
      "Unexplained exclusion",
      "Broken segments",
      "Integrity gap",
      "Evidence recourse"
    ]
  },
  "figure_discipline": {
    "rule": "Only numbers from run_audit.py / integrity_gap / evidence_recourse may appear.",
    "attack_cost_medians_are_not_interchangeable": true,
    "sources": [
      "janus/run_audit.py",
      "janus/audits.py",
      "janus/data_gen.py"
    ]
  }
};
