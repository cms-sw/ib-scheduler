#!/bin/sh -ex
if [ "X$1" = X ]; then
  echo "Please specify arch"
  exit 1
fi

if [ "X$2" = X ]; then
  echo "Please specify work directory (should be on local disk)"
  exit 1
fi

export SCRAM_ARCH=$1
export BASEDIR=$2
export BASEDESTDIR=/afs/cern.ch/cms/sw/ReleaseCandidates
export LANG=C

# In order to avoid synchronizing the whole directories every time we do the
# following logic:
# - Get all the package directories
# - Check the source does not have a timestamp file in it called "done"
# - Do the rsync to destination.
# - Create the timestamp
# - Remove packages which are not in the source anymore.
for WEEK in 0 1; do
  WORKDIR=$BASEDIR/vol$WEEK/$SCRAM_ARCH/$SCRAM_ARCH
  DESTDIR=$BASEDESTDIR/vol$WEEK/$SCRAM_ARCH
  for PKG in `find $WORKDIR/ -mindepth 3 -maxdepth 3 -type d | sed -e "s|.*$SCRAM_ARCH/||"`; do
    if [ ! -f  $WORKDIR/$PKG/done ]; then
      echo mkdir -p $DESTDIR/$PKG
      echo rsync -av --delete --no-group --no-owner $WORKDIR/$PKG/ $DESTDIR/$PKG/ && echo touch $WORKDIR/$PKG/done
    fi
  done
  DIRFILE=`mktemp`
  find $WORKDIR -mindepth 3 -maxdepth 3 -type d | sed -e "s|.*$SCRAM_ARCH/||" > $DIRFILE
  find $DESTDIR -mindepth 3 -maxdepth 3 -type d | sed -e "s|.*$SCRAM_ARCH/||" >> $DIRFILE
  for REMOVED in `cat $DIRFILE | sort | uniq -c | grep -e "^ " | grep -e '^[^1]*1 '| sed -e's/^[^1]*1 //'`; do
    pushd $DESTDIR
      echo rm -rf $REMOVED
    popd
  done
  rm $DIRFILE
done

# We install packages for both weeks. We reset every two week, alternating.
# Notice that the biweekly period for week 1 is shifted by 1 week for this
# reason we move it away from the 0 into 52 and take the modulo 52 afterward.
# Potentially we could separate the installation of the two volumes so that 
# we don't need a huge local disk, but we can scatter this on different machienes.
for WEEK in 0 1; do
  BIWEEK=`echo "((52 + $(date +%W) - $WEEK)/2)%26" | bc`
  WORKDIR=$BASEDIR/vol$WEEK/$SCRAM_ARCH
  DESTDIR=$BASEDESTDIR/vol$WEEK
  mkdir -p $WORKDIR
  # Due to a bug in bootstrap.sh I need to install separate archs in separate directories.
  # This is because bootstraptmp is otherwise shared between different arches. Sigh.
  LOGFILE=$WORKDIR/bootstrap-$BIWEEK.log
  # If the bootstrap log for the current two week period is not there
  # rebootstrap the area.
  if [ ! -e $LOGFILE ]; then
    # We move it so that if we are slow removing it, we do not endup removing
    # what got installed by someone else.  
    mv $WORKDIR $WORKDIR.old
    rm -rf $WORKDIR.old
    mkdir -p $WORKDIR/common
    touch $LOGFILE
    wget -O $WORKDIR/bootstrap.sh http://cmsrep.cern.ch/cmssw/cms/bootstrap.sh
    sh -x $WORKDIR/bootstrap.sh setup -path $WORKDIR -r cms.week$WEEK -arch $SCRAM_ARCH >& $LOGFILE
    # We install locally, but we want to run from DESTDIR.
    echo "CMS_INSTALL_PREFIX='$DESTDIR'; export CMS_INSTALL_PREFIX" > $WORKDIR/common/apt-site-env.sh
  fi
  # Since we are installing on a local disk, no need to worry about
  # the rpm database.
  #
  # Make sure we do not mess up environment.
  # Also we do not want the installation of one release (which can be broken)
  # to interfere with the installation of a different one. For that reason we
  # ignore the exit code.
  (
    source $WORKDIR/$SCRAM_ARCH/external/apt/*/etc/profile.d/init.sh ;
    apt-get update ;
    CMSSW_PKGS=`apt-cache search cmssw | sed -e 's/ .*//' | grep _X` ;
    for x in $CMSSW_PKGS ; do
      apt-get install -q -y $x ;
    done ;
    apt-get clean 
  ) || true 
  # Do the final rsync for the installation relying of rsync is much better to
  # install on afs than trusting anything else. It also has the advantage we
  # can delete only what changed, not the whole repository.
  rsync -a --delete --no-group --no-owner $WORKDIR/$SCRAM_ARCH/ $DESTDIR/$SCRAM_ARCH/
  rsync -a --no-group --no-owner $WORKDIR/etc/ $DESTDIR/etc/
done
