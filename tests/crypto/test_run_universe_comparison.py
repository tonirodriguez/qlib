from work.crypto.run_universe_comparison import UNIVERSES, comparison_plan, parse_seeds


def test_comparison_plan_uses_same_seeds_for_all_universes():
    plan = comparison_plan((42, 43))
    assert len(plan) == 6
    for universe in UNIVERSES:
        assert [item["seed"] for item in plan if item["universe"] == universe] == [42, 43]


def test_reduced_universe_removes_xlm_but_retains_xrp():
    reduced = UNIVERSES["reduced_8_no_xlm"]
    assert "XLM" not in reduced
    assert "XRP" in reduced
    assert parse_seeds("42, 43") == (42, 43)
