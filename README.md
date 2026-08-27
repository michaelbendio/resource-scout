# Resource Scout

Resource Scout turns resource leads gathered from several consumer chat products
into a consolidated candidate list and a portable Resource Curator. It is designed
for repeated use across TSO locations and resource categories.

Version 0.39.2 is a chat-discovery-only product. The former model-agent,
optimization, benchmark, trace, and teaching systems are not part of this codebase.

## Workflow

1. Connect an existing TSO Resources package. For the less common package-free
   workflow, choose **Research a location** alongside the package control.
2. Select a category and set up discovery.
3. Copy Scout's category- and location-specific assignment into ChatGPT, Grok,
   Claude, Perplexity, or another chat of your choice.
4. Paste each response into Scout. The first valid saved response starts the
   discovery. Scout preserves the submitted text and source label, parses the leads,
   and reports any response that needs correction.
5. Consolidate the leads. Scout collapses exact repetitions and clear same-program
   aliases, keeps genuinely uncertain identities separate, distinguishes providers
   and programs from directories and routing sources, and compares candidates with
   resources already in the package.
6. Finish discovery. Curator groups distinct programs under their organization so
   specialists can work through a large provider without doing record linkage.
7. For candidates without a website, export Scout's contact-search assignment,
   complete those searches, and return the results. Confirmed unavailable or
   unreachable entries are removed from the Curator candidate list; inconclusive
   searches become plain-language checklist items in Notes.
8. Export **Resource Curator**.

When a genuinely changed resource package is connected after a discovery has
finished, its run card offers **Reconcile with current package**. Scout preserves
the package used during discovery, compares the existing candidates with the new
package, omits only candidates supported as the same resource by an exact identity
plus exact website or address, and keeps weaker relationships for human review.
The replacement Curator uses the reconciled package as its additions-only base.

Scout is for discovery and consolidation. Resource Specialists perform the website
review, telephone interview, classification, editing, printing, and final package
decision in Curator.

## Resource Curator

Each Curator is a self-contained HTML file. It contains two resizable work areas:
**Editors** and **Notes**. Editors contains Categories, Resource, and For tabs.

The candidate's concise service summary initially fills Description. Available
phone, address, website, and other contact information fill their matching fields.
The specialist completes and corrects the resource, prints it for review, and marks
it **Ready for package** when satisfied.

**Save work** downloads a portable JSON checkpoint. **Save a resource package**
creates an additions-only ZIP containing currently ready resources. The ZIP can be
merged through TSO Resources. Curators created without a source package can save
work but cannot create a resource package.

## Run Scout

Python 3.10 or newer is required. Scout has no third-party Python dependency.

```sh
./run.sh
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

For private access from an iPad connected to the same Tailscale network:

```sh
./run-tailscale.sh --port 8767
```

The command prints the private address to open on the iPad.

## Background service on macOS

```sh
./background-service.sh install
./background-service.sh status
./background-service.sh restart
./background-service.sh logs
```

The service starts Scout with private Tailscale access. Uninstalling the service
does not remove Scout's database or logs.

## Data and privacy

The connected package is read without modifying the source ZIP. Scout stores an
immutable import snapshot, the chat responses pasted by the user, deterministic
consolidation records, contact-search results, and completed candidate records in
its local SQLite database. A Curator export contains only the selected completed
run, the fields needed for curation and package creation, limited package identity,
and plain-language provenance for source-only records.

## Tests

```sh
python3 -m unittest discover -s tests
```

The suite covers package import and duplicate indexing, category guidance,
response parsing, conservative consolidation, identity decisions, contact lookup,
Curator isolation and package creation, Tailscale behavior, background service
configuration, and Scout/Curator UI wiring.
