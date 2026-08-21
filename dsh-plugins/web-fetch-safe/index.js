import dns from "node:dns/promises";
import http from "node:http";
import https from "node:https";
import net from "node:net";

import { WebError } from "@deepseek-ai/dsh-web";
import ipaddr from "ipaddr.js";


export const name = "web-fetch-safe";
export const inject = ["web"];
export const SAFE_FETCH_PROVIDER_ID = "safe-http";

const REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);
const PUBLIC_RANGES = new Set(["unicast"]);


function fetchError(message, code = "WEB_PROVIDER_ERROR", cause) {
  return new WebError(message, code, cause === undefined ? undefined : { cause });
}


export function isPublicAddress(address) {
  if (!ipaddr.isValid(address)) return false;
  let parsed = ipaddr.parse(address);
  if (parsed.kind() === "ipv6" && parsed.isIPv4MappedAddress()) {
    parsed = parsed.toIPv4Address();
  }
  return PUBLIC_RANGES.has(parsed.range());
}


export function parseSafeURL(value) {
  let url;
  try {
    url = new URL(String(value));
  } catch (error) {
    throw fetchError(`Invalid fetch URL: ${String(value)}`, "WEB_FETCH_INVALID_URL", error);
  }
  if (!['http:', 'https:'].includes(url.protocol)) {
    throw fetchError("Only HTTP and HTTPS URLs may be fetched", "WEB_FETCH_INVALID_URL");
  }
  if (url.username || url.password) {
    throw fetchError("URLs containing credentials may not be fetched", "WEB_FETCH_INVALID_URL");
  }
  if (!url.hostname) {
    throw fetchError("Fetch URL has no hostname", "WEB_FETCH_INVALID_URL");
  }
  return url;
}


export async function resolvePublicAddress(url, resolver = dns.lookup) {
  const literalFamily = net.isIP(url.hostname);
  const records = literalFamily
    ? [{ address: url.hostname, family: literalFamily }]
    : await resolver(url.hostname, { all: true, verbatim: true });
  if (!Array.isArray(records) || records.length === 0) {
    throw fetchError(`No addresses resolved for ${url.hostname}`, "WEB_FETCH_BLOCKED_URL");
  }
  for (const record of records) {
    if (!record || !isPublicAddress(record.address)) {
      throw fetchError(
        `Fetch destination ${url.hostname} resolved to a blocked address`,
        "WEB_FETCH_BLOCKED_URL"
      );
    }
  }
  return records[0];
}


async function withinDeadline(operation, deadline, signal) {
  if (signal?.aborted) {
    throw fetchError("Web fetch aborted", "WEB_ABORTED", signal.reason);
  }
  const remaining = deadline - Date.now();
  if (remaining <= 0) {
    throw fetchError("Web fetch exceeded its elapsed-time limit", "WEB_FETCH_TIMEOUT");
  }
  let timer;
  let onAbort;
  const timeout = new Promise((_resolve, reject) => {
    timer = setTimeout(() => reject(fetchError(
      "Web fetch exceeded its elapsed-time limit", "WEB_FETCH_TIMEOUT"
    )), remaining);
  });
  const aborted = new Promise((_resolve, reject) => {
    onAbort = () => reject(fetchError("Web fetch aborted", "WEB_ABORTED", signal?.reason));
    signal?.addEventListener("abort", onAbort, { once: true });
  });
  try {
    return await Promise.race([operation, timeout, aborted]);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}


export function requestWithPinnedAddress(url, address, options, signal) {
  return new Promise((resolve, reject) => {
    const transport = url.protocol === "https:" ? https : http;
    let settled = false;
    let response;
    const chunks = [];
    let bytes = 0;
    let truncated = false;
    const finish = (callback) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      callback();
    };
    const complete = () => finish(() => resolve({
      statusCode: response?.statusCode ?? 0,
      headers: response?.headers ?? {},
      body: Buffer.concat(chunks),
      truncated,
    }));
    const request = transport.request({
      protocol: url.protocol,
      hostname: address.address,
      port: url.port || undefined,
      path: `${url.pathname}${url.search}`,
      method: "GET",
      headers: {
        accept: "text/html, application/xhtml+xml, text/plain;q=0.9",
        host: url.host,
        "user-agent": "Resource-Scout-Safe-Fetch/0.1",
      },
      servername: url.hostname,
    });
    const onAbort = () => {
      request.destroy();
      finish(() => reject(fetchError("Web fetch aborted", "WEB_ABORTED", signal?.reason)));
    };
    const timer = setTimeout(() => {
      request.destroy();
      finish(() => reject(fetchError(
        `Web fetch exceeded ${options.timeoutMs} ms`, "WEB_FETCH_TIMEOUT"
      )));
    }, options.timeoutMs);
    signal?.addEventListener("abort", onAbort, { once: true });
    request.on("response", incoming => {
      response = incoming;
      incoming.on("data", chunk => {
        if (settled) return;
        const buffer = Buffer.from(chunk);
        const remaining = options.maxBytes - bytes;
        if (buffer.length > remaining) {
          if (remaining > 0) chunks.push(buffer.subarray(0, remaining));
          bytes = options.maxBytes;
          truncated = true;
          complete();
          incoming.destroy();
          request.destroy();
          return;
        }
        chunks.push(buffer);
        bytes += buffer.length;
      });
      incoming.on("end", complete);
      incoming.on("error", error => {
        if (!settled) finish(() => reject(fetchError(
          `Web fetch response failed: ${error.message}`, "WEB_PROVIDER_ERROR", error
        )));
      });
    });
    request.on("error", error => {
      if (!settled) finish(() => reject(fetchError(
        `Web fetch request failed: ${error.message}`, "WEB_PROVIDER_ERROR", error
      )));
    });
    request.end();
  });
}


