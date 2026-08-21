import assert from "node:assert/strict";
import { chmod, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  DDGSSearchProvider,
} from "../dsh-runtime/node_modules/@resource-scout/dsh-web-search-ddgs/index.js";


async function helper(source) {
  const directory = await mkdtemp(join(tmpdir(), "resource-scout-ddgs-"));
  const path = join(directory, "helper.mjs");
  await writeFile(path, source, "utf8");
  await chmod(path, 0o755);
  return path;
}


test("provider returns normalized helper output without an API key", async () => {
  const script = await helper(`
    process.stdin.resume();
    process.stdin.on("end", () => console.log(JSON.stringify({
      sources: [{url: "https://example.org/", title: "Example"}], truncated: false
    })));
  `);
  const provider = new DDGSSearchProvider({ python: process.execPath, helper: script });
  const result = await provider.search({ query: "local help", maxResults: 4 });
  assert.equal(result.sources[0].url, "https://example.org/");
  assert.equal(result.truncated, false);
});


test("provider accepts an empty result set", async () => {
  const script = await helper(`
    process.stdin.resume();
    process.stdin.on("end", () => console.log('{"sources":[],"truncated":false}'));
  `);
  const provider = new DDGSSearchProvider({ python: process.execPath, helper: script });
  assert.deepEqual(await provider.search({ query: "nothing" }), {
    sources: [], truncated: false,
  });
});


test("provider rejects malformed helper output", async () => {
  const script = await helper(`console.log("not json");`);
  const provider = new DDGSSearchProvider({ python: process.execPath, helper: script });
  await assert.rejects(provider.search({ query: "bad" }), /returned invalid JSON/);
});


test("provider enforces its timeout", async () => {
  const script = await helper(`setInterval(() => {}, 1000);`);
  const provider = new DDGSSearchProvider({
    python: process.execPath, helper: script, timeoutMs: 25,
  });
  await assert.rejects(provider.search({ query: "slow" }), /exceeded 25 ms/);
});


test("provider honors cancellation", async () => {
  const script = await helper(`setInterval(() => {}, 1000);`);
  const provider = new DDGSSearchProvider({
    python: process.execPath, helper: script, timeoutMs: 5000,
  });
  const controller = new AbortController();
  const pending = provider.search({ query: "cancel" }, controller.signal);
  controller.abort("test cancellation");
  await assert.rejects(pending, /DDGS search aborted/);
});


test("provider enforces a deterministic per-run search call limit", async () => {
  const script = await helper(`
    process.stdin.resume();
    process.stdin.on("end", () => console.log('{"sources":[],"truncated":false}'));
  `);
  const provider = new DDGSSearchProvider({
    python: process.execPath, helper: script, maxCalls: 2,
  });
  await provider.search({ query: "one" });
  await provider.search({ query: "two" });
  await assert.rejects(provider.search({ query: "three" }), /call limit of 2 reached/);
});
