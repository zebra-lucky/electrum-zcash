#!/bin/bash

REQ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

for fname in $REQ_DIR/requirements*
do
    if ! [[ -s "$fname" && -z "$(tail -c 1 "$fname")" ]]; then
        echo "No newline at end of $fname"
        echo "" >> $fname
    fi
done
