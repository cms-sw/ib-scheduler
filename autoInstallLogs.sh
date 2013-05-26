#!/bin/sh -e
export LANG=C
for WEEK in 0 1; do
  BIWEEK=`echo "((52 + $(date +%W) - $WEEK)/2)%26" | bc`
  # notice it must finish with something which matches %Y-%m-%d-%H00
  BUILDS=`ssh cmsbuild@cmsrep.cern.ch find /data/cmssw/cms.week$WEEK/WEB/build-logs/ -mindepth 2 -maxdepth 2 | cut -d/ -f7,8 | grep CMSSW | grep _X_ | grep '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]$'`
  for x in $BUILDS; do
    SCRAM_ARCH=`echo $x | cut -f1 -d/`
    CMSSW_NAME=`echo $x | cut -f2 -d/`
    CMSSW_DATE=`echo $CMSSW_NAME | sed -e's/.*_X_//'`
    CMSSW_WEEKDAY=`python -c "import time;print time.strftime('%a', time.strptime('$CMSSW_DATE', '%Y-%m-%d-%H00')).lower()"`
    CMSSW_HOUR=`python -c "import time;print time.strftime('%H', time.strptime('$CMSSW_DATE', '%Y-%m-%d-%H00')).lower()"`
    CMSSW_QUEUE=`echo $CMSSW_NAME | sed -e 's/CMSSW_\([0-9]\)_\([0-9]\)_.*/\1.\2/'`
    REL_LOGS="/afs/cern.ch/cms/sw/ReleaseCandidates/$SCRAM_ARCH/www/$CMSSW_WEEKDAY/$CMSSW_QUEUE-$CMSSW_WEEKDAY-$CMSSW_HOUR/$CMSSW_NAME/new"
    if [ -L $REL_LOGS ]; then
      rm -rf $REL_LOGS
    fi
    mkdir -p $REL_LOGS
    rsync -a --no-group --no-owner cmsbuild@cmsrep.cern.ch:/data/cmssw/cms.week$WEEK/WEB/build-logs/$SCRAM_ARCH/$CMSSW_NAME/logs/html/ $REL_LOGS/ || true
    # Decompress logs if they are compressed.
    if [ -f $REL_LOGS/html-logs.tgz ]; then
      if [ ! -f $REL_LOGS/done ]; then
        pushd $REL_LOGS
          tar xzf html-logs.tgz
        popd
        touch $REL_LOGS/done
      fi
    fi
  done
done
