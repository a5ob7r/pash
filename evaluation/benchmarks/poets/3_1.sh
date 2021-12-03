#!/bin/bash
# tag: sort
# set -e

IN=${IN:-$PASH_TOP/evaluation/benchmarks/poets/input/pg/}
OUT=${OUT:-$PASH_TOP/evaluation/benchmarks/poets/output/3_1/}
ENTRIES=${ENTRIES:-1000}
mkdir -p "$OUT"
#ls ${IN} | sed "s;^;$IN;"| xargs cat| tr -sc '[A-Z][a-z]' '[\012*]' | sort | uniq -c | sort -nr
for input in $(ls ${IN} | head -n ${ENTRIES})
do
    cat $IN/$input | tr -sc '[A-Z][a-z]' '[\012*]' | sort | uniq -c | sort -nr > ${OUT}/${input}.out
done

#for output in $(ls ${OUT} | sed "s;^;$OUT;")
#do
#    cat $output
#done

echo 'done';
rm -rf "${OUT}"
