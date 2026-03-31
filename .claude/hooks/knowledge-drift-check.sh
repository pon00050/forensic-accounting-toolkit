#!/usr/bin/env bash
# knowledge-drift-check.sh — Detect unmirrored or diverged knowledge files in ecosystem repos at session end.
#
# For each repo in ALL_REPOS, checks if knowledge/context/ or knowledge/hypotheses/
# directories contain .md files:
#   - UNMIRRORED: stem not found in hub knowledge/ at all
#   - CONTENT DRIFT: stem matches hub file but content differs (hash mismatch)
#
# Fires silently when there is no drift.
# Output goes to Claude as context.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../../ecosystem.conf" 2>/dev/null || {
    BASE="/c/Users/pon00/Projects"
    HUB="$BASE/forensic-accounting-toolkit"
    ALL_REPOS=(forensic-accounting-toolkit kr-company-registry kr-trading-calendar
        kr-beneish kr-derivatives jfia-catalog jfia-forensic kr-enforcement-cases
        kr-forensic-core krff-shell kr-dart-pipeline kr-anomaly-scoring kr-stat-tests
        kr-real-estate)
}

KNOWLEDGE_DIR="$HUB/knowledge"

# Build index of hub knowledge stems (case-insensitive) → full path
declare -A hub_stem_to_path
while IFS= read -r file; do
    stem=$(basename "$file" .md | tr '[:upper:]' '[:lower:]')
    hub_stem_to_path[$stem]="$file"
done < <(find "$KNOWLEDGE_DIR" -name "*.md" 2>/dev/null)

# Hash a file's content after stripping frontmatter (lines between --- delimiters)
content_hash() {
    local file="$1"
    awk '/^---/{c++; if(c==2){p=1; next}} p{print}' "$file" 2>/dev/null | md5sum 2>/dev/null | cut -d' ' -f1
}

unmirrored=()
content_drifted=()

for repo in "${ALL_REPOS[@]}"; do
    # Skip the hub itself
    [ "$repo" = "forensic-accounting-toolkit" ] && continue

    repo_path="$BASE/$repo"
    [ ! -d "$repo_path" ] && continue

    # Check knowledge/context/ and knowledge/hypotheses/ and knowledge/
    for subdir in "knowledge/context" "knowledge/hypotheses" "knowledge"; do
        repo_knowledge="$repo_path/$subdir"
        [ ! -d "$repo_knowledge" ] && continue

        while IFS= read -r file; do
            stem=$(basename "$file" .md | tr '[:upper:]' '[:lower:]')
            # Skip _index files
            [ "$stem" = "_index" ] && continue

            rel="${file#$BASE/}"

            if [ -z "${hub_stem_to_path[$stem]:-}" ]; then
                # Not in hub at all
                unmirrored+=("$rel")
            else
                # Stem matches — compare content hashes
                hub_file="${hub_stem_to_path[$stem]}"
                repo_hash=$(content_hash "$file")
                hub_hash=$(content_hash "$hub_file")
                if [ -n "$repo_hash" ] && [ -n "$hub_hash" ] && [ "$repo_hash" != "$hub_hash" ]; then
                    hub_rel="${hub_file#$BASE/}"
                    content_drifted+=("$rel → hub: $hub_rel")
                fi
            fi
        done < <(find "$repo_knowledge" -maxdepth 2 -name "*.md" 2>/dev/null)
    done
done

if [ "${#unmirrored[@]}" -gt 0 ] || [ "${#content_drifted[@]}" -gt 0 ]; then
    echo "--- KNOWLEDGE DRIFT (session end) ---"

    if [ "${#unmirrored[@]}" -gt 0 ]; then
        echo "  UNMIRRORED — ${#unmirrored[@]} file(s) in repos with no hub copy:"
        for f in "${unmirrored[@]}"; do
            echo "    $f"
        done
        echo "  Copy these to hub knowledge/ with gold-standard frontmatter."
        echo "  Or run /knowledge-sync to migrate them automatically."
    fi

    if [ "${#content_drifted[@]}" -gt 0 ]; then
        echo "  CONTENT DRIFT — ${#content_drifted[@]} file(s) with same name but different content:"
        for f in "${content_drifted[@]}"; do
            echo "    $f"
        done
        echo "  Review which version is authoritative and update the other."
    fi

    echo "---"
fi
