"""The four office-fit rules, shared by research, curation and review.

Michael, 28 September 2026. The measure of a resource is whether a missionary would
hand it to someone across the desk, not how many resources Scout finds. His random
sample of 20 Food resources from the complete Mesa delivery passed 4. The rules are
written relative to the office, so they apply to every office unchanged; nothing in
them is Mesa-specific. They are Scout's policy, not an experiment (Michael, same day).
"""
from __future__ import annotations

OFFICE_FIT_VERSION = "office-fit-2026-09-28-v2"

OFFICE_FIT_RULES = (
    "Reach from the office: an in-person service must be in, or reasonably reachable from, the office's own "
    "city or service area. A countywide or statewide front door (coordinated entry, a hotline that is the real "
    "way in, a shelter at a confidential site) passes wherever its office is, because it is the actual route. "
    "A service reached by phone or online passes when the office's residents can use it. "
    "A program limited to residents of another city or area fails.",
    "Main service: place a resource in a category only when that category is its main service, not a service "
    "it mentions among others.",
    "Direct contact: a person must be able to contact or apply to it themselves. A program reached only by "
    "referral from a hospital, caseworker, child welfare or a health plan, or open only to people already "
    "enrolled elsewhere, fails; name the front door the person can reach instead.",
    "One entry per agency, unless its programs differ in a way a client would notice: a different phone "
    "number, intake or eligibility.",
)


def office_fit_lines(prefix: str) -> list[str]:
    """The rules as prompt lines under a stage-specific lead-in."""
    return [prefix, *(f"{n}. {rule}" for n, rule in enumerate(OFFICE_FIT_RULES, 1))]