function decodedBody(headers, body) {
  const contentEncoding = String(headers["content-encoding"] || "").trim().toLowerCase();
  if (contentEncoding && contentEncoding !== "identity") {
    throw fetchError(
      `Unsupported response content encoding: ${contentEncoding}`,
      "WEB_FETCH_UNSUPPORTED_CONTENT"
    );
  }
  const rawType = String(headers["content-type"] || "").toLowerCase();
  const mediaType = rawType.split(";", 1)[0].trim();
  const charsetMatch = /charset\s*=\s*["']?([^;"'\s]+)/iu.exec(rawType);
  const charset = charsetMatch?.[1]?.toLowerCase() || "utf-8";
  let content;
  try {
    content = new TextDecoder(charset).decode(body);
  } catch (error) {
    throw fetchError(`Unsupported response character set: ${charset}`, "WEB_FETCH_UNSUPPORTED_CONTENT", error);
  }
  if (mediaType === "text/html" || mediaType === "application/xhtml+xml") {
    return { kind: "html", content };
  }
  if (mediaType === "text/plain") {
    return { kind: "text", content };
  }
  throw fetchError(
    `Unsupported response content type: ${mediaType || "missing"}`,
    "WEB_FETCH_UNSUPPORTED_CONTENT"
  );
}


export class SafeFetchProvider {
  id = SAFE_FETCH_PROVIDER_ID;

  constructor(options = {}) {
    this.timeoutMs = options.timeoutMs ?? 30000;
    this.maxBytes = options.maxBytes ?? 500000;
    this.maxRedirects = options.maxRedirects ?? 5;
    this.maxCalls = Math.max(1, Math.floor(Number(options.maxCalls) || 5));
    this.calls = 0;
    this.resolver = options.resolver ?? dns.lookup;
    this.requester = options.requester ?? requestWithPinnedAddress;
  }

  available() {
    return this.timeoutMs > 0 && this.maxBytes > 0 && this.maxRedirects >= 0;
  }

  async fetch(request, signal) {
    if (this.calls >= this.maxCalls) {
      throw fetchError(
        `Web fetch call limit of ${this.maxCalls} reached; synthesize the result now`,
        "WEB_CALL_LIMIT"
      );
    }
    this.calls += 1;
    let url = parseSafeURL(request.url);
    const deadline = Date.now() + this.timeoutMs;
    for (let redirects = 0; ; redirects += 1) {
      if (signal?.aborted) {
        throw fetchError("Web fetch aborted", "WEB_ABORTED", signal.reason);
      }
      let address;
      try {
        address = await withinDeadline(
          resolvePublicAddress(url, this.resolver), deadline, signal
        );
      } catch (error) {
        if (error instanceof WebError) throw error;
        throw fetchError(`Could not resolve ${url.hostname}: ${error.message}`, "WEB_PROVIDER_ERROR", error);
      }
      const response = await this.requester(
        url,
        address,
        { timeoutMs: Math.max(1, deadline - Date.now()), maxBytes: this.maxBytes },
        signal
      );
      const location = response.headers.location;
      if (REDIRECT_STATUSES.has(response.statusCode) && location) {
        if (redirects >= this.maxRedirects) {
          throw fetchError("Web fetch exceeded the redirect limit", "WEB_FETCH_REDIRECT_LIMIT");
        }
        url = parseSafeURL(new URL(String(location), url).href);
        continue;
      }
      return {
        url: url.href,
        statusCode: response.statusCode,
        body: decodedBody(response.headers, response.body),
        truncated: Boolean(response.truncated),
      };
    }
  }
}


export function apply(ctx, config = {}) {
  ctx.web.registerFetchProvider(new SafeFetchProvider(config));
}
