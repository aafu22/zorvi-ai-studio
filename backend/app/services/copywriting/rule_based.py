"""Template-based marketing copy. This is NOT AI.

Text is assembled from hand-written phrase banks plus the user's own product details,
chosen with a random number generator. It works offline with no API key. To keep it
honest, the templates avoid inventing product facts (materials, "handmade", awards,
scarcity). Anything specific in the output comes from what the user typed.
"""

import random
import re
import secrets
from dataclasses import dataclass

from app.schemas.copy import (
    CaptionItem,
    CopyRequest,
    CopyResponse,
    PromoItem,
    Tone,
)
from app.services.copywriting.base import provider_info

TONES: tuple[Tone, ...] = ("friendly", "professional", "luxury", "playful", "festive")

# {name}, {detail}, {aud} and {offer} are filled with the user's text via str.format.
# Only these banks are templates; user text is passed as arguments, so braces typed by
# the user are safe.
BANKS: dict[str, dict[str, tuple[str, ...]]] = {
    "friendly": {
        "hooks": (
            "Say hello to {name} ✨",
            "Meet {name}. We think you're going to love it 💛",
            "New in: {name}! 🎉",
            "Your next favourite is here: {name} 💫",
            "We couldn't wait to share {name} with you 😍",
        ),
        "details": ("{detail}.", "Here's the scoop: {detail}.", "What makes it special? {detail}."),
        "audiences": ("Perfect for {aud}.", "A great pick for {aud}."),
        "ctas": (
            "Tap the link in bio to shop 🛍️",
            "DM us to order 💌",
            "Tell us what you think in the comments 👇",
            "Save this for later and share it with a friend 🔖",
        ),
        "offers": ("Special offer: {offer} 🎁", "Treat yourself: {offer} 💝", "Offer: {offer} ✨"),
    },
    "professional": {
        "hooks": (
            "Introducing {name}.",
            "Now available: {name}.",
            "Presenting {name}.",
            "Announcing {name}.",
            "{name} is now available.",
        ),
        "details": ("{detail}.", "Key details: {detail}.", "At a glance: {detail}."),
        "audiences": ("Suited to {aud}.", "Ideal for {aud}."),
        "ctas": (
            "Visit the link in our bio to place an order.",
            "Send us a message for pricing and availability.",
            "Contact us to learn more.",
            "Order today through our profile link.",
        ),
        "offers": ("Current offer: {offer}.", "Offer details: {offer}.", "Take advantage of our offer: {offer}."),
    },
    "luxury": {
        "hooks": (
            "{name}. Refined in every detail.",
            "Elevate your everyday with {name}.",
            "Introducing {name}: understated elegance.",
            "{name}, a statement of quiet luxury.",
            "Discover {name}.",
        ),
        "details": ("{detail}.", "{detail}. A considered choice.", "Every element matters: {detail}."),
        "audiences": ("Curated for {aud}.", "For {aud} who appreciate the finer things."),
        "ctas": (
            "Discover more via the link in bio.",
            "Enquire by direct message.",
            "Explore the collection. Link in bio.",
            "Reserve yours today.",
        ),
        "offers": ("Exclusive offer: {offer}.", "Reserved for you: {offer}.", "Offer: {offer}."),
    },
    "playful": {
        "hooks": (
            "Plot twist: {name} just dropped 🙌",
            "Okay, we're obsessed with {name} 😍",
            "Warning: {name} may cause serious heart-eyes 😻",
            "{name} has entered the chat 💥",
            "Guess who's here? {name}! 🎈",
        ),
        "details": ("{detail}. Yes, really!", "The good stuff: {detail}.", "Why we're obsessed: {detail}."),
        "audiences": ("Calling all {aud}! 📣", "Hey {aud}, this one's for you 👋"),
        "ctas": (
            "Link in bio, go go go 🏃",
            "Slide into our DMs to order 📩",
            "Tag a friend who needs this 👯",
            "Don't sleep on it. Shop now 🛒",
        ),
        "offers": ("Psst… {offer} 🤫", "Treat yourself: {offer} 🎉", "Deal alert: {offer} 🚨"),
    },
    "festive": {
        "hooks": (
            "Celebrate in style with {name} 🎉",
            "The season of joy calls for {name} ✨",
            "Make every moment brighter with {name} 🎊",
            "{name}: a gift-worthy find 🎁",
            "Spread the joy with {name} 🎊",
        ),
        "details": ("{detail}.", "Here's what you'll love: {detail}.", "The details: {detail}."),
        "audiences": ("A lovely choice for {aud}.", "Bringing joy to {aud} 💝"),
        "ctas": (
            "Shop the festive picks via link in bio 🎁",
            "DM us to place your order 🎊",
            "Gift it to someone special 💝",
            "Tap the link in bio to celebrate 🎉",
        ),
        "offers": ("Festive offer: {offer} 🎁", "Celebrate with this offer: {offer} 🎊", "Offer: {offer} ✨"),
    },
}

