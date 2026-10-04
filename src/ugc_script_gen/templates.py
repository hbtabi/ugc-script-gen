"""Hook angles and script formats.

Every template is plain text with ``{placeholders}`` filled from the brief. Formats
are lists of beats; each beat has a relative weight (share of runtime), a shot
description, and line options for the voice-over and on-screen text.
"""

from __future__ import annotations

from dataclasses import dataclass

HOOKS: dict[str, list[str]] = {
    "problem": [
        "If {pain} is ruining your week, watch this.",
        "{Pain}? Yeah, me too. Until this.",
        "Stop scrolling if you're tired of {pain}.",
        "Nobody talks about how annoying {pain} actually is.",
    ],
    "curiosity": [
        "I didn't expect a {category} to fix {pain}.",
        "This tiny change fixed {pain} for me.",
        "The {category} {audience} keep gatekeeping.",
        "I tried {product} for 7 days. Here's what happened.",
    ],
    "pov": [
        "POV: you finally found a fix for {pain}.",
        "POV: you're one of the {audience} who stopped putting up with {pain}.",
    ],
    "social_proof": [
        "{proof}. I had to see why.",
        "There's a reason {product} has {proof_lower}.",
    ],
    "contrarian": [
        "Unpopular opinion: you don't need more products, you need {product}.",
        "Everything you've been told about {pain} is wrong.",
    ],
    "listicle": [
        "3 reasons {audience} are switching to {product}.",
        "3 things I wish I knew before trying {product}.",
    ],
    "before_after": [
        "Me before {product} vs. me after.",
        "Day 1 vs. day 14 with {product}.",
    ],
}

TONE_SIGNOFFS = {
    "casual": ["Honestly? Obsessed.", "Not sponsored energy, just genuinely love it.", "Ten out of ten, no notes."],
    "premium": ["Quietly the best thing I've bought this year.", "Small detail, big difference.", "Worth every penny."],
    "playful": ["My only regret is not finding it sooner.", "Main character energy, unlocked.", "Yes, I'm that friend now."],
    "clinical": ["The results speak for themselves.", "Simple, measurable, repeatable.", "Evidence over hype."],
}


@dataclass(frozen=True)
class Beat:
    name: str
    weight: float
    shot: str
    vo: tuple[str, ...]
    on_screen: tuple[str, ...]
    broll: str = ""
    drop: int = 0  # 0 = always kept; higher numbers are dropped first when the VO overruns


@dataclass(frozen=True)
class Format:
    key: str
    title: str
    description: str
    beats: tuple[Beat, ...]


def _b(name, weight, shot, vo, on_screen, broll="", drop=0):
    return Beat(name, weight, shot, tuple(vo), tuple(on_screen), broll, drop)


