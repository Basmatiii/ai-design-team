#!/bin/sh
# The AI Design Team: enforcement and run ledger.
#
# Claude Code runs this script from hooks/hooks.json with the hook event as JSON on stdin.
# It is plain POSIX sh on purpose: no jq, node or python needed on the designer's machine.
#
#   guard.sh prompt        UserPromptSubmit: records a typed approval, opens a workflow window
#   guard.sh linear-write  PreToolUse: Linear tools that are not reads
#   guard.sh figma-write   PreToolUse: Figma tools that are not reads
#   guard.sh agent-scope   PreToolUse: Write, Edit, NotebookEdit, Skill, Bash inside design-team agents
#   guard.sh dispatch      PreToolUse: Agent and SendMessage (handoff budget + ledger)
#   guard.sh ledger-ok     PostToolUse: Figma and Linear calls that succeeded
#   guard.sh ledger-fail   PostToolUseFailure: Figma and Linear calls that failed
#   guard.sh ledger-stop   SubagentStop: a design-team agent finished
#
# A decision is printed as JSON on stdout. No output means "no decision": Claude Code's normal
# permission flow (your allow, ask and deny rules) still applies afterwards.

mode="$1"
INPUT=$(cat | tr '\n\r' '  ')

STATE="${CLAUDE_PLUGIN_DATA:-${TMPDIR:-/tmp}/design-team-state}"
TTL_MIN="${DESIGN_TEAM_APPROVAL_TTL_MIN:-120}"
MAX_SPAWNS="${DESIGN_TEAM_MAX_SPAWNS:-5}"
MAX_RESUMES="${DESIGN_TEAM_MAX_RESUMES:-6}"
LEDGER_DIR="${CLAUDE_PROJECT_DIR:-.}/.design-team"

# Every string value of a JSON key, one per line. Quotes inside JSON strings are escaped, so a key
# name that only appears inside a string value (ticket text, a Figma script) can never match.
vals() {
  printf '%s' "$INPUT" \
    | grep -oE "\"$1\"[[:space:]]*:[[:space:]]*\"([^\"\\\\]|\\\\.)*\"" \
    | sed -E 's/^"[^"]*"[[:space:]]*:[[:space:]]*"(.*)"$/\1/'
}
first() { vals "$1" | head -n 1; }

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

# Session id: exactly one distinct value made of safe characters, or empty (callers fail closed).
SID=$(vals session_id | sort -u)
case "$SID" in
  ''|*[!A-Za-z0-9_-]*) SID='' ;;
esac

AGENTS=$(vals agent_type)
in_team=0;  case "$AGENTS" in *design-team:*) in_team=1 ;; esac
read_only=0
case "$AGENTS" in
  *design-team:ux-analyst*|*design-team:design-qa*|*design-team:design-orchestrator*) read_only=1 ;;
esac
WHO=$(printf '%s' "$AGENTS" | head -n 1); [ -n "$WHO" ] || WHO=main

active=0
[ -n "$SID" ] && [ -f "$STATE/active/$SID" ] && active=1
# Fail closed: if the session cannot be identified, the two write gates behave as if a workflow is active.
if [ -z "$SID" ]; then case "$mode" in linear-write|figma-write) active=1 ;; esac; fi

approved() {
  [ -n "$SID" ] || return 1
  [ -f "$STATE/approved/$SID" ] || return 1
  [ -n "$(find "$STATE/approved/$SID" -mmin "-$TTL_MIN" 2>/dev/null)" ]
}

ledger() { # $1 event, $2 detail, $3 result
  [ "$active" = 1 ] || [ "$in_team" = 1 ] || return 0
  mkdir -p "$LEDGER_DIR" 2>/dev/null || return 0
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${SID:-unknown}" "$WHO" "$1" "$2" "$3" \
    >> "$LEDGER_DIR/run-ledger.tsv" 2>/dev/null
  return 0
}

bump() { # increments the counter file $1 and prints the new value
  n=$(cat "$1" 2>/dev/null); case "$n" in ''|*[!0-9]*) n=0 ;; esac
  n=$((n + 1)); printf '%s' "$n" > "$1" 2>/dev/null; printf '%s' "$n"
}

case "$mode" in

prompt)
  [ -n "$SID" ] || exit 0
  P=$(first prompt | tr 'A-Z' 'a-z' | sed -E 's/(\\n|\\r|\\t)/ /g; s/^[[:space:]]+//; s/[[:space:].!]+$//')
  mkdir -p "$STATE/active" "$STATE/approved" "$STATE/count" 2>/dev/null
  case "$P" in
    approve|approved|'approve design'|'approve the design'|/design-team:approve)
      rm -f "$STATE/count/$SID.spawn" "$STATE/count/$SID.resume"
      if [ "$active" = 1 ] || [ "$in_team" = 1 ]; then
        : > "$STATE/approved/$SID"
        ledger approval typed ok
        echo "design-team: approval recorded. Figma edits are unlocked for this session for $TTL_MIN minutes or until the next /design-team command."
      fi ;;
    revoke|'revoke approval')
      rm -f "$STATE/approved/$SID"
      [ "$active" = 1 ] && echo "design-team: approval revoked. Figma edits are locked again." ;;
    /design-team:*)
      : > "$STATE/active/$SID"; active=1
      rm -f "$STATE/approved/$SID" "$STATE/count/$SID.spawn" "$STATE/count/$SID.resume"
      ledger workflow "$(printf '%s' "$P" | cut -c1-80 | tr '\t' ' ')" start
      # Resolve rubrics here so no agent spends a turn looking for them. A project copy in
      # .claude/rubrics/ overrides the copy that ships with the plugin.
      for r in design-quality specs-check audit-check; do
        if [ -f "${CLAUDE_PROJECT_DIR:-.}/.claude/rubrics/$r.md" ]; then
          echo "design-team: rubric $r = ${CLAUDE_PROJECT_DIR:-.}/.claude/rubrics/$r.md (project override)"
        elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
          echo "design-team: rubric $r = $CLAUDE_PLUGIN_ROOT/rubrics/$r.md"
        fi
      done ;;
    '<'*) : ;; # system-generated notices (for example background agent reports) never reset budgets
    *) rm -f "$STATE/count/$SID.spawn" "$STATE/count/$SID.resume" ;;
  esac
  exit 0 ;;

