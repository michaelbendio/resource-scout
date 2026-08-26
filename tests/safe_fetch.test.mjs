import assert from "node:assert/strict";
import http from "node:http";
import test from "node:test";

import {
  SafeFetchProvider,
  isPublicAddress,
  parseSafeURL,
  requestWithPinnedAddress,
} from "../dsh-runtime/node_modules/@resource-scout/dsh-web-fetch-safe/index.js";


const publicResolver = async () => [{ address: "93.184.216.34", family: 4 }];


async function localServer(handler) {
  const server = http.createServer(handler);
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  return {
    server,
    url: new URL(`http://fetch-test.invalid:${port}/`),
    address: { address: "127.0.0.1", family: 4 },
  };
}


test("address policy allows public unicast and blocks local and special ranges", () => {
  assert.equal(isPublicAddress("93.184.216.34"), true);
  for (const address of [
    "127.0.0.1", "10.0.0.1", "169.254.169.254", "192.168.1.1",
    "0.0.0.0", "224.0.0.1", "::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1",
  ]) assert.equal(isPublicAddress(address), false, address);
});


test("URL policy rejects credentials and unsupported protocols", () => {
  assert.throws(() => parseSafeURL("file:///etc/passwd"), /Only HTTP and HTTPS/);
  assert.throws(() => parseSafeURL("https://user:secret@example.org/"), /credentials/);
  assert.equal(parseSafeURL("https://example.org/help").hostname, "example.org");
});


test("provider returns bounded HTML with final URL and status", async () => {
  const provider = new SafeFetchProvider({
    resolver: publicResolver,
    requester: async () => ({
      statusCode: 200,
      headers: { "content-type": "text/html; charset=utf-8" },
      body: Buffer.from("<main><h1>Help</h1><p>Call first"),
      truncated: true,
    }),
  });
  const result = await provider.fetch({ url: "https://example.org/help" });
  assert.equal(result.url, "https://example.org/help");
  assert.equal(result.statusCode, 200);
  assert.equal(result.body.kind, "html");
  assert.match(result.body.content, /Call first/);
  assert.equal(result.truncated, true);
});


test("every redirect destination is resolved and private redirects are rejected", async () => {
  let requests = 0;
  const provider = new SafeFetchProvider({
    resolver: async hostname => hostname === "public.example"
      ? [{ address: "93.184.216.34", family: 4 }]
      : [{ address: "127.0.0.1", family: 4 }],
    requester: async () => {
      requests += 1;
      return {
        statusCode: 302,
        headers: { location: "http://localhost/admin", "content-type": "text/plain" },
        body: Buffer.alloc(0),
        truncated: false,
      };
    },
  });
  await assert.rejects(
    provider.fetch({ url: "https://public.example/start" }), /blocked address/
  );
  assert.equal(requests, 1);
});


test("ordinary public redirects are followed", async () => {
  const seen = [];
  const provider = new SafeFetchProvider({
    resolver: publicResolver,
    requester: async url => {
      seen.push(url.href);
      if (seen.length === 1) return {
        statusCode: 301,
        headers: { location: "/final", "content-type": "text/plain" },
        body: Buffer.alloc(0),
        truncated: false,
      };
      return {
        statusCode: 200,
        headers: { "content-type": "text/plain" },
        body: Buffer.from("finished"),
        truncated: false,
      };
    },
  });
  const result = await provider.fetch({ url: "https://example.org/start" });
  assert.deepEqual(seen, ["https://example.org/start", "https://example.org/final"]);
  assert.equal(result.url, "https://example.org/final");
  assert.equal(result.body.content, "finished");
});


test("mixed public and private DNS answers fail closed against rebinding", async () => {
  const provider = new SafeFetchProvider({
    resolver: async () => [
      { address: "93.184.216.34", family: 4 },
      { address: "10.0.0.5", family: 4 },
    ],
    requester: async () => { throw new Error("must not connect"); },
  });
  await assert.rejects(provider.fetch({ url: "https://example.org/" }), /blocked address/);
});


test("DNS resolution is covered by the elapsed timeout", async () => {
  const provider = new SafeFetchProvider({
    timeoutMs: 25,
    resolver: async () => await new Promise(() => {}),
    requester: async () => { throw new Error("must not connect"); },
  });
  await assert.rejects(provider.fetch({ url: "https://example.org/" }), /elapsed-time limit/);
});


test("provider rejects unsupported content types", async () => {
  const provider = new SafeFetchProvider({
    resolver: publicResolver,
    requester: async () => ({
      statusCode: 200,
      headers: { "content-type": "application/pdf" },
      body: Buffer.from("%PDF"),
      truncated: false,
    }),
  });
  await assert.rejects(provider.fetch({ url: "https://example.org/file.pdf" }), /content type/);
});


