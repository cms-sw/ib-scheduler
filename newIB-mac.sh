#!/bin/bash
##################################################################
#usage: newIB-mac.sh <release cycle> <scram archs> [<build machine>] [<build directory>]
##################################################################
machine="macms05"
TOPDIR=/build1/cmsbuild/intBld
if [ "X$3" != "X" ] ; then  machine=$3 ; fi
if [ "X$4" != "X" ] ; then  TOPDIR=$4  ; fi

ADDRS="cmssdt-ibs@cern.ch"
FRONT_END="vocms12.cern.ch"
SCRIPT_DIR=`dirname $0`
LOCALINSTALL=${TOPDIR}/Install
INT_BLD_LOG_DIR=$TOPDIR/logs/p$$
INT_BLD_LOG_FILE=$INT_BLD_LOG_DIR/intBld.log

echo ssh $machine mkdir -p $INT_BLD_LOG_DIR
ssh $machine mkdir -p $INT_BLD_LOG_DIR

echo ssh $machine touch $INT_BLD_LOG_FILE
ssh $machine touch $INT_BLD_LOG_FILE

ssh $machine "mkdir -p $TOPDIR; rm -rf ${TOPDIR}/scripts"
scp -q -r ${SCRIPT_DIR} $machine:${TOPDIR}/scripts
echo ssh $machine "${TOPDIR}/scripts/buildIB.py --releasecycle '$1' --architectures '$2' --buildDir $TOPDIR --logfile ${INT_BLD_LOG_FILE} --nomail"
ssh $machine "${TOPDIR}/scripts/buildIB.py --releasecycle '$1' --architectures '$2' --buildDir $TOPDIR --logfile ${INT_BLD_LOG_FILE} --nomail"

stamp=`ssh $machine "grep 'IB stamp=' $INT_BLD_LOG_FILE | tail -n 1 | cut -c 10-"`
stampday=`echo $stamp | cut -c 1-3`
stamphour=`echo $stamp | cut -c 5-6`

arch=`ssh $machine "grep 'IB self._arch=' $INT_BLD_LOG_FILE | tail -n 1 | cut -c 15-"`
cycname=`ssh $machine "grep 'IB self.cycname=' $INT_BLD_LOG_FILE | tail -n 1 | cut -c 17-"`
cycname_dot=`ssh $machine "grep 'IB self.cycname dot=' $INT_BLD_LOG_FILE | tail -n 1 | cut -c 21-"`
ibname=`ssh $machine "grep 'IB ibName=' $INT_BLD_LOG_FILE | tail -n 1 | cut -c 11-"`

AFSWWW=/afs/cern.ch/cms/sw/ReleaseCandidates/$arch/www
mkdir -p $AFSWWW
LOGFILE=$AFSWWW/intBld.${cycname_dot}.log
touch $LOGFILE
echo "===================================================" >> ${LOGFILE}
date >> ${LOGFILE}

echo arch=$arch >> ${LOGFILE} 2>&1 3>&1
echo cycname=${cycname} >> ${LOGFILE} 2>&1 3>&1
echo cycname_dot=${cycname_dot} >> ${LOGFILE} 2>&1 3>&1
echo stamp=$stamp >> ${LOGFILE} 2>&1 3>&1
echo stampday=$stampday >> ${LOGFILE} 2>&1 3>&1
echo ibname=$ibname >> ${LOGFILE} 2>&1 3>&1
if [ "X$stampday" != "X" ] ; then
  echo stamphour=$stamphour >> ${LOGFILE} 2>&1 3>&1
  if [ "X$stamphour" != "X" ] ; then
    echo rm -rf $AFSWWW/$stampday/${cycname_dot}-$stampday-$stamphour >> ${LOGFILE} 2>&1 3>&1
    rm -rf $AFSWWW/$stampday/${cycname_dot}-$stampday-$stamphour >> ${LOGFILE} 2>&1 3>&1
    mkdir -p $AFSWWW/$stampday  >> ${LOGFILE} 2>&1 3>&1
    echo scp -q -r $machine:$LOCALINSTALL/$arch/www/$stampday/${cycname_dot}-$stampday-$stamphour $AFSWWW/$stampday/${cycname_dot}-$stampday-$stamphour >> ${LOGFILE} 2>&1 3>&1
    scp -q -r $machine:$LOCALINSTALL/$arch/www/$stampday/${cycname_dot}-$stampday-$stamphour $AFSWWW/$stampday/${cycname_dot}-$stampday-$stamphour >> ${LOGFILE} 2>&1 3>&1
    dqm_reports=\'`ssh $machine "ls -d -1 /Volumes/build1/cmsbuild/intBld/cms/$arch/cms/cmssw/$ibname/build_comparison_reports/* | grep -v log$ | grep -v pkls$ | grep -v pkl$ | grep -v back$ | tr '\n' ' '"`\'
    echo ssh $FRONT_END \"mkdir -p /data/intBld/incoming/dqm-reports/$arch/$ibname/report\" >> ${LOGFILE} 2>&1 3>&1
    ssh $FRONT_END \"mkdir -p /data/intBld/incoming/dqm-reports/$arch/$ibname/report\"
    echo ssh $FRONT_END \"scp -r $machine:$dqm_reports /data/intBld/incoming/dqm-reports/$arch/$ibname/report\" >> ${LOGFILE} 2>&1 3>&1
    ssh $FRONT_END \"scp -r $machine:$dqm_reports /data/intBld/incoming/dqm-reports/$arch/$ibname/report\"
    echo ssh $FRONT_END \"scp -r $machine:/Volumes/build1/cmsbuild/intBld/cms/$arch/cms/cmssw/$ibname/build_comparison_reports/runall-comparison.log  $AFSWWW/$stampday/${cycname_dot}-$stampday-$stamphour/$ibname/pyRelValMatrixLogs/run/runall-comparison.log\" >> ${LOGFILE} 2>&1 3>&1
    ssh $FRONT_END \"scp -r $machine:/Volumes/build1/cmsbuild/intBld/cms/$arch/cms/cmssw/$ibname/build_comparison_reports/runall-comparison.log  $AFSWWW/$stampday/${cycname_dot}-$stampday-$stamphour/$ibname/pyRelValMatrixLogs/run/runall-comparison.log\"
    echo "will mail build log"
    ssh $machine cat  $INT_BLD_LOG_FILE | mail -s "IB for ${cycname}_X on $arch finished" ${ADDRS} >> ${LOGFILE} 2>&1 3>&1
  fi
fi

echo ssh $machine rm -rf $INT_BLD_LOG_DIR >> ${LOGFILE} 2>&1 3>&1
ssh $machine rm -rf $INT_BLD_LOG_DIR
date >> ${LOGFILE}
echo ">> IB Copied: $cycname $arch $machine <<" >> ${LOGFILE} 2>&1 3>&1