HEADLINES: dict[str, str] = {
    "friendly": "Meet {name}",
    "professional": "Introducing {name}",
    "luxury": "Discover {name}",
    "playful": "Say hi to {name} 👋",
    "festive": "Celebrate with {name} 🎉",
}

SHORT_CTAS: dict[str, str] = {
    "friendly": "Shop now via link in bio.",
    "professional": "Order via the link in our bio.",
    "luxury": "Discover more via link in bio.",
    "playful": "Link in bio. Go go go!",
    "festive": "Shop the festive picks. Link in bio.",
}

GENERAL_CTAS = ("Shop now. Link in bio.", "Message us to order.")

# keyword (matched inside the lower-cased category) -> hashtags; first match wins
CATEGORY_TAGS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("candle", "fragrance"), ("#Candles", "#CandleLovers", "#CosyVibes", "#SelfCareRituals")),
    (("jewel", "accessor"), ("#Jewellery", "#JewelleryLovers", "#Accessories", "#StatementPiece")),
    (("beauty", "skin", "cosmetic", "makeup"), ("#Beauty", "#Skincare", "#SelfCare", "#GlowUp")),
    (("bag", "footwear", "shoe"), ("#BagLovers", "#Handbags", "#FashionAccessories", "#StyleEssentials")),
    (("fashion", "cloth", "apparel", "dress"), ("#Fashion", "#OOTD", "#StyleInspo", "#OutfitIdeas")),
    (("home", "decor"), ("#HomeDecor", "#InteriorStyling", "#HomeInspo", "#CosyHome")),
    (("food", "bak", "snack"), ("#Foodie", "#FoodLovers", "#TreatYourself", "#Delicious")),
    (("gift", "stationery", "art"), ("#GiftIdeas", "#Stationery", "#ArtLovers", "#CreativeLife")),
)
FALLBACK_CATEGORY_TAGS = ("#NewArrival", "#ShopNow", "#MustHave", "#TrendingNow")
GENERAL_TAGS = ("#SmallBusiness", "#ShopSmall", "#SupportSmallBusiness", "#InstagramShop")
STYLE_TAGS: dict[str, tuple[str, ...]] = {
    "minimal": ("#MinimalStyle", "#LessIsMore"),
    "luxury": ("#LuxuryLifestyle", "#Elegant"),
    "aesthetic": ("#Aesthetic", "#AestheticVibes"),
    "festive": ("#FestiveVibes", "#Celebrate"),
    "vibrant": ("#ColorPop", "#VibrantVibes"),
}
MAX_HASHTAGS = 15


@dataclass(frozen=True)
class Context:
    name: str
    category: str
    detail: str  # first sentence(s) of the description, no trailing punctuation
    audience: str  # without a leading "for"
    brand: str
    offer: str


def _clip(text: str, limit: int) -> str:
    """Keep whole sentences up to `limit` characters, then strip trailing punctuation."""
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for sentence in sentences:
        candidate = f"{out} {sentence}".strip()
        if len(candidate) > limit:
            break
        out = candidate
    if not out:  # first sentence alone is too long: cut at a word boundary
        cut = text[:limit].rsplit(" ", 1)[0]
        out = cut if cut else text[:limit]
    return out.rstrip(" .!?…,;:")


def _fit(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" .,;:-—")
    return f"{cut}…"


def _hashtag(text: str) -> str | None:
    words = re.findall(r"[^\W_]+", text)
    tag = "".join(w[:1].upper() + w[1:] for w in words)
    return f"#{tag}" if 3 <= len(tag) <= 30 else None


def _build_context(req: CopyRequest) -> Context:
    audience = re.sub(r"^(for|to)\s+", "", req.target_audience, flags=re.IGNORECASE)
    return Context(
        name=req.product_name,
        category=req.category,
        detail=_clip(req.description, 160),
        audience=audience,
        brand=req.brand_name,
        offer=req.offer.rstrip(" .!"),
    )


