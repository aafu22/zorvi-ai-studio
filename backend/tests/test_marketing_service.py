"""AI Marketing Brain service tests. A fake client stands in for Gemini, so no API key or network is needed."""

import json

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.marketing import MarketingContent, MarketingRequest
from app.services.marketing import marketing_service as svc
from app.services.marketing.gemini_client import AiProviderError, _translate

GOOD = {
    "captions": ["Caption one about the ring", "A story about wearing it daily", "Which finger will you wear it on?"],
    "hashtags": ["#RoseRing", "#silverjewellery", "#minimal", "#giftideas", "#handmade", "#everyday"],
    "headlines": ["Meet the Rose Ring", "Quiet sparkle", "Silver, simply", "Wear it daily", "A small luxury"],
    "description": "A sterling silver ring with a rose quartz stone.",
    "ctas": ["Shop now", "See the ring", "Order today"],
    "promo": "Meet the Rose Ring. Sterling silver, rose quartz.",
    "ideas": ["Photo idea one.", "Video idea two.", "Question idea three."],
}


class FakeClient:
    model = "fake-model"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def generate_json(self, system, prompt, schema):
        self.calls.append((system, prompt, schema))
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)


def req(**kw):
    base = {"product_name": "Rose Ring", "description": "Sterling silver ring with a rose quartz stone."}
    return MarketingRequest(**{**base, **kw})


# ------------------------------------------------------------------ validation


