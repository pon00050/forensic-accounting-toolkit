#!/usr/bin/env bash
# knowledge-freshness-check.sh — Scan hub knowledge vault for stale/incomplete notes at session start.
#
# Checks:
#   1. Stale notes: last_verified > 90 days ago
#   2. Unverifiable notes: no last_verified field at all
#   3. MOC staleness: any note has created date newer than _index.md last_updated
#   4. Frontmatter quality: notes missing required fields (domain, type, description)
#
# Fires silently when vault is healthy.
# Output goes to Claude as context.

HUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KNOWLEDGE_DIR="$HUB/knowledge"
STALE_DAYS=90
TODAY=$(date +%s)
TODAY_DATE=$(date +%Y-%m-%d)

# Only run if knowledge dir exists
if [ ! -d "$KNOWLEDGE_DIR" ]; then
    exit 0
fi

stale_notes=()
stale_ages=()
unverifiable_count=0
missing_fields_count=0
newest_created=""
newest_created_file=""

# --- MOC last_updated ---
moc_file="$KNOWLEDGE_DIR/_index.md"
moc_last_updated=""
if [ -f "$moc_file" ]; then
    moc_last_updated=$(awk '/^---/{c++; if(c==2) exit} c==1 && /^last_updated:/{print $2}' "$moc_file" 2>/dev/null)
fi

while IFS= read -r file; do
    # Skip redirect notes — they are intentionally stale placeholders
    note_type=$(awk '/^---/{c++; if(c==2) exit} c==1 && /^type:/{print $2}' "$file" 2>/dev/null)
    [ "$note_type" = "redirect" ] && continue

    # --- Check 1 & 2: stale vs. missing last_verified ---
    last_verified=$(awk '/^---/{c++; if(c==2) exit} c==1 && /^last_verified:/{print $2}' "$file" 2>/dev/null)

    if [ -z "$last_verified" ]; then
        (( unverifiable_count++ ))
    else
        file_epoch=$(date -d "$last_verified" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$last_verified" +%s 2>/dev/null)
        if [ -n "$file_epoch" ]; then
            age_days=$(( (TODAY - file_epoch) / 86400 ))
            if [ "$age_days" -gt "$STALE_DAYS" ]; then
                rel_path="${file#$KNOWLEDGE_DIR/}"
                stale_notes+=("$rel_path")
                stale_ages+=("$age_days")
            fi
        fi
    fi

    # --- Check 3: MOC staleness (newest created date) ---
    if [ -n "$moc_last_updated" ]; then
        created=$(awk '/^---/{c++; if(c==2) exit} c==1 && /^created:/{print $2}' "$file" 2>/dev/null)
        if [ -n "$created" ] && [[ "$created" > "$moc_last_updated" ]]; then
            if [ -z "$newest_created" ] || [[ "$created" > "$newest_created" ]]; then
                newest_created="$created"
                newest_created_file="${file#$KNOWLEDGE_DIR/}"
            fi
        fi
    fi

    # --- Check 4: Frontmatter quality (required fields) ---
    has_domain=$(awk '/^---/{c++; if(c==2) exit} c==1 && /^domain:/{found=1} END{print found+0}' "$file" 2>/dev/null)
    has_type=$(awk '/^---/{c++; if(c==2) exit} c==1 && /^type:/{found=1} END{print found+0}' "$file" 2>/dev/null)
    has_description=$(awk '/^---/{c++; if(c==2) exit} c==1 && /^description:/{found=1} END{print found+0}' "$file" 2>/dev/null)
    if [ "$has_domain" != "1" ] || [ "$has_type" != "1" ] || [ "$has_description" != "1" ]; then
        (( missing_fields_count++ ))
    fi

done < <(find "$KNOWLEDGE_DIR" -name "*.md" ! -name "_index.md" 2>/dev/null)

# --- Output ---
issues=0

if [ "${#stale_notes[@]}" -gt 0 ]; then
    (( issues++ ))
    echo "--- KNOWLEDGE FRESHNESS ---"
    echo "  ${#stale_notes[@]} note(s) stale (last_verified > ${STALE_DAYS} days):"
    for i in "${!stale_notes[@]}"; do
        echo "  ${stale_ages[$i]}d  ${stale_notes[$i]}"
    done | sort -rn | head -5 | sed 's/^/    /'
    if [ "${#stale_notes[@]}" -gt 5 ]; then
        echo "    ... and $((${#stale_notes[@]} - 5)) more"
    fi
    echo "  Run /vault-housekeeping to refresh the full vault."
fi

if [ "$unverifiable_count" -gt 0 ]; then
    (( issues++ ))
    [ "$issues" -eq 1 ] && echo "--- KNOWLEDGE FRESHNESS ---"
    echo "  ${unverifiable_count} note(s) have no last_verified field (invisible to freshness checks)"
    echo "  Run /knowledge-audit to find them and add last_verified dates."
fi

if [ -n "$newest_created" ]; then
    (( issues++ ))
    [ "$issues" -eq 1 ] && echo "--- KNOWLEDGE FRESHNESS ---"
    echo "  MOC may need regeneration: note created ${newest_created} (${newest_created_file}) is newer than MOC (${moc_last_updated:-unknown})"
    echo "  Run /create-moc to rebuild _index.md."
fi

if [ "$missing_fields_count" -gt 0 ]; then
    (( issues++ ))
    [ "$issues" -eq 1 ] && echo "--- KNOWLEDGE FRESHNESS ---"
    echo "  ${missing_fields_count} note(s) missing required frontmatter fields (domain, type, or description)"
    echo "  Run /knowledge-audit to find and fix incomplete frontmatter."
fi

if [ "$issues" -gt 0 ]; then
    echo "---"
fi
