#!/bin/bash
BLD_DIR=/build/cmsbuild
if [ "X$1" != "X" ] ; then
  BLD_DIR=$1
fi
BLD_DIR=${BLD_DIR}/stdTest-Cleanup

mkdir -p $BLD_DIR

LOGFILE=${BLD_DIR}/cleanupLog-`date +%Y%m%d-%H%M`.log

cd $BLD_DIR
svn -q co svn+ssh://svn.cern.ch/reps/CMSIntBld/trunk/IntBuild/QA QA > $LOGFILE 2>&1

$BLD_DIR/QA/cleanupQA.py --type QALocal >> $LOGFILE 2>&1
`dirname $0`/cleanupDirs.py --type QAIgprof >> $LOGFILE 2>&1

