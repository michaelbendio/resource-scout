# Draft filing under the proposed standard vocabulary

You are filing real resources from TSO offices under
a **proposed** standard vocabulary: 18 categories, their subcategories, and 19 For groups.
It is a draft for a prototype that Elder Bendio and Stephanie will try out to decide the
final vocabulary. Honest "doesn't fit" answers are as valuable as fits: they are how the
standard learns.

Read `standard.json` (same folder as this brief) first. It has each category's definition
and subcategories, and each group's "who belongs" and "a resource counts when".

## For each resource, decide

1. **categories** (1, at most 2): the category ids that are its **main service**, not
   services it mentions among others. Two only when both are genuinely its main service.
   Settled rules:
   - Shelters: both `housing` (Emergency shelter) and `homeless-services` (Emergency shelter).
   - A soup kitchen: `food` (Meals) and `homeless-services` (Meals) when it serves homeless people.
   - SNAP/WIC: `food` (Food benefits); add `filing-assistance` (Food benefits) only when
     helping people apply is also a main service.
   - Protective orders: `legal` (Family law) and `domestic-violence` (Protective orders).
   - Eviction defense: `legal` and `housing` (Eviction prevention).
   - Substance use main service is `addiction`; treating both equally is both.
   - Rent and deposit help is `housing`; utility bills are `utilities`; money skills are
     `education`; tax preparation is `filing-assistance`.
   - A trade school is `education`; training for a specific job or placement is `employment`.
   - Seniors, veterans, disability, immigration, reentry, children and pregnancy are **not
     categories**: file by the kind of help and add the group.
   - Pet shelter is `housing` with the group Pet owners; pet food is `food` (Pet food).
2. **subcategories**: for each chosen category that has subcategories, the ones that
   fit (usually 1-2), using the exact labels in `standard.json`. Empty list if none fits.
3. **groups**: group ids the resource **targets or supports** by the "counts" test, each
   with `only: true` when a person must belong to the group to be helped (e.g. Veterans
   only, Women only). Be sparing: most resources have none or one or two.
4. **navigator**: true when it is a tool for finding help elsewhere (211, findhelp.org,
   a resource directory, a help-finder line) rather than a provider. Navigators get
   `categories: []` unless they are specific to one category (FindTreatment.gov:
   `["addiction"]`).
5. **serves**: where the service is offered, as a fact about the resource:
   `{"level": "national"}`, `{"level": "state", "state": "UT"}`, or
   `{"level": "local", "counties": ["Weber"], "state": "UT"}` (best judgement from address
   and text; counties without the word "County").
6. **restriction**: plain words for a place-based eligibility limit, e.g. "Provo residents
   only", "Utah residents only"; empty string when anyone may use it.
7. **missionariesOnly**: true only when the text says it is for missionaries' internal
   use or must not be given to the people they interview.
8. **noFit**: when no category or subcategory fits well, a short note of what is missing
   (e.g. "short-term lodging", "refugee resettlement"); otherwise empty string.
9. **note**: at most 15 words when the filing needed a judgement worth showing a
   reviewer (e.g. "Old category Housing; main service is addiction treatment"). Usually "".

## Output

Write a JSON array to the output path you were given, one object per input resource, in
input order:

```json
{"id": "...", "categories": ["housing", "homeless-services"],
 "subcategories": {"housing": ["Emergency shelter"], "homeless-services": ["Emergency shelter", "Meals"]},
 "groups": [{"id": "families", "only": false}],
 "navigator": false, "serves": {"level": "local", "state": "UT", "counties": ["Weber"]},
 "restriction": "", "missionariesOnly": false, "noFit": "", "note": ""}
```

Use only ids and labels from `standard.json`. Every input id must appear exactly once.
Validate the file parses as JSON before you finish (e.g. `python3 -c "import json;
json.load(open(PATH))"`), and report only the count written and any problems.