test("provider rejects compressed bodies it cannot safely bound after decoding", async () => {
  const provider = new SafeFetchProvider({
    resolver: publicResolver,
    requester: async () => ({
      statusCode: 200,
      headers: { "content-type": "text/html", "content-encoding": "gzip" },
      body: Buffer.from("compressed bytes"),
      truncated: false,
    }),
  });
  await assert.rejects(provider.fetch({ url: "https://example.org/compressed" }), /content encoding/);
});


test("provider accepts malformed HTML as bounded source text", async () => {
  const provider = new SafeFetchProvider({
    resolver: publicResolver,
    requester: async () => ({
      statusCode: 200,
      headers: { "content-type": "text/html" },
      body: Buffer.from("<div><p>Still readable"),
      truncated: false,
    }),
  });
  const result = await provider.fetch({ url: "https://example.org/broken" });
  assert.equal(result.body.content, "<div><p>Still readable");
});


test("pinned request truncates an oversized response", async t => {
  const local = await localServer((_request, response) => {
    response.setHeader("content-type", "text/plain");
    response.end("x".repeat(1000));
  });
  t.after(() => local.server.close());
  const result = await requestWithPinnedAddress(
    local.url, local.address, { timeoutMs: 1000, maxBytes: 32 }
  );
  assert.equal(result.body.length, 32);
  assert.equal(result.truncated, true);
});


test("pinned request enforces elapsed timeout", async t => {
  const local = await localServer(() => {});
  t.after(() => local.server.close());
  await assert.rejects(
    requestWithPinnedAddress(local.url, local.address, { timeoutMs: 25, maxBytes: 100 }),
    /exceeded 25 ms/
  );
});


test("pinned request honors cancellation", async t => {
  const local = await localServer(() => {});
  t.after(() => local.server.close());
  const controller = new AbortController();
  const pending = requestWithPinnedAddress(
    local.url, local.address, { timeoutMs: 1000, maxBytes: 100 }, controller.signal
  );
  controller.abort("test cancellation");
  await assert.rejects(pending, /Web fetch aborted/);
});


test("provider enforces a deterministic per-run fetch call limit", async () => {
  const provider = new SafeFetchProvider({
    maxCalls: 2,
    resolver: publicResolver,
    requester: async () => ({
      statusCode: 200,
      headers: { "content-type": "text/plain" },
      body: Buffer.from("ok"),
      truncated: false,
    }),
  });
  await provider.fetch({ url: "https://example.org/one" });
  await provider.fetch({ url: "https://example.org/two" });
  await assert.rejects(
    provider.fetch({ url: "https://example.org/three" }), /call limit of 2 reached/
  );
});


test("provider traces one fetch request and its linked response", { concurrency: false }, async () => {
  const originalFetch = globalThis.fetch;
  const originalEndpoint = process.env.RESOURCE_SCOUT_TRACE_ENDPOINT;
  const originalTraceId = process.env.RESOURCE_SCOUT_TRACE_ID;
  const events = [];
  process.env.RESOURCE_SCOUT_TRACE_ENDPOINT = "http://trace.invalid";
  process.env.RESOURCE_SCOUT_TRACE_ID = "stage-test";
  globalThis.fetch = async (_url, options) => {
    const event = JSON.parse(options.body);
    events.push(event);
    return new Response(JSON.stringify({ ok: true, event: { id: `event-${events.length}` } }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };
  try {
    const provider = new SafeFetchProvider({
      resolver: publicResolver,
      requester: async () => ({
        statusCode: 200,
        headers: { "content-type": "text/plain" },
        body: Buffer.from("ok"),
        truncated: false,
      }),
    });
    await provider.fetch({ url: "https://example.org/help" });
  } finally {
    globalThis.fetch = originalFetch;
    if (originalEndpoint === undefined) delete process.env.RESOURCE_SCOUT_TRACE_ENDPOINT;
    else process.env.RESOURCE_SCOUT_TRACE_ENDPOINT = originalEndpoint;
    if (originalTraceId === undefined) delete process.env.RESOURCE_SCOUT_TRACE_ID;
    else process.env.RESOURCE_SCOUT_TRACE_ID = originalTraceId;
  }
  assert.deepEqual(events.map(event => event.kind), ["fetch-request", "fetch-response"]);
  assert.equal(events[0].traceId, "stage-test");
  assert.equal(events[1].replyTo, "event-1");
});
