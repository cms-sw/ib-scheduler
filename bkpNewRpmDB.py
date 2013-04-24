#!/usr/bin/env python

import os, sys, time, socket


import os, sys, time, re

def doCleanup(plat, host):

    bkpDir = "/afs/cern.ch/cms/rpmDbBackupNew"

    os.chdir(bkpDir)
    
    files = os.listdir(".")

    today = time.strftime("%Y %m %d").split()
    print "today : ", today

    dateRe = re.compile("rpmDB-"+plat+"-"+host+"-(\d\d\d\d)(\d\d)(\d\d).tgz")

    for item in files :
        dateMatch = dateRe.match(item)
        if dateMatch:
            yr  = dateMatch.group(1)
            mon = dateMatch.group(2)
            day = dateMatch.group(3)
            
            if ( (yr  == today[0]) and
                 (mon == today[1]) and
                 ( int(today[2])-int(day) > 2 ) ): # keep last few days
                print "going to remove: ", item
                cmd = "rm -rf " + item
                print "in ",os.getcwd()," executing:", cmd
                ret = os.system(cmd)
                if ret != 0:
                    print "ERROR: cmd returned: ", ret
                    
    os.system('fs lq .')
    return

def doBackup(plat, host) :
    
    os.chdir("/build/cmsbuild/")

    tgt  = plat+'/'+host+"/rpm"
    
    stamp = time.strftime("%Y%m%d")
    
    bkpDir = "/afs/cern.ch/cms/rpmDbBackupNew"
    bkpFile = bkpDir + "/rpmDB-"+plat+"-"+host+"-"+stamp+".tgz"
    
    print "in ",os.getcwd()
    
    cmd = "tar zcf "+bkpFile+" "+tgt
    ret = os.system(cmd)
    
    print cmd, 'returned', ret

    os.system("ls -al "+bkpDir)

    return

if __name__ == "__main__" :

    hostFQN = socket.gethostname()
    host = hostFQN.split('.')[0]

    if host == "vocms155":
        for plat in [ "slc5_ia32_gcc434",
                      "slc5_amd64_gcc434",
                      "slc5_amd64_gcc451",
                      "slc5_amd64_gcc461" ]:
            doCleanup(plat, host)
            doBackup(plat, host)
    else:
        print "unknown host", hostFQN, 'nothing done.'

    
