"""Tests for the template-based copy generator (no HTTP, no API key)."""

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.copy import CopyRequest
from app.services.copywriting.registry import get_provider
from app.services.copywriting.rule_based import RuleBasedProvider

PROVIDER = RuleBasedProvider()


def make(**overrides) -> CopyRequest:
    data = dict(
        product_name="Rose Quartz Ring",
        category="Jewellery & accessories",
        description="Delicate silver ring with a rose quartz stone. Sizes 5-9.",
        target_audience="women who love minimal jewellery",
        tone="friendly",
        style="aesthetic",
        brand_name="Luna Studio",
        offer="20% off this weekend",
        seed=7,
    )
    data.update(overrides)
    return CopyRequest(**data)


def all_text(resp) -> str:
    parts = [c.text for c in resp.captions] + resp.hashtags + resp.short_descriptions
    parts += [p.text for p in resp.promos] + resp.ctas
    return "\n".join(parts)


def test_provider_is_honestly_labelled_not_ai():
    resp = PROVIDER.generate(make())
    assert resp.provider.id == "template"
    assert resp.provider.is_ai is False
    assert "not ai" in resp.provider.label.lower()
    assert "ai-generated" not in all_text(resp).lower()


def test_same_seed_same_output_different_seed_differs():
    a = PROVIDER.generate(make(seed=1))
    b = PROVIDER.generate(make(seed=1))
    c = PROVIDER.generate(make(seed=2))
    assert a == b
    assert a.captions != c.captions


def test_caption_mix_primary_tone_plus_each_other_tone():
    resp = PROVIDER.generate(make(tone="luxury"))
    tones = [c.tone for c in resp.captions]
    assert tones.count("luxury") == 3
    assert sorted(set(tones)) == ["festive", "friendly", "luxury", "playful", "professional"]
    assert len(resp.captions) == 7
    assert len({c.text for c in resp.captions}) == 7  # all different


@pytest.mark.parametrize("tone", ["friendly", "professional", "luxury", "playful", "festive"])
def test_every_tone_produces_clean_output(tone):
    text = all_text(PROVIDER.generate(make(tone=tone)))
    assert "{" not in text and "}" not in text
    assert "None" not in text
    assert all("  " not in line for line in text.split("\n"))  # no double spaces within a line


def test_hashtags_are_valid_unique_and_capped():
    tags = PROVIDER.generate(make()).hashtags
    assert 5 <= len(tags) <= 15
    assert all(t.startswith("#") and " " not in t and len(t) > 3 for t in tags)
    assert len({t.lower() for t in tags}) == len(tags)
    assert "#RoseQuartzRing" in tags
    assert "#LunaStudio" in tags
    assert "#AestheticVibes" in tags


def test_category_changes_hashtags():
    candle = PROVIDER.generate(make(category="Candles & fragrance")).hashtags
    ring = PROVIDER.generate(make(category="Jewellery & accessories")).hashtags
    assert any(t in candle for t in ("#Candles", "#CandleLovers", "#CosyVibes", "#SelfCareRituals"))
    assert not any(t in ring for t in ("#Candles", "#CandleLovers"))


def test_unknown_category_falls_back():
    tags = PROVIDER.generate(make(category="Other")).hashtags
    assert any(t in tags for t in ("#NewArrival", "#ShopNow", "#MustHave", "#TrendingNow"))


def test_offer_used_when_given_and_absent_otherwise():
    with_offer = PROVIDER.generate(make())
    assert "20% off this weekend" in with_offer.captions[0].text
    assert "20% off this weekend" in with_offer.promos[0].text
    without = PROVIDER.generate(make(offer=""))
    assert "off" not in all_text(without).lower().replace("suited", "")


def test_minimal_input_still_works():
    resp = PROVIDER.generate(CopyRequest(product_name="Tote", seed=3))
    text = all_text(resp)
    assert "Tote" in text
    assert "{" not in text and "None" not in text
    assert len(resp.captions) == 7
    assert len(resp.short_descriptions) == 2 and resp.short_descriptions[0] != resp.short_descriptions[1]


def test_user_braces_and_symbols_are_safe():
    resp = PROVIDER.generate(make(product_name="Ring {x} %s", description="Great {detail} {0}."))
    assert "Ring {x} %s" in resp.captions[0].text


def test_audience_leading_for_is_not_duplicated():
    text = all_text(PROVIDER.generate(make(target_audience="for busy parents")))
    assert "for for" not in text.lower()


def test_ad_copy_fits_125_characters():
    resp = PROVIDER.generate(make(
        product_name="An extremely long product name that keeps going and going",
        offer="Buy two get one free on every single item in our store this week",
        tone="festive"))
    ad = next(p for p in resp.promos if p.kind == "ad")
    assert len(ad.text) <= 125


def test_does_not_invent_product_claims():
    text = all_text(PROVIDER.generate(make(description="", offer="", target_audience=""))).lower()
    for claim in ("handmade", "handcrafted", "organic", "award", "limited stock", "best-selling"):
        assert claim not in text


def test_long_description_is_clipped_to_whole_sentences():
    desc = "First sentence here. " + "Another sentence that is quite long and wordy. " * 10
    resp = PROVIDER.generate(make(description=desc))
    assert "First sentence here" in resp.captions[0].text
    assert len(resp.captions[0].text) < 700


# ---------- validation and registry ----------


def test_empty_product_name_rejected():
    with pytest.raises(ValidationError):
        CopyRequest(product_name="   ")


def test_whitespace_is_collapsed():
    assert CopyRequest(product_name="  Silver   Ring ").product_name == "Silver Ring"


def test_bad_tone_and_length_rejected():
    with pytest.raises(ValidationError):
        CopyRequest(product_name="x", tone="angry")
    with pytest.raises(ValidationError):
        CopyRequest(product_name="x" * 81)
    with pytest.raises(ValidationError):
        CopyRequest(product_name="x", description="y" * 601)


def test_unknown_provider_rejected_by_registry():
    with pytest.raises(AppError) as exc:
        get_provider("llm")
    assert exc.value.status_code == 400
