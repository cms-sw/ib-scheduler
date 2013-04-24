#!/usr/bin/env python

import os, sys, time, socket


import os, sys, time, re

def doCleanup(plat):

    bkpDir = "/afs/cern.ch/cms/rpmDbBackup"

    os.chdir(bkpDir)
    
    files = os.listdir(".")

    today = time.strftime("%Y %m %d").split()
    print "today : ", today

    dateRe = re.compile("rpmDB-"+plat+"-(\d\d\d\d)(\d\d)(\d\d).tgz")

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

def doBackup(plat) :
    
    os.chdir("/build/cmsbuild/")

    # set default: slc4_ia32_gcc345
    tgt  = "slc4_ia32_gcc323/rpmDatabase/rpm"
    if (plat == "slc4_ia32_gcc345") :
        tgt  = "slc4_ia32_gcc323/rpmDatabase/rpm"
    elif (plat == "slc3_ia32_gcc323") :
        tgt = "slc3rpm/var/lib/rpm"
    elif (plat == "slc5_ia32_gcc434") :
        tgt = "rpm/"+plat
    elif (plat == "slc5_amd64_gcc434") :
        tgt = "rpm/"+plat
    
    stamp = time.strftime("%Y%m%d")
    
    bkpDir = "/afs/cern.ch/cms/rpmDbBackup"
    bkpFile = bkpDir + "/rpmDB-"+plat+"-"+stamp+".tgz"
    
    print "in ",os.getcwd()
    
    cmd = "tar zcf "+bkpFile+" "+tgt
    ret = os.system(cmd)
    
    print cmd, 'returned', ret

    os.system("ls -al "+bkpDir)

    return

if __name__ == "__main__" :

    # set default:
    plat = "slc4_ia32_gcc345"
    
    host = socket.gethostname()

    if host[:10] == "lxbuild150":
        plat = "slc5_ia32_gcc434"    
        doCleanup(plat)
        doBackup(plat)
        plat = "slc5_amd64_gcc434"    
        doCleanup(plat)
        doBackup(plat)
    else:
        plat = "slc4_ia32_gcc345"
        doCleanup(plat)
        doBackup(plat)
        

    
