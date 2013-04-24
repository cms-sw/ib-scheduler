#!/usr/bin/env python

import os, sys, time, subprocess


# ================================================================================

class ActionError(Exception):
    def __init__(self, msg):
        self.msg = msg
        return
    def __str__(self):
        return repr(self.msg)

#================================================================================

def doCmd(cmd, dryRun=False, inDir=None, usePopen=False):
    if not inDir:
        print "--> "+time.asctime()+ " in ", os.getcwd() ," executing ", cmd
    else:
        print "--> "+time.asctime()+ " in " + inDir + " executing ", cmd
        cmd = "cd " + inDir + "; "+cmd
	
    sys.stdout.flush()
    sys.stderr.flush()
        
    start = time.time()
    ret = 0
    if dryRun:
        print "DryRun for: "+cmd
    else:
        if usePopen:
            p = subprocess.Popen(cmd, shell=True)
            ret = os.waitpid(p.pid, 0)[1]
        else:
            ret = os.system(cmd)
            
    # do the logging before raising an Error
    stop = time.time()
    print "--> "+time.asctime()+" cmd took", stop-start, "sec. ("+time.strftime("%H:%M:%S",time.gmtime(stop-start))+")"
    sys.stdout.flush()
    sys.stderr.flush()
    
    if ret != 0 :
        msg = "ERROR: cmd returned :" + str(ret)
        raise ActionError(msg)

    return ret