class RuleBasedProvider:
    id = "template"
    label = "Template-based (not AI-generated)"
    is_ai = False

    def generate(self, request: CopyRequest) -> CopyResponse:
        rng = random.Random(request.seed if request.seed is not None else secrets.randbits(31))
        ctx = _build_context(request)
        tone = request.tone
        return CopyResponse(
            provider=provider_info(self),
            captions=self._captions(ctx, tone, rng),
            hashtags=self._hashtags(ctx, request.style, rng),
            short_descriptions=self._short_descriptions(ctx),
            promos=self._promos(ctx, tone),
            ctas=self._ctas(tone),
        )

    # ------------------------------------------------------------------ captions
    def _caption(self, tone: str, ctx: Context, rng: random.Random, hook: str) -> str:
        bank = BANKS[tone]
        body: list[str] = []
        if ctx.detail:
            body.append(rng.choice(bank["details"]).format(detail=ctx.detail))
        if ctx.audience:
            body.append(rng.choice(bank["audiences"]).format(aud=ctx.audience))
        if ctx.offer:
            body.append(rng.choice(bank["offers"]).format(offer=ctx.offer))
        parts = [hook.format(name=ctx.name)]
        if body:
            parts.append(" ".join(body))
        parts.append(rng.choice(bank["ctas"]))
        return "\n\n".join(parts)

    def _captions(self, ctx: Context, tone: str, rng: random.Random) -> list[CaptionItem]:
        # Three captions in the chosen tone (distinct hooks), then one in each other tone.
        items = [
            CaptionItem(tone=tone, text=self._caption(tone, ctx, rng, hook))  # type: ignore[arg-type]
            for hook in rng.sample(BANKS[tone]["hooks"], 3)
        ]
        for other in TONES:
            if other != tone:
                hook = rng.choice(BANKS[other]["hooks"])
                items.append(CaptionItem(tone=other, text=self._caption(other, ctx, rng, hook)))
        return items

    # ------------------------------------------------------------------ hashtags
    def _hashtags(self, ctx: Context, style: str, rng: random.Random) -> list[str]:
        category_key = ctx.category.lower()
        category_tags = FALLBACK_CATEGORY_TAGS
        for keywords, tags in CATEGORY_TAGS:
            if any(k in category_key for k in keywords):
                category_tags = tags
                break

        ordered: list[str | None] = [
            _hashtag(ctx.brand) if ctx.brand else None,
            _hashtag(ctx.name),
            *rng.sample(category_tags, min(4, len(category_tags))),
            _hashtag(ctx.audience) if ctx.audience and len(ctx.audience.split()) <= 3 else None,
            *STYLE_TAGS[style],
            *rng.sample(GENERAL_TAGS, 3),
        ]
        seen: set[str] = set()
        result: list[str] = []
        for tag in ordered:
            if tag and tag.lower() not in seen:
                seen.add(tag.lower())
                result.append(tag)
        return result[:MAX_HASHTAGS]

    # ------------------------------------------------------------------ descriptions
    def _short_descriptions(self, ctx: Context) -> list[str]:
        by_brand = f" by {ctx.brand}" if ctx.brand else ""
        for_aud = f" for {ctx.audience}" if ctx.audience else ""
        category = ctx.category.lower()
        in_cat = f" in {category}" if category and category != "other" else ""

        first = (
            f"{ctx.name}{by_brand}: {ctx.detail}."
            if ctx.detail
            else f"{ctx.name}{by_brand}, now available{for_aud}."
        )
        second = f"Discover {ctx.name}{by_brand}{in_cat}."
        if ctx.detail:
            second += f" {ctx.detail}."
        if ctx.audience:
            second += f" Perfect for {ctx.audience}."
        if not ctx.detail and not ctx.audience:
            second += " Message us for details."
        return [first, second]

    # ------------------------------------------------------------------ promos / CTAs
    def _promos(self, ctx: Context, tone: str) -> list[PromoItem]:
        headline = (
            f"{ctx.name}: {ctx.offer}" if ctx.offer else HEADLINES[tone].format(name=ctx.name)
        )
        cta = SHORT_CTAS[tone]
        if ctx.offer:
            ad = f"{ctx.name}. {ctx.offer}. {cta}"
        else:
            for_aud = f" for {ctx.audience}" if ctx.audience else ""
            ad = f"{ctx.name}{for_aud}. {cta}"
            if len(ad) > 125:
                ad = f"{ctx.name}. {cta}"
        ad = _fit(ad, 125)

        story_lines = [
            ctx.brand,
            "Now available",
            ctx.name,
            ctx.offer or _clip(ctx.detail, 60),
            "Link in bio",
        ]
        story = "\n".join(line for line in story_lines if line)
        return [
            PromoItem(kind="headline", text=headline),
            PromoItem(kind="ad", text=ad),
            PromoItem(kind="story", text=story),
        ]

    def _ctas(self, tone: str) -> list[str]:
        ctas = list(BANKS[tone]["ctas"]) + list(GENERAL_CTAS)
        return list(dict.fromkeys(ctas))
