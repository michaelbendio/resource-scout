import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { WebError } from "@deepseek-ai/dsh-web";


export const name = "web-search-ddgs";
export const inject = ["web"];
export const DDGS_PROVIDER_ID = "ddgs";

const helper = fileURLToPath(new URL("./search.py", import.meta.url));


function pythonExecutable() {
  return process.env.RESOURCE_SCOUT_DDGS_PYTHON?.trim() || "python3";
}


export class DDGSSearchProvider {
  id = DDGS_PROVIDER_ID;

  constructor(options = {}) {
    this.timeoutMs = options.timeoutMs ?? 60000;
    this.maxCalls = Math.max(1, Math.floor(Number(options.maxCalls) || 2));
    this.calls = 0;
    this.python = options.python ?? pythonExecutable();
    this.helper = options.helper ?? helper;
  }

  available() {
    return Boolean(this.python) && existsSync(this.helper);
  }

  async search(request, signal) {
    if (signal?.aborted) {
      throw new WebError("DDGS search aborted", "WEB_ABORTED", { cause: signal.reason });
    }
    if (this.calls >= this.maxCalls) {
      throw new WebError(
        `DDGS search call limit of ${this.maxCalls} reached; synthesize the result now`,
        "WEB_CALL_LIMIT"
      );
    }
    this.calls += 1;
    const maxResults = Math.max(1, Math.min(Number(request.maxResults) || 8, 20));
    return await new Promise((resolve, reject) => {
      const child = spawn(this.python, [this.helper], {
        stdio: ["pipe", "pipe", "pipe"],
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
      });
      let stdout = "";
      let stderr = "";
      let settled = false;

      const finish = (callback) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        signal?.removeEventListener("abort", onAbort);
        callback();
      };
      const onAbort = () => {
        child.kill("SIGTERM");
        finish(() => reject(new WebError("DDGS search aborted", "WEB_ABORTED", {
          cause: signal?.reason,
        })));
      };
      const timer = setTimeout(() => {
        child.kill("SIGTERM");
        finish(() => reject(new WebError(
          `DDGS search exceeded ${this.timeoutMs} ms`, "WEB_PROVIDER_ERROR"
        )));
      }, this.timeoutMs);

      signal?.addEventListener("abort", onAbort, { once: true });
      child.stdout.setEncoding("utf8");
      child.stderr.setEncoding("utf8");
      child.stdout.on("data", chunk => { stdout += chunk; });
      child.stderr.on("data", chunk => { stderr += chunk; });
      child.on("error", error => finish(() => reject(new WebError(
        `Could not start DDGS search: ${error.message}`, "WEB_PROVIDER_ERROR", { cause: error }
      ))));
      child.on("close", code => finish(() => {
        if (code !== 0) {
          reject(new WebError(
            `DDGS search failed: ${stderr.trim() || `exit code ${code}`}`,
            "WEB_PROVIDER_ERROR"
          ));
          return;
        }
        try {
          const result = JSON.parse(stdout);
          if (!Array.isArray(result.sources) || typeof result.truncated !== "boolean") {
            throw new Error("response has the wrong shape");
          }
          resolve(result);
        } catch (error) {
          reject(new WebError(
            `DDGS search returned invalid JSON: ${error.message}`,
            "WEB_PROVIDER_ERROR",
            { cause: error }
          ));
        }
      }));
      child.stdin.end(JSON.stringify({ query: String(request.query || ""), maxResults }));
    });
  }
}


export function apply(ctx, config = {}) {
  ctx.web.registerSearchProvider(new DDGSSearchProvider(config));
}
