#!/bin/bash
file=$1
SQLITE=$2
echo $SQLITE
RESULTS=$3
echo $RESULTS
while read line; do
echo $line
INPUT=$line
docker run -v $INPUT:$INPUT -v $RESULTS:$RESULTS -v $SQLITE:$SQLITE -e AIDA_AIF_TTL=$INPUT -e AIDA_CORPUS_SQLITE=$SQLITE -e RESULTS=$RESULTS --rm aida-viz:latest /bin/bash -c "python -m aida_viz -a ${INPUT} -d ${SQLITE} -o ${RESULTS}"
done < $file
