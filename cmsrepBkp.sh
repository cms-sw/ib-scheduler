#!/usr/bin/env bash

export LOG_FILE=/data/cmsrepBkp.log
if [ -e ${LOG_FILE} ] ; then 
   mv $LOG_FILE $LOG_FILE.bkp
fi

script_dir=`dirname $0`
${script_dir}/do_cmsrepBackup.sh >$LOG_FILE 2>&1

# ret=$?
# if [ $ret != 0 ] ; then
cat ${LOG_FILE} | mail -s "[log] cmsrep backup finished" eulisse@mail.cern.ch
# fi
