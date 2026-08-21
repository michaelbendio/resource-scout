import { SafeFetchProvider } from "./index.js";


let input = "";
for await (const chunk of process.stdin) input += chunk;

try {
  const request = JSON.parse(input);
  const provider = new SafeFetchProvider({
    timeoutMs: Number(request.timeoutMs) || 30000,
    maxBytes: Number(request.maxBytes) || 500000,
    maxRedirects: Number(request.maxRedirects) || 5,
    maxCalls: 1,
  });
  const result = await provider.fetch({ url: String(request.url || "") });
  process.stdout.write(JSON.stringify(result));
} catch (error) {
  process.stderr.write(`${error?.message || String(error)}\n`);
  process.exitCode = 1;
}
