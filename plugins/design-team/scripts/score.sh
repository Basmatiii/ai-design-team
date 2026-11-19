#!/bin/sh
# The AI Design Team: deterministic rubric scoring. POSIX sh and awk only.
#
#   sh score.sh <rubric.md> <scores.txt>
#
# The rubric file carries its own weights in one machine-readable line, for example:
#   <!-- weights: requirements=25 ux=25 system=20 accessibility=20 craft=10 threshold=85 floor=3 -->
# The scores file is plain key=value, one per line:
#   requirements=4        a whole number 0 to 5, or "na" when the criterion could not be inspected
#   blockers=0            count of unresolved hard blockers (required, never assumed)
#   correction_pass=no    optional, echoed back
#
# Weighted total = SUM(weight * rating / 5). PASS needs: every criterion rated, total at or above
# the threshold, no rating below the floor, and zero hard blockers.
# Exit status: 0 PASS, 1 NEEDS IMPROVEMENT, 2 invalid input.

rubric="$1"; scores="$2"
[ -f "$rubric" ] || { echo "ERROR: rubric file not found: $rubric"; exit 2; }
[ -f "$scores" ] || { echo "ERROR: scores file not found: $scores"; exit 2; }

spec=$(grep -oE 'weights:[^>]*' "$rubric" | head -n 1 | sed -E 's/^weights:[[:space:]]*//; s/[[:space:]-]*$//')
[ -n "$spec" ] || { echo "ERROR: no 'weights:' line in $rubric"; exit 2; }

awk -v spec="$spec" '
BEGIN {
  thr = 85; minr = 3
  n = split(spec, parts, /[ \t]+/)
  for (i = 1; i <= n; i++) {
    if (parts[i] == "") continue
    split(parts[i], kv, "=")
    if (kv[1] == "threshold") thr = kv[2] + 0
    else if (kv[1] == "floor") minr = kv[2] + 0
    else { m++; order[m] = kv[1]; w[kv[1]] = kv[2] + 0; wsum += kv[2] }
  }
}
/^[ \t]*#/ || !/=/ { next }
{
  line = $0; sub(/\r$/, "", line)
  k = line; sub(/=.*/, "", k); v = line; sub(/^[^=]*=/, "", v)
  gsub(/^[ \t]+|[ \t]+$/, "", k); gsub(/^[ \t]+|[ \t]+$/, "", v)
  val[k] = tolower(v)
}
END {
  if (wsum != 100) { printf "ERROR: rubric weights add up to %s, not 100\n", wsum; exit 2 }
  for (i = 1; i <= m; i++) {
    c = order[i]; v = val[c]
    if (!(c in val) || v == "") { err = err " missing:" c; continue }
    if (v == "na" || v == "n/a") { na = na " " c; ratings = ratings " " c "=na"; continue }
    if (v !~ /^[0-5]$/) { err = err " invalid:" c "=" v; continue }
    total += w[c] * v / 5; assessed += w[c]; ratings = ratings " " c "=" v
    if (v + 0 < minr) low = low " " c
  }
  b = val["blockers"]
  if (!("blockers" in val) || b !~ /^[0-9]+$/) err = err " missing-or-invalid:blockers"
  if (err != "") { print "ERROR: scores file is incomplete or invalid:" err; exit 2 }

  if (na != "") printf "SCORE: %s/%s assessable points (INCOMPLETE, not out of 100)\n", total + 0, assessed + 0
  else          printf "SCORE: %s/100\n", total + 0
  print "RATINGS:" ratings
  pass = 1; reasons = ""
  if (na != "")        { pass = 0; reasons = reasons "; not assessed (no evidence inspected):" na }
  if (na == "" && total < thr) { pass = 0; reasons = reasons "; total below " thr }
  if (low != "")       { pass = 0; reasons = reasons "; rated below " minr ":" low }
  if (b + 0 > 0)       { pass = 0; reasons = reasons "; " b " unresolved hard blocker(s)" }
  if (pass) print "VERDICT: PASS"
  else { sub(/^; /, "", reasons); print "VERDICT: NEEDS IMPROVEMENT"; print "REASONS: " reasons }
  print "THRESHOLD: " thr "/100, no rating below " minr ", no hard blockers"
  if ("correction_pass" in val) print "CORRECTION_PASS: " val["correction_pass"]
  exit (pass ? 0 : 1)
}' "$scores"