linear-write)
  [ "$active" = 1 ] || [ "$in_team" = 1 ] || [ "${DESIGN_TEAM_LINEAR_LOCK:-}" = always ] || exit 0
  ledger blocked "$(first tool_name)" linear-read-only
  deny "Linear is strictly read-only while a design-team workflow is active. Only get, list, search and extract tools are allowed. Do not retry, and do not look for another way to change the ticket: report this to the person instead." ;;

figma-write)
  [ "$active" = 1 ] || [ "$in_team" = 1 ] || exit 0
  TOOL=$(first tool_name)
  if [ "$read_only" = 1 ]; then
    ledger blocked "$TOOL" read-only-role
    deny "This design-team role is read-only in Figma. Only design-team:figma-designer may edit, and only after the person approves the design approach."
  fi
  if approved; then exit 0; fi
  ledger blocked "$TOOL" no-approval
  deny "No approval on record for this session. Figma stays unchanged until the person types approve in reply to the design approach. Stop, present the approach, and wait. Do not retry this call." ;;

agent-scope)
  [ "$in_team" = 1 ] || exit 0
  TOOL=$(first tool_name)
  case "$TOOL" in
    Write|Edit)
      PATHS=$(vals file_path | sed -E 's#\\\\#/#g')
      [ -n "$PATHS" ] || deny "design-team agents may only write their own artifacts inside the project's .design-team folder."
      OLDIFS=$IFS; IFS='
'
      for p in $PATHS; do
        case "$p" in
          *..*) IFS=$OLDIFS; deny "design-team agents may only write inside the project's .design-team folder." ;;
          */.design-team/*.md|*/.design-team/*.json|*/.design-team/*.txt) : ;;
          *) IFS=$OLDIFS; deny "design-team agents may only write .md, .json or .txt artifacts inside the project's .design-team folder. No HTML, prototypes or code." ;;
        esac
      done
      IFS=$OLDIFS; exit 0 ;;
    NotebookEdit)
      deny "design-team agents do not edit notebooks." ;;
    Bash)
      CMD=$(first command | sed -E 's/\\"/"/g')
      if printf '%s' "$CMD" | grep -qE '^sh "?[A-Za-z0-9_./ :~-]+/scripts/score\.sh"? "?[A-Za-z0-9_./ :~-]+"? "?[A-Za-z0-9_./ :~-]+"?$'; then
        exit 0
      fi
      deny "design-team agents may only run the bundled score script: sh <plugin>/scripts/score.sh <rubric.md> <scores.txt>. No other shell commands." ;;
    Skill)
      SK=$(first skill | tr 'A-Z' 'a-z')
      case "$SK" in
        *figma*) exit 0 ;;
        *) deny "design-team agents may only load Figma usage skills. Other skills (prototypes, HTML, code generation) are outside this workflow." ;;
      esac ;;
  esac
  exit 0 ;;

dispatch)
  TOOL=$(first tool_name)
  TARGET=$(first subagent_type)
  case "$TOOL" in
    SendMessage)
      [ "$active" = 1 ] || [ "$in_team" = 1 ] || exit 0
      [ -n "$SID" ] || exit 0
      mkdir -p "$STATE/count" 2>/dev/null
      n=$(bump "$STATE/count/$SID.resume")
      if [ "$n" -gt "$MAX_RESUMES" ]; then
        ledger blocked SendMessage handoff-budget
        deny "Handoff budget reached: $MAX_RESUMES agent messages since the person's last instruction. Stop delegating. Report what exists (status, artifact paths, what is missing) and let the person decide the next step."
      fi
      ledger resume "$(first to | cut -c1-40)" "$n"
      exit 0 ;;
    *)
      case "$TARGET" in design-team:*) : ;; *) exit 0 ;; esac
      [ -n "$SID" ] || { ledger spawn "$TARGET" unknown-session; exit 0; }
      mkdir -p "$STATE/count" 2>/dev/null
      n=$(bump "$STATE/count/$SID.spawn")
      if [ "$n" -gt "$MAX_SPAWNS" ]; then
        in_team=1; ledger blocked "$TARGET" handoff-budget
        deny "Handoff budget reached: $MAX_SPAWNS design-team agents started since the person's last instruction. Stop delegating. Report what exists (status, artifact paths, what is missing) and let the person decide the next step."
      fi
      in_team=1; ledger spawn "$TARGET" "$n"
      exit 0 ;;
  esac ;;

ledger-ok)   ledger call "$(first tool_name) $(first nodeId)" ok;   exit 0 ;;
ledger-fail) ledger call "$(first tool_name) $(first nodeId)" fail; exit 0 ;;
ledger-stop) ledger stop "$WHO" done; exit 0 ;;

*) exit 0 ;;
esac
