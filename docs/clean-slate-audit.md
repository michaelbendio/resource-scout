# Clean-slate audit

Status: completed for version 0.37.0.

The production path is package import, category guidance, chat-response collection,
parsing, consolidation, optional identity review, duplicate comparison, contact
lookup, Curator export, package creation, and private Tailscale access.

The following retired systems and their tests, scripts, service definitions,
schemas, and documentation were removed:

- model adapters and model-specific launchers;
- search and page-fetch agent plugins;
- staged research coordination and recovery;
- optimization, quantization comparison, benchmark, and frozen-report readers;
- trace consoles and message interception;
- prior-run lead recovery, referral-graph expansion, and qualification manifests;
- the automated research-lesson system;
- generated-resource and Scout-side review routes;
- source-package attachment serving; and
- batch research runners.

The macOS background service now starts only Resource Scout. The user interface has
one discovery path and one Curator handoff. New Curators use a clean versioned work
format and contain no compatibility outcome fields.

Static checks cover direct page event listeners so a removed control cannot leave a
dangling listener that prevents startup. The full retained test suite exercises the
current product path only.
