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
    { name: "get_metadata", description: "Read the page and frame structure of a file or one node (read-only).", inputSchema: { type: "object", properties: { fileKey: str("File key"), nodeId: str("Optional node id") }, required: ["fileKey"] } },
    { name: "get_design_context", description: "Read layout, components, variables and text of one node (read-only).", inputSchema: { type: "object", properties: { fileKey: str("File key"), nodeId: str("Node id") }, required: ["fileKey", "nodeId"] } },
    { name: "get_screenshot", description: "Screenshot of one node (read-only). The mock returns a text description in place of an image.", inputSchema: { type: "object", properties: { fileKey: str("File key"), nodeId: str("Node id") }, required: ["fileKey", "nodeId"] } },
    { name: "get_variable_defs", description: "Variables and styles used by one node (read-only).", inputSchema: { type: "object", properties: { fileKey: str("File key"), nodeId: str("Node id") }, required: ["fileKey"] } },
    { name: "search_design_system", description: "Search the file's library components and variables (read-only).", inputSchema: { type: "object", properties: { fileKey: str("File key"), query: str("Search text") }, required: ["fileKey"] } },
    { name: "get_libraries", description: "List the libraries attached to a file (read-only).", inputSchema: { type: "object", properties: { fileKey: str("File key") }, required: ["fileKey"] } },
    { name: "use_figma", description: "Run a script that edits the Figma file (WRITE).", inputSchema: { type: "object", properties: { fileKey: str("File key"), code: str("Plugin API script"), description: str("What the script does") }, required: ["fileKey", "code"] } },
    { name: "create_new_file", description: "Create a new Figma file (WRITE).", inputSchema: { type: "object", properties: { name: str("File name") }, required: ["name"] } },
  ],
}[kind];

// Failure injection for tests: MOCK_FAIL=use_figma,get_screenshot makes those tools return an MCP error result.
// MOCK_BUILD=inaccessible makes frames created by use_figma read back as an inaccessible design.
const FAIL = new Set((process.env.MOCK_FAIL || "").split(",").map((s) => s.trim()).filter(Boolean));
let created = 0;

function call(name, a = {}) {
  log(name, a);
  const ok = (o) => ({ content: [{ type: "text", text: typeof o === "string" ? o : JSON.stringify(o, null, 2) }] });
  if (FAIL.has(name)) return { isError: true, content: [{ type: "text", text: `MOCK FAILURE: ${name} returned 503 Service Unavailable (injected by MOCK_FAIL).` }] };
  if (kind === "linear") {
    if (name === "get_issue") { const i = fx.linear.issues[a.id]; return i ? ok(i) : ok(`No issue ${a.id}`); }
    if (name === "list_issues") return ok(Object.values(fx.linear.issues).filter((i) => !a.parentId || i.parent === a.parentId).map(({ id, title, parent }) => ({ id, title, parent })));
    if (name === "list_comments") return ok(fx.linear.comments[a.issueId] || []);
    return ok(`MOCK WRITE RECORDED: ${name}. In a real workspace this would have changed Linear.`);
  }
  const built = (id) => { const i = parseInt(String(id).split(":")[1], 10); if (!(i >= 1 && i <= created)) return null; return process.env.MOCK_BUILD === "inaccessible" ? fx.figma.nodes["20:1"] : fx.figma.built[(i - 1) % fx.figma.built.length]; };
  const node = (id) => fx.figma.nodes[id] || (String(id || "").startsWith("99:") ? built(id) : null);
  if (name === "get_metadata") { if (!a.nodeId) return ok(fx.figma.metadata); const n = node(a.nodeId); return n ? ok({ id: a.nodeId, name: n.name, type: "FRAME", children: n.layers }) : ok(`No node ${a.nodeId}`); }
  if (name === "get_design_context") { const n = node(a.nodeId); return n ? ok({ id: a.nodeId, name: n.name, context: n.context }) : ok(`No node ${a.nodeId}`); }
  if (name === "get_screenshot") { const n = node(a.nodeId); return n ? ok(`MOCK SCREENSHOT of ${a.nodeId} "${n.name}" (text standing in for an image): ${n.screenshot}`) : ok(`No node ${a.nodeId}`); }
  if (name === "get_variable_defs") { const n = node(a.nodeId); return ok(n ? n.variables : fx.figma.variables); }
  if (name === "get_libraries") return ok(fx.figma.libraries);
  if (name === "search_design_system") { const q = (a.query || "").toLowerCase(); return ok(fx.figma.components.filter((c) => !q || JSON.stringify(c).toLowerCase().includes(q))); }
  if (name === "use_figma") {
    // A script that creates nothing (inspection through the plugin API) changes nothing. A creating script gets one
    // node per top-level frame it makes, capped at six; each reads back as one of the six fixture states.
    const code = String(a.code || "");
    const frames = (code.match(/createFrame\(|\.clone\(/g) || []).length;
    const creates = frames > 0 || /createInstance\(|createComponent\(|createText\(|appendChild\(/.test(code);
    if (!creates) return ok({ status: "success", note: "MOCK: read-only script executed against the fictional file. Nothing was created or changed.", pages: fx.figma.metadata.pages });
    const n = Math.max(1, Math.min(6, frames)); const nodes = [];
    for (let i = 0; i < n; i++) { created += 1; nodes.push({ id: `99:${created}`, name: (process.env.MOCK_BUILD === "inaccessible" ? fx.figma.nodes["20:1"] : fx.figma.built[(created - 1) % fx.figma.built.length]).name, link: `https://figma.example/design/POLLEN-DEMO?node-id=99-${created}` }); }
    return ok({ status: "success", note: "MOCK WRITE RECORDED: the script ran against the fictional file. A real workspace would now contain these frames.", createdNodes: nodes });
  }
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
    if (m.method === "initialize") send({ jsonrpc: "2.0", id: m.id, result: { protocolVersion: m.params?.protocolVersion || "2025-06-18", capabilities: { tools: {} }, serverInfo: { name: `mock-${kind}`, version: "0.3.0" } } });
    else if (m.method === "tools/list") send({ jsonrpc: "2.0", id: m.id, result: { tools: TOOLS } });
    else if (m.method === "tools/call") send({ jsonrpc: "2.0", id: m.id, result: call(m.params.name, m.params.arguments) });
    else if (m.method === "ping") send({ jsonrpc: "2.0", id: m.id, result: {} });
    else send({ jsonrpc: "2.0", id: m.id, error: { code: -32601, message: "Method not found" } });
  }
});
