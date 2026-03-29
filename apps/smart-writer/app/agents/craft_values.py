"""Designer craft / hygiene value templates (stable value_ids, versioned copy in git)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.models import (
    DIMENSIONS_PER_VALUE,
    RubricDimension,
    ValueDefinition,
    ValueRubric,
)

CRAFT_RUBRIC_VERSION = "2026-03-29"


@dataclass(frozen=True)
class CraftTemplate:
    """One craft row: stable ids, default raw weight, and full rubric text."""

    craft_key: str
    value_id: str
    default_raw_weight: float
    name: str
    description: str
    rubric: ValueRubric


def _dim(
    name: str,
    desc: str,
    s1: str,
    s2: str,
    s3: str,
    s4: str,
    s5: str,
) -> RubricDimension:
    return RubricDimension(
        name=name,
        description=desc,
        score_1=s1,
        score_2=s2,
        score_3=s3,
        score_4=s4,
        score_5=s5,
    )


def _rubric_grammar(value_id: str) -> ValueRubric:
    return ValueRubric(
        value_id=value_id,
        value_name="Grammar & mechanics",
        dimensions=[
            _dim(
                "Spelling",
                "Correct spelling of common and domain terms.",
                "Many errors obscure meaning.",
                "Noticeable errors.",
                "Minor slips only.",
                "Consistently correct.",
                "Publication-clean spelling.",
            ),
            _dim(
                "Punctuation & syntax",
                "Fragments, run-ons, or punctuation errors impede reading.",
                "Frequent issues.",
                "Occasional issues.",
                "Mostly clean.",
                "Clean with rare slips.",
                "Fluent, precise syntax.",
            ),
            _dim(
                "Agreement & word forms",
                "Subject–verb, tense, or agreement errors distract.",
                "Several errors.",
                "Some errors.",
                "Few issues.",
                "Rare issues.",
                "Fully consistent.",
            ),
            _dim(
                "Capitalization & formatting",
                "Inconsistent or incorrect caps / formatting.",
                "Poor.",
                "Mixed.",
                "Acceptable.",
                "Mostly right.",
                "Professional consistency.",
            ),
            _dim(
                "Proofreading polish",
                "Reads unrevised or error-strewn.",
                "Weak.",
                "Adequate.",
                "Solid.",
                "Strong.",
                "Impeccable surface quality.",
            ),
        ],
    )


def _rubric_clarity(value_id: str) -> ValueRubric:
    return ValueRubric(
        value_id=value_id,
        value_name="Clarity & coherence",
        dimensions=[
            _dim(
                "Sentence clarity",
                "Sentences are hard to parse or ambiguous.",
                "Often unclear.",
                "Sometimes unclear.",
                "Mixed clarity.",
                "Mostly clear.",
                "Crisp, unambiguous sentences.",
            ),
            _dim(
                "Logical flow",
                "Ideas jump without bridges; reader gets lost.",
                "Disjointed.",
                "Uneven flow.",
                "Improving flow.",
                "Reasonable flow.",
                "Smooth, logical progression.",
            ),
            _dim(
                "Cohesion",
                "Paragraphs feel stapled together.",
                "Weak links.",
                "Some cohesion.",
                "Moderate cohesion.",
                "Good cohesion.",
                "Tight, unified narrative.",
            ),
            _dim(
                "Precision",
                "Vague claims or filler instead of concrete sense.",
                "Very vague.",
                "Somewhat vague.",
                "Mixed precision.",
                "Moderately precise.",
                "Sharp and specific.",
            ),
            _dim(
                "Reader effort",
                "Reader must re-read or guess intent.",
                "High effort.",
                "Moderate effort.",
                "Manageable effort.",
                "Low effort.",
                "Effortless to follow.",
            ),
        ],
    )


def _rubric_structure(value_id: str) -> ValueRubric:
    return ValueRubric(
        value_id=value_id,
        value_name="Structure & length fit",
        dimensions=[
            _dim(
                "Macro structure",
                "No discernible intro/body/conclusion or wrong shape for genre.",
                "Absent.",
                "Weak.",
                "Emerging shape.",
                "Adequate.",
                "Strong rhetorical shape.",
            ),
            _dim(
                "Paragraphing",
                "Blocks are too long/short; topic sentences missing.",
                "Poor.",
                "Mixed.",
                "Uneven.",
                "Acceptable.",
                "Disciplined paragraphing.",
            ),
            _dim(
                "Headings & signposting",
                "If expected, missing or confusing navigation cues.",
                "Missing/confusing.",
                "Sparse.",
                "Partial cues.",
                "Helpful.",
                "Clear, professional signposting.",
            ),
            _dim(
                "Length vs brief",
                "Clearly off brief (too long/short vs stated goal).",
                "Way off.",
                "Somewhat off.",
                "Approaching fit.",
                "Close to brief.",
                "Well calibrated to brief.",
            ),
            _dim(
                "Pacing",
                "Rushed endings, bloated middles, or uneven emphasis.",
                "Broken pacing.",
                "Uneven.",
                "Choppy.",
                "Okay.",
                "Balanced pacing.",
            ),
        ],
    )


def _rubric_register(value_id: str) -> ValueRubric:
    return ValueRubric(
        value_id=value_id,
        value_name="Diction & register",
        dimensions=[
            _dim(
                "Tone fit",
                "Tone clashes with audience or genre (too casual/formal).",
                "Misfire.",
                "Shaky.",
                "Uneven fit.",
                "Mostly fit.",
                "Assured tone.",
            ),
            _dim(
                "Word choice",
                "Jargon misuse, clichés, or vague intensifiers dominate.",
                "Poor diction.",
                "Mixed.",
                "Adequate.",
                "Competent.",
                "Precise, fresh wording.",
            ),
            _dim(
                "Consistency",
                "Shifts in person, tense, or voice without purpose.",
                "Inconsistent.",
                "Some drift.",
                "Mostly stable.",
                "Mostly steady.",
                "Controlled voice.",
            ),
            _dim(
                "Inclusivity & sensitivity",
                "Alienating or careless phrasing for intended readers.",
                "Problematic.",
                "Risky spots.",
                "Mostly okay.",
                "Generally fine.",
                "Considerate, professional.",
            ),
            _dim(
                "Concision",
                "Padding, redundancy, or throat-clearing weakens impact.",
                "Verbose.",
                "Some bloat.",
                "Moderate trim.",
                "Reasonably tight.",
                "Lean and purposeful.",
            ),
        ],
    )


# Canonical inventory (design §4.3.1) — single source for ids and keys.
_CRAFT_SPECS: list[tuple[str, str, float, str, str, object]] = [
    (
        "grammar_mechanics",
        "CRAFT_GRAMMAR",
        1.0,
        "Grammar & mechanics",
        "Spelling, grammar, punctuation, and basic surface correctness.",
        _rubric_grammar,
    ),
    (
        "clarity_coherence",
        "CRAFT_CLARITY",
        1.0,
        "Clarity & coherence",
        "Sentence clarity, flow, and coherence across the draft.",
        _rubric_clarity,
    ),
    (
        "structure_length",
        "CRAFT_STRUCTURE",
        1.0,
        "Structure & length fit",
        "Structure, headings where appropriate, and fit to stated length/brief.",
        _rubric_structure,
    ),
    (
        "diction_register",
        "CRAFT_REGISTER",
        1.0,
        "Diction & register",
        "Tone, register, and word choice suited to audience and task.",
        _rubric_register,
    ),
]


def default_craft_keys() -> list[str]:
    return [s[0] for s in _CRAFT_SPECS]


def build_craft_template(craft_key: str) -> CraftTemplate:
    for spec in _CRAFT_SPECS:
        if spec[0] == craft_key:
            key, vid, w, title, desc, factory = spec
            rub = factory(vid)
            if len(rub.dimensions) != DIMENSIONS_PER_VALUE:
                raise RuntimeError(f"Craft rubric {vid} must have {DIMENSIONS_PER_VALUE} dimensions.")
            vd = ValueDefinition(
                value_id=vid,
                name=title,
                description=desc,
                raw_weight=w,
                craft_key=key,
            )
            return CraftTemplate(
                craft_key=key,
                value_id=vid,
                default_raw_weight=w,
                name=title,
                description=desc,
                rubric=rub,
            )
    raise KeyError(f"Unknown craft_key: {craft_key!r}")


def craft_value_definition(craft_key: str) -> ValueDefinition:
    """Template row without final ``weight`` (filled by compose_values)."""
    t = build_craft_template(craft_key)
    return ValueDefinition(
        value_id=t.value_id,
        name=t.name,
        description=t.description,
        raw_weight=t.default_raw_weight,
        craft_key=t.craft_key,
    )


def craft_rubric_for_value_id(value_id: str) -> ValueRubric:
    for spec in _CRAFT_SPECS:
        if spec[1] == value_id:
            return spec[5](value_id)
    raise KeyError(f"Unknown craft value_id: {value_id!r}")
