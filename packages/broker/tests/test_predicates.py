"""Pure predicate derivation — country->region, thresholds->age_band."""

from __future__ import annotations

import pytest

from hearme_broker.verify.predicates import (
    PredicateError,
    country_to_region,
    derive_predicates,
    thresholds_to_age_band,
)


@pytest.mark.parametrize(
    "country,region",
    [
        ("DE", "EU"), ("de", "EU"), ("FR", "EU"), ("GB", "EU"), ("RU", "EU"),
        ("US", "NA"), ("MX", "NA"), ("BR", "SA"), ("AR", "SA"),
        ("JP", "AS"), ("CN", "AS"), ("IN", "AS"),
        ("NG", "AF"), ("ZA", "AF"), ("AU", "OC"), ("NZ", "OC"),
    ],
)
def test_country_to_region(country, region):
    assert country_to_region(country) == region


def test_country_to_region_unmapped_raises():
    with pytest.raises(PredicateError):
        country_to_region("ZZ")
    with pytest.raises(PredicateError):
        country_to_region("")


# ICAO Doc 9303 MRZ-formatted nationality codes: passports may disclose the raw
# MRZ field rather than ISO-3166. The most common one in the wild is German
# passports issued before the 2007 ePassport rollout, where the country field
# is ``D<<`` ("D" padded with MRZ filler chars). The mapper must strip the
# fillers and remap to ``DE``.
@pytest.mark.parametrize(
    "country,region",
    [
        ("D<<", "EU"),     # legacy German MRZ form
        ("D", "EU"),       # same code after stripping fillers
        ("d<<", "EU"),     # lower-case + fillers
        ("USA<", "NA"),    # trailing filler on an otherwise valid alpha-3
        ("DEU<<", "EU"),   # alpha-3 with trailing fillers
    ],
)
def test_country_to_region_mrz(country, region):
    assert country_to_region(country) == region


def test_derive_predicates_mrz_germany():
    # An incoming legacy MRZ German code must produce the normalized alpha-2
    # form in the disclosed `country` field, not the raw `D<<`.
    assert derive_predicates(nationality="D<<", satisfied_thresholds=[18]) == {
        "region": "EU",
        "country": "DE",
        "age_band": "18+",
    }


@pytest.mark.parametrize(
    "satisfied,band",
    [
        ([18], "18+"),
        ([18, 25], "25-34"),
        ([18, 25, 35], "35-49"),
        ([18, 25, 35, 50], "50-64"),
        ([18, 25, 35, 50, 65], "65+"),
        ([35, 25, 18], "35-49"),  # order-independent
    ],
)
def test_thresholds_to_age_band(satisfied, band):
    assert thresholds_to_age_band(satisfied) == band


def test_thresholds_without_18_rejected():
    with pytest.raises(PredicateError):
        thresholds_to_age_band([25, 35])
    with pytest.raises(PredicateError):
        thresholds_to_age_band([])


def test_unknown_thresholds_ignored():
    # 40 isn't on the ladder; ignored, band still from the valid max (35).
    assert thresholds_to_age_band([18, 25, 35, 40]) == "35-49"


def test_derive_predicates():
    # Lower-case input is normalised; the raw country is disclosed alongside the
    # continent so worldwide questions can break down per nation.
    assert derive_predicates(nationality="fr", satisfied_thresholds=[18, 25]) == {
        "region": "EU",
        "country": "FR",
        "age_band": "25-34",
    }
