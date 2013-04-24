#!/bin/bash
##################################################################
#usage: localIB.sh <release cycle> <scram arch> [YYYY-MM-DD-hh]
##################################################################

TOPDIR=`pwd`
export INTBUILD_SITELOCAL=yes
export SCRAM_ARCH=$2
SCRIPT_DIR=${TOPDIR}/IntBuild/$$
LOG_DIR=${TOPDIR}/logs/$$
LOG_FILE=${LOG_DIR}/intBld.log
CYCNAME=`echo $1 | tr '.' '_'`

rm -rf ${SCRIPT_DIR}; mkdir -p ${SCRIPT_DIR}
rm -rf ${LOG_DIR};    mkdir -p ${LOG_DIR}

SCRIPT_PATH=`dirname $0`
SVN_BRANCH=`python ${SCRIPT_PATH}/CmsTCReader.py --uri "ReleaseExternalsXML?release=CMSSW_${CYCNAME}_X&architecture=${SCRAM_ARCH}" | grep INTBUILD | sed 's|.*tag="||;s|".*||'` >>${LOG_FILE} 2>&1 3>&1
if [ "X${SVN_BRANCH}" == "X" ] ; then SVN_BRANCH="branches/production" ; fi
echo "SVN IntBuild/IB: ${SVN_BRANCH}" >>${LOG_FILE} 2>&1 3>&1

cd ${TOPDIR}
svn -q co http://svn.cern.ch/guest/CMSIntBld/${SVN_BRANCH}/IntBuild/IB ${SCRIPT_DIR}/IB  >>${LOG_FILE} 2>&1 3>&1

if [ -e ${SCRIPT_DIR}/IB/buildManager.py ] ; then
  ${SCRIPT_DIR}/IB/buildManager.py --rel $1 --ibdate $3 >>${LOG_FILE} 2>&1 3>&1
else
  echo "ERROR: Unable to checkout ${SVN_BRANCH}/IntBuild/IB" >>${LOG_FILE} 2>&1 3>&1
fi

cat ${LOG_FILE} | mail -s "IB for ${CYCNAME}_X on $SCRAM_ARCH finished" `whoami`'@cern.ch'
touch ${LOG_DIR}/../allIntBld.log
echo "================================================================================" >> ${LOG_DIR}/../allIntBld.log
echo ">>         `date`         <<" >> ${LOG_DIR}/../allIntBld.log
cat ${LOG_FILE} >>  ${LOG_DIR}/../allIntBld.log
mv ${LOG_FILE} ${LOG_DIR}/../
rm -rf ${SCRIPT_DIR} ${LOG_DIR}