FORMATS: dict[str, Format] = {
    "problem_solution": Format(
        "problem_solution", "Problem → Solution",
        "Classic direct-response arc: name the pain, show the fix, prove it, ask.",
        (
            _b("hook", 0.12, "Selfie close-up, handheld, creator looks straight to lens", ["{hook}"], ["{hook_short}"]),
            _b("problem", 0.18, "Medium shot acting out the frustration", [
                "Every single time, {pain}. I'd tried everything.",
                "I was so done with {pain}. Nothing actually worked.",
            ], ["the struggle: {pain}"], "Quick cut of the problem in real life", drop=1),
            _b("solution", 0.28, "Product hero shot, then hands-on demo", [
                "Then I found {product} from {brand}. {usp_sentence}",
                "So I tried {product}. {usp_sentence}",
            ], ["{product}"], "Macro of product texture / UI / detail"),
            _b("benefits", 0.22, "Over-the-shoulder use in a real setting", [
                "Now {benefit_1}, and {benefit_2}.",
                "The difference? {Benefit_1}. Plus {benefit_2}.",
            ], ["✓ {benefit_1}", "✓ {benefit_2}"]),
            _b("proof", 0.08, "Screen recording of reviews or close-up of packaging", ["{proof_sentence}"], ["{proof}"], drop=2),
            _b("cta", 0.12, "Back to selfie, product held next to face", ["{offer_sentence}{cta}. {signoff}"], ["{cta_short}"]),
        ),
    ),
    "testimonial": Format(
        "testimonial", "Talking-head testimonial",
        "One creator, one honest story. Feels native, converts on trust.",
        (
            _b("hook", 0.12, "Tight selfie, natural window light", ["{hook}"], ["{hook_short}"]),
            _b("backstory", 0.22, "Creator sitting, casual framing, slight push-in", [
                "So, quick context: I'm one of those {audience} who deals with {pain}.",
                "Backstory: as one of the {audience}, {pain} was my daily reality.",
            ], ["me, 3 months ago"], drop=1),
            _b("discovery", 0.2, "Creator picks product up off a shelf/desk", [
                "A friend told me about {product} and I was sceptical. {usp_sentence}",
                "I kept seeing {brand} everywhere, so I caved. {usp_sentence}",
            ], ["{brand} {product}"]),
            _b("result", 0.26, "Cutaways of daily use, creator reacting", [
                "Two weeks in: {benefit_1}. And honestly, {benefit_2}.",
                "What changed? {Benefit_1}. That alone was worth it.",
            ], ["{benefit_1}"], "Daily-routine B-roll"),
            _b("cta", 0.2, "Selfie, holding product to camera", ["{offer_sentence}{cta}. {signoff}"], ["{cta_short}"]),
        ),
    ),
    "three_reasons": Format(
        "three_reasons", "3 reasons listicle",
        "Numbered on-screen list. High retention because viewers wait for #3.",
        (
            _b("hook", 0.12, "Creator holds up three fingers, product in other hand", ["{hook_listicle}"], ["3 reasons ↓"]),
            _b("reason_1", 0.22, "Demo shot #1", ["One: {benefit_1}."], ["1. {benefit_1}"]),
            _b("reason_2", 0.22, "Demo shot #2, different angle", ["Two: {benefit_2}."], ["2. {benefit_2}"]),
            _b("reason_3", 0.24, "Demo shot #3, payoff moment", ["And three, the big one: {benefit_3}."], ["3. {benefit_3}"]),
            _b("cta", 0.2, "Product hero on clean background, creator VO",
               ["{proof_sentence} {offer_sentence}{cta}.", "{offer_sentence}{cta}."], ["{cta_short}"]),
        ),
    ),
    "before_after": Format(
        "before_after", "Before / after",
        "Split-screen or jump-cut transformation. Visual proof first, words second.",
        (
            _b("hook", 0.12, "Split screen: before (left) / after (right)", ["{hook_before_after}"], ["before ➜ after"]),
            _b("before", 0.22, "Desaturated 'before' footage", [
                "This was me. {Pain}, every day.",
                "Before: {pain}. Constantly.",
            ], ["BEFORE"]),
            _b("switch", 0.18, "Snap-transition into product reveal", ["Then I switched to {product}. {usp_sentence}"],
               ["the switch"], drop=1),
            _b("after", 0.28, "Bright, saturated 'after' footage", [
                "After: {benefit_1}. And {benefit_2}.",
                "Now? {Benefit_1}. Totally different.",
            ], ["AFTER"], "Same location as 'before' for contrast"),
            _b("cta", 0.2, "Creator to camera", ["{offer_sentence}{cta}. {signoff}"], ["{cta_short}"]),
        ),
    ),
    "unboxing": Format(
        "unboxing", "Unboxing + first impressions",
        "ASMR-friendly reveal, then a fast first-use demo.",
        (
            _b("hook", 0.12, "Top-down: hands with sealed package", ["{hook}"], ["{hook_short}"]),
            _b("unbox", 0.22, "Top-down unboxing, crisp audio", [
                "Okay, {product} from {brand} just arrived. Look at this.",
                "Unboxing {product}. The packaging alone, wow.",
            ], ["unboxing {brand}"], "Macro details of packaging"),
            _b("first_use", 0.3, "First use, close-ups on the key moment", [
                "First impression: {usp_sentence_lower} I'm into it already.",
                "Trying it right now. {usp_sentence}",
            ], ["first use"]),
            _b("verdict", 0.18, "Creator reacting to camera", ["Verdict: {benefit_1}. Bye, {pain}."], ["verdict: ✓"], drop=1),
            _b("cta", 0.18, "Product beside the open box", ["{offer_sentence}{cta}."], ["{cta_short}"]),
        ),
    ),
}