def test_product_name_is_required():
    for bad in ({"product_name": ""}, {"product_name": "   "}):
        try:
            MarketingRequest(**bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should be rejected")


def test_defaults_and_whitespace_tidying():
    r = MarketingRequest(product_name="  Rose   Ring  ")
    assert r.product_name == "Rose Ring"
    assert (r.category, r.goal, r.platform, r.tone, r.section) == ("other", "sales", "instagram", "friendly", "all")


def test_unknown_choices_are_rejected():
    for bad in ({"tone": "angry"}, {"platform": "tiktok"}, {"goal": "world domination"}, {"section": "everything"}):
        try:
            req(**bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should be rejected")


# ------------------------------------------------------------------ happy path


def test_generate_returns_all_sections_labelled_as_ai():
    fake = FakeClient(GOOD)
    out = svc.generate_marketing(req(), client=fake)
    assert out.source.is_ai and out.source.id == "gemini" and out.source.model == "fake-model"
    c = out.content
    assert len(c.captions) == 3 and len(c.headlines) == 5 and len(c.ctas) == 3 and len(c.ideas) == 3
    assert c.description and c.promo and out.warnings == []
    assert len(fake.calls) == 1


def test_prompt_contains_brief_and_guardrails_but_no_secrets():
    fake = FakeClient(GOOD)
    svc.generate_marketing(req(tone="elegant", platform="whatsapp", goal="launch", target_audience="gift buyers"), client=fake)
    system, prompt, _ = fake.calls[0]
    assert "Rose Ring" in prompt and "gift buyers" in prompt and "elegant" in prompt and "WhatsApp" in prompt
    assert "Never invent" in system and "scarcity" in system
    assert "Offer: (not provided)" in prompt  # missing optional data is stated, not guessed


def test_hashtags_are_normalised_and_deduped():
    data = {**GOOD, "hashtags": ["rose ring", "#Rose Ring", "#silver!", "gift", "#GIFT", "a#b", "#x y z", "#more"]}
    out = svc.generate_marketing(req(), client=FakeClient(data))
    assert out.content.hashtags == ["#rosering", "#silver", "#gift", "#ab", "#xyz", "#more"]


def test_extra_items_are_trimmed_to_the_requested_count():
    data = {**GOOD, "captions": GOOD["captions"] + ["fourth"], "headlines": GOOD["headlines"] + ["sixth"]}
    c = svc.generate_marketing(req(), client=FakeClient(data)).content
    assert len(c.captions) == 3 and len(c.headlines) == 5


def test_single_section_regenerate_returns_only_that_section():
    fake = FakeClient({"headlines": ["A", "B", "C", "D", "E"]})
    out = svc.generate_marketing(req(section="headlines"), client=fake)
    assert out.section == "headlines" and out.content.headlines == list("ABCDE")
    assert out.content.captions is None and out.content.promo is None
    assert "[headlines]" in fake.calls[0][1] and "[captions]" not in fake.calls[0][1]


# ------------------------------------------------------------------ bad model output


def test_bad_output_is_retried_once_then_succeeds():
    fake = FakeClient("not json at all", GOOD)
    out = svc.generate_marketing(req(), client=fake)
    assert out.content.captions and len(fake.calls) == 2
    assert "unusable" in fake.calls[1][1]


def test_bad_output_twice_gives_a_clear_error():
    fake = FakeClient({**GOOD, "captions": ["only one"]})
    try:
        svc.generate_marketing(req(), client=fake)
    except AppError as exc:
        assert exc.status_code == 502 and "try again" in exc.detail.lower()
    else:
        raise AssertionError("expected AppError")
    assert len(fake.calls) == 2


def test_empty_description_is_rejected():
    try:
        svc.parse_content(json.dumps({**GOOD, "description": "  "}), "all")
    except svc.BadModelOutput:
        return
    raise AssertionError("expected BadModelOutput")


# ------------------------------------------------------------------ invented claims


def test_numbers_not_in_the_brief_are_flagged():
    data = {**GOOD, "promo": "Get 30% off today, only 3 left!"}
    out = svc.generate_marketing(req(), client=FakeClient(data))
    text = " ".join(out.warnings)
    assert '"30"' in text and '"3"' in text


def test_numbers_that_are_in_the_brief_are_fine():
    data = {**GOOD, "promo": "Enjoy 20% off the Rose Ring."}
    out = svc.generate_marketing(req(offer="20% off this weekend"), client=FakeClient(data))
    assert out.warnings == []


def test_risky_claims_are_flagged_unless_the_brief_has_them():
    data = {**GOOD, "description": "Our bestseller, loved in customer reviews."}
    warnings = svc.generate_marketing(req(), client=FakeClient(data)).warnings
    assert any("bestseller" in w for w in warnings) and any("reviews" in w for w in warnings)
    assert svc.check_claims(req(description="Our bestseller"), MarketingContent(description="A bestseller.")) == []


def test_a_clean_retry_replaces_a_flagged_first_answer():
    fake = FakeClient({**GOOD, "promo": "Only 3 left!"}, GOOD)
    out = svc.generate_marketing(req(), client=fake)
    assert out.warnings == [] and len(fake.calls) == 2
    assert "not in the brief" in fake.calls[1][1]


# ------------------------------------------------------------------ provider failures


def test_provider_errors_become_clear_app_errors():
    cases = {
        "auth": (502, "API key"), "rate_limit": (429, "rate limit"), "timeout": (504, "too long"),
        "unavailable": (502, "unavailable"), "bad_request": (502, "model"),
    }
    for kind, (status, fragment) in cases.items():
        fake = FakeClient(AiProviderError(kind, "Gemini does not know that model name."))
        try:
            svc.generate_marketing(req(), client=fake)
        except AppError as exc:
            assert exc.status_code == status and fragment.lower() in exc.detail.lower(), (kind, exc.detail)
        else:
            raise AssertionError(kind)
        assert len(fake.calls) == 1  # provider errors are not retried


def test_missing_api_key_is_explained(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    try:
        svc.generate_marketing(req())
    except AppError as exc:
        assert exc.status_code == 503 and "GEMINI_API_KEY" in exc.detail and "backend/.env" in exc.detail
    else:
        raise AssertionError("expected AppError")
    finally:
        get_settings.cache_clear()


class _SdkError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message)
        self.code, self.message = code, message


def test_sdk_errors_are_translated_without_leaking_details():
    assert _translate(_SdkError(429, "RESOURCE_EXHAUSTED")).kind == "rate_limit"
    assert _translate(_SdkError(400, "API key not valid. Please pass a valid API key.")).kind == "auth"
    assert _translate(_SdkError(403)).kind == "auth"
    assert _translate(_SdkError(404)).kind == "bad_request"
    assert _translate(_SdkError(503)).kind == "unavailable"
    assert _translate(_SdkError(504)).kind == "timeout"
    assert _translate(TimeoutError("boom")).kind == "timeout"
    assert _translate(RuntimeError("something odd")).kind == "unavailable"
    assert "AIza" not in _translate(_SdkError(400, "key AIzaSECRET invalid api key")).message


# ------------------------------------------------------------------ template fallback


def test_template_fallback_is_labelled_and_needs_no_key():
    out = svc.template_marketing(req(tone="elegant", offer="10% off"))
    assert out.source.id == "template" and out.source.is_ai is False
    assert "not AI" in out.source.label
    assert len(out.content.captions) == 3 and out.content.hashtags and out.content.description


def test_template_fallback_single_section():
    out = svc.template_marketing(req(section="ctas"))
    assert out.content.ctas and out.content.captions is None
