#!/usr/bin/env bash

BKP_HOST=lxbuild041

echo "Starting cmsrep bkp to "${BKP_HOST}" at: "`date`

cd /data/cmssw
nohup time rsync -vau aptinstaller.sh  \
       CernVM md5cache \
       openssl-sources oracleDownloads \
       PKGTOOLS RPMS simplify.sh SOURCES SRPMS tools \
       UploadRules.txt \
       ${BKP_HOST}:/build1/cmsbuild/cmsrep-bkp/.

echo "Starting generatorData bkp ... "`date`

cd /data/generatorData
nohup time rsync -vau . ${BKP_HOST}:/build1/cmsbuild/generatorData-bkp/.

echo "all backups finished "`date`

echo "space info on "${BKP_HOST}":"
ssh ${BKP_HOST} "df -h /build1"

touch /data/bkpDone-${BKP_HOST}
