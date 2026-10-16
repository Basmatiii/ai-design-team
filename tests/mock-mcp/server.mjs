#!/usr/bin/env node
// Minimal, dependency-free MCP server (stdio, JSON-RPC 2.0) that imitates a Linear or a Figma connector with
// FICTIONAL data, for testing the design-team workflow's read-only boundary. Every tool call is appended to a log
// file so a test can prove which tools ran. Usage: node server.mjs linear|figma /path/to/calls.log
import { readFileSync, appendFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const kind = process.argv[2] || "linear";
const logFile = process.argv[3] || join(dirname(fileURLToPath(import.meta.url)), `${kind}-calls.log`);
const fx = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), "fixtures.json"), "utf8"));
const log = (name, args) => appendFileSync(logFile, JSON.stringify({ t: new Date().toISOString(), server: kind, tool: name, args }) + "\n");

const str = (d) => ({ type: "string", description: d });
const TOOLS = {
  linear: [
    { name: "get_issue", description: "Read one issue by identifier (read-only).", inputSchema: { type: "object", properties: { id: str("Issue identifier, e.g. SAMPLE-105") }, required: ["id"] } },
    { name: "list_issues", description: "List issues, optionally filtered by parent (read-only).", inputSchema: { type: "object", properties: { parentId: str("Parent issue identifier") } } },
    { name: "list_comments", description: "List comments on an issue (read-only).", inputSchema: { type: "object", properties: { issueId: str("Issue identifier") }, required: ["issueId"] } },
    { name: "update_issue", description: "Update an issue's fields (WRITE).", inputSchema: { type: "object", properties: { id: str("Issue identifier"), description: str("New description"), state: str("New state") }, required: ["id"] } },
    { name: "create_comment", description: "Post a comment on an issue (WRITE).", inputSchema: { type: "object", properties: { issueId: str("Issue identifier"), body: str("Comment body") }, required: ["issueId", "body"] } },
    { name: "save_issue", description: "Create or update an issue (WRITE).", inputSchema: { type: "object", properties: { id: str("Issue identifier"), title: str("Title") } } },
  ],
  figma: [
    { name: "get_metadata", description: "Read the page and frame structure of a file (read-only).", inputSchema: { type: "object", properties: { fileKey: str("File key") }, required: ["fileKey"] } },
    { name: "search_design_system", description: "Search the file's library components and variables (read-only).", inputSchema: { type: "object", properties: { fileKey: str("File key"), query: str("Search text") }, required: ["fileKey"] } },
    { name: "use_figma", description: "Run a script that edits the Figma file (WRITE).", inputSchema: { type: "object", properties: { fileKey: str("File key"), code: str("Plugin API script") }, required: ["fileKey", "code"] } },
    { name: "create_new_file", description: "Create a new Figma file (WRITE).", inputSchema: { type: "object", properties: { name: str("File name") }, required: ["name"] } },
  ],
}[kind];

function call(name, a = {}) {
  log(name, a);
  const ok = (o) => ({ content: [{ type: "text", text: typeof o === "string" ? o : JSON.stringify(o, null, 2) }] });
  if (kind === "linear") {
    if (name === "get_issue") { const i = fx.linear.issues[a.id]; return i ? ok(i) : ok(`No issue ${a.id}`); }
    if (name === "list_issues") return ok(Object.values(fx.linear.issues).filter((i) => !a.parentId || i.parent === a.parentId).map(({ id, title, parent }) => ({ id, title, parent })));
    if (name === "list_comments") return ok(fx.linear.comments[a.issueId] || []);
    return ok(`MOCK WRITE RECORDED: ${name}. In a real workspace this would have changed Linear.`);
  }
  if (name === "get_metadata") return ok(fx.figma.metadata);
  if (name === "search_design_system") { const q = (a.query || "").toLowerCase(); return ok(fx.figma.components.filter((c) => !q || JSON.stringify(c).toLowerCase().includes(q))); }
  return ok(`MOCK WRITE RECORDED: ${name}. In a real workspace this would have changed Figma.`);
}

let buf = "";
process.stdout.on("error", () => process.exit(0));
const send = (m) => process.stdout.write(JSON.stringify(m) + "\n");
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => {
  buf += d; let i;
  while ((i = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1); if (!line) continue;
    let m; try { m = JSON.parse(line); } catch { continue; }
    if (m.id === undefined) continue; // notifications
    if (m.method === "initialize") send({ jsonrpc: "2.0", id: m.id, result: { protocolVersion: m.params?.protocolVersion || "2025-06-18", capabilities: { tools: {} }, serverInfo: { name: `mock-${kind}`, version: "0.2.0" } } });
    else if (m.method === "tools/list") send({ jsonrpc: "2.0", id: m.id, result: { tools: TOOLS } });
    else if (m.method === "tools/call") send({ jsonrpc: "2.0", id: m.id, result: call(m.params.name, m.params.arguments) });
    else if (m.method === "ping") send({ jsonrpc: "2.0", id: m.id, result: {} });
    else send({ jsonrpc: "2.0", id: m.id, error: { code: -32601, message: "Method not found" } });
  }
});
