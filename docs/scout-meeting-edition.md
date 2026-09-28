# Deadline research checkpoint

`scripts/build_meeting_edition.py` produces a working HTML resource editor, a
printable overview and a research-draft resource ZIP from exact saved project
revisions. A pilot and continuation can be combined when their current office
package is identical. The database connection is read-only.

This path applies only fully researched and reconciled proposals. Unfinished
tasks never contribute partial results. Uncertain closure/identity findings,
blocked resources, already-exported rows and conflicts with newer office edits
remain held; original patron-facing text is retained and the overview identifies
the follow-up. Uncertain status also becomes an open question in the resource
editor; blocked or conflicting office edits are left untouched. No retirement or human approval is created. Resolved questions,
verification metadata and exact PDF bytes are preserved.

The HTML and ZIP contain the same resources. The ZIP is an uncurated research
draft for review or a demonstrated package import, not an office release.
Normal curator selection and package export remain available in the HTML.
The overview shows changed text in bold and prints either a short overview or
one selected resource. A visible checkpoint notice gives unfinished-work counts
without appearing on patron handouts.

Use an empty delivery directory. Supply each exact revision explicitly, for
example `--project 1:74 --project 2:1900`; obtain the actual saved revisions
before running. `--created-at` can reproduce an earlier timestamp. Stale
revisions, incompatible source packages or overlapping completed identities
fail rather than silently selecting a winner.

The existing strict completed-project builder and the research protocol are
unchanged. This delivery option does not mark research tasks complete, alter
sampling, activate lessons, or bypass any configured independent comparison.
