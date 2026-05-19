from hearme_broker.eligibility import is_scope_eligible


def test_worldwide_accepts_any_predicates():
    assert is_scope_eligible(
        question={"scope": "worldwide", "country": None, "continent": None},
        disclosed_predicates={},
    )


def test_country_requires_matching_country_predicate():
    question = {"scope": "country", "country": "DE", "continent": "EU"}

    assert is_scope_eligible(
        question=question,
        disclosed_predicates={"country": "DE", "continent": "EU"},
    )
    assert not is_scope_eligible(
        question=question,
        disclosed_predicates={"country": "FR", "continent": "EU"},
    )
    assert not is_scope_eligible(
        question=question,
        disclosed_predicates={"region": "EU"},
    )


def test_continent_accepts_continent_or_legacy_region_predicate():
    question = {"scope": "continent", "country": None, "continent": "EU"}

    assert is_scope_eligible(
        question=question,
        disclosed_predicates={"continent": "EU"},
    )
    assert is_scope_eligible(
        question=question,
        disclosed_predicates={"region": "EU"},
    )
    assert not is_scope_eligible(
        question=question,
        disclosed_predicates={"continent": "NA"},
    )
