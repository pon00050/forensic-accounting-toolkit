#!/bin/bash
# SessionStart hook: show board summary when opening the toolkit hub
# Output goes to Claude as context

GH="/c/Program Files/GitHub CLI/gh.exe"

echo "=== Forensic Accounting Toolkit — Session Start ==="
echo ""

# Board summary
BOARD=$("$GH" project item-list 1 --owner pon00050 --format json 2>/dev/null)

if [ $? -eq 0 ]; then
    # Count items by status
    TODO_AI=$(echo "$BOARD" | python -c "
import sys, json
data = json.load(sys.stdin)
items = [i for i in data['items'] if i.get('status') == 'Todo']
# Check for Owner field in the raw data
ai_count = 0
for i in items:
    # Owner field may not be in the simplified JSON; count all Todo as actionable
    ai_count += 1
print(f'{ai_count} items in Todo')
" 2>/dev/null)

    DONE=$(echo "$BOARD" | python -c "
import sys, json
data = json.load(sys.stdin)
done = [i for i in data['items'] if i.get('status') == 'Done']
print(f'{len(done)} items done')
" 2>/dev/null)

    echo "Board: $TODO_AI, $DONE"

    # Show P0 items
    echo ""
    echo "P0 items:"
    echo "$BOARD" | python -c "
import sys, json
data = json.load(sys.stdin)
for i in data['items']:
    if i.get('priority') == 'P0' and i.get('status') != 'Done':
        print(f'  - {i[\"title\"]}')
" 2>/dev/null
else
    echo "Board: could not fetch (gh CLI issue or offline)"
fi

echo ""
echo "Use /board for full details, /ecosystem-status for repo health, /work <repo> to switch."
