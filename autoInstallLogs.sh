#!/bin/sh -e
export LANG=C
IB_BASEDIR="/afs/cern.ch/cms/sw/ReleaseCandidates"
# Remove from AFS logs for releases older than 7 days.
find $IB_BASEDIR -maxdepth 5 -mindepth 5 -mtime +7 -path '*/www/*/CMSSW_*' -type d -exec rm -rf {} \; || true
for WEEK in 0 1; do
  BIWEEK=`echo "((52 + $(date +%W) - $WEEK)/2)%26" | bc`
  # notice it must finish with something which matches %Y-%m-%d-%H00
  # We only sync the last 7 days.
  BUILDS=`ssh cmsbuild@cmsrep.cern.ch find /data/cmssw/cms.week$WEEK/WEB/build-logs/ -mtime -7 -mindepth 2 -maxdepth 2 | cut -d/ -f7,8 | grep CMSSW | grep _X_ | grep '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]$' || true`
  for x in $BUILDS; do
    SCRAM_ARCH=`echo $x | cut -f1 -d/`
    CMSSW_NAME=`echo $x | cut -f2 -d/`
    CMSSW_DATE=`echo $CMSSW_NAME | sed -e's/.*_X_//'`
    CMSSW_WEEKDAY=`python -c "import time;print time.strftime('%a', time.strptime('$CMSSW_DATE', '%Y-%m-%d-%H00')).lower()"`
    CMSSW_HOUR=`python -c "import time;print time.strftime('%H', time.strptime('$CMSSW_DATE', '%Y-%m-%d-%H00')).lower()"`
    CMSSW_QUEUE=`echo $CMSSW_NAME | sed -e 's/CMSSW_\([0-9][0-9]*\)_\([0-9][0-9]*\)_.*/\1.\2/'`
    REL_LOGS="$IB_BASEDIR/$SCRAM_ARCH/www/$CMSSW_WEEKDAY/$CMSSW_QUEUE-$CMSSW_WEEKDAY-$CMSSW_HOUR/$CMSSW_NAME/new"
    if [ -L $REL_LOGS ]; then
      rm -rf $REL_LOGS
    fi
    mkdir -p $REL_LOGS || echo "Cannot create directory for $REL_LOGS"
    rsync -a --no-group --no-owner cmsbuild@cmsrep.cern.ch:/data/cmssw/cms.week$WEEK/WEB/build-logs/$SCRAM_ARCH/$CMSSW_NAME/logs/html/ $REL_LOGS/ || echo "Unable to sync logs in $REL_LOGS."
    pushd $REL_LOGS
      tar xzf html-logs.tgz ./logAnalysis.pkl ./index.html || echo "Unable to unpack logs in $REL_LOGS."
    popd
  done
done
