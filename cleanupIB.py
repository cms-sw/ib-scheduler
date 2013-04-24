#!/usr/bin/env python
 
import os, sys, time, stat
# ================================================================================

from threading import Thread
class CleanupThread(Thread):
    def __init__(self, cmdIn):
        Thread.__init__(self)
        self.cmd = cmdIn
	self.stime = time.time()
	self.jobDone = False
        return

    def jobTime(self):
        return  time.time()-self.stime
	
    def run(self):
        print 'Cleanup> Started: '+self.cmd
	os.system(self.cmd)
	print 'Cleanup> Done: '+self.cmd
        return

# ================================================================================

def cleanArea(dirType, daysToKeep=None, dryRun=False, sudo=False):
    cmdargs =  os.path.dirname(os.path.abspath(sys.argv[0]))+"/cleanupDirs.py --type "+dirType
    if sudo:       cmdargs += " --sudo "
    if dryRun:     cmdargs += " --dryRun "
    if daysToKeep: cmdargs += " --days "+str(daysToKeep)
    thrds = []
    import commands
    boxes=commands.getoutput("acrontab -l | grep -v '^ *#' | grep '/buildIB.py' | awk '{print $6}' | sort | uniq").split('\n')
    for box in boxes:
        box = box.strip()
	cmd = "ssh "+box+" "+cmdargs
       	thd = CleanupThread(cmd)
        thrds.append(thd)
       	thd.start()
    
    hasActive = True
    maxTime = 60*30
    while (hasActive):
        time.sleep(60)
        hasActive = False
        for thd in thrds:
            if not thd.isAlive(): continue
            if thd.jobTime()<maxTime:
                hasActive = True
                continue
            try:
                thd._Thread__stop()
            except:
                pass
    return
    
# ================================================================================

def usage():
    print "usage: ", os.path.basename(sys.argv[0])," [--type <type>] [--dryRun] [--days <days>] [--sudo]"
    return

if __name__ == "__main__" :
    import getopt
    options = sys.argv[1:]
    try:
        opts, args = getopt.getopt(options, 'h', 
                                   ['help','dryRun','sudo','type=', 'days='])
    except getopt.GetoptError:
        usage()
        sys.exit(-2)

    dryRun = False
    dType = 'IBLocal'
    days = None
    sudo = False
    
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
            
        if o in ('--dryRun',):
            dryRun = True
        if o in ('--type',):
            dType = a
        if o in ('--days',):
            days = int(a)
        if o in ('--sudo',):
            sudo = True

    cleanArea(dType, days, dryRun, sudo)
