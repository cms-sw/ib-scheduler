#!/usr/bin/env python
 
import os, sys, time, stat, glob

# ================================================================================

class LocalCleaner(object) :
    def __init__(self, dirType, daysToKeep=None, dryRun=False):

        import sdtIbQaMap
        self.basePaths = []
        self.dirsToDelete = {}
        self.dryRun = dryRun
        if sdtIbQaMap.StdIBQAMap.has_key(dirType):
            self.basePaths = sdtIbQaMap.StdIBQAMap[dirType]['basePaths']
            self.dirsToDelete = sdtIbQaMap.StdIBQAMap[dirType]['dirsToDelete']
            if not daysToKeep: daysToKeep = sdtIbQaMap.StdIBQAMap[dirType]['daysToKeep']
            
        if not self.dryRun:
            import socket
            host = socket.gethostname().replace('.cern.ch','')
            #tmp hack to keep min release for slc6 i.e vocms117
	    if dirType == 'IBLocal' and host == 'vocms117': daysToKeep =1
            logFileName = os.path.join( os.environ['HOME'], 'cleanupLogs', 'localDiskCleanup'+dirType+'-'+host)
            if os.path.exists(logFileName):
                os.system('mv '+logFileName+ ' ' +logFileName+'.bkp')
            self.logFile = open( logFileName, 'w')

        self.DeleteThreshold = daysToKeep * 86400
        return
    
    # --------------------------------------------------------------------------------

    def __del__(self):
        if not self.dryRun:self.logFile.close()
        return

    # --------------------------------------------------------------------------------

    def log(self, msg):
        if not self.dryRun:
            self.logFile.write(msg)
        else:
            print msg
        return

    # --------------------------------------------------------------------------------

    def doCmd(self, cmd):
        self.log( "--> "+time.asctime()+ " in "+ os.getcwd() +" executing "+ cmd + "\n")
        
        start = time.time()
        ret = 0
        if self.dryRun:
            self.log( "DryRun for: "+cmd + "\n")
        else:
            ret = os.system(cmd)
            
        stop = time.time()
        self.log( "--> "+time.asctime()+" cmd took " +str(stop-start) +" sec. ("+time.strftime("%H:%M:%S",time.gmtime(stop-start))+")"  + "\n")
    
        return ret
    
    # --------------------------------------------------------------------------------

    def cleanArea(self, sudo=False) :
        utype = 'own'
	if sudo: utype = 'sudo'
	for xbase in self.basePaths:
            if not os.path.exists(xbase): continue
            for xdir in self.dirsToDelete[utype]:
                for localPath in glob.glob(xbase+'/'+xdir):
                    try:
                        if not self.cleanLocalDiskArea(localPath, sudo): continue
                    except:
                        continue 
                    self.log( '\n--------------------------------------------------------------------------------' + "\n")        
                    if self.dryRun: continue
                    self.log( '\n' + "\n")
                    cmd = '/bin/df -h ' + xbase
                    pipe = os.popen(cmd)
                    lines = pipe.readlines()
                    pipe.close()
                    self.log('usage for '+xbase+'\n')
                    for line in lines: self.log(line)
                    self.log( '\n' + "\n")
        return
    
    # --------------------------------------------------------------------------------

    def cleanLocalDiskArea(self, localPath, sudo) :
        difftime = time.time() - os.path.getmtime(localPath)
        if difftime < self.DeleteThreshold: return False

        self.log( '\ncleaning out in '+ localPath + "\n")
        self.log( localPath+ ' is now ' + str(difftime/float(86400)) + ' days old.' + "\n")
        cmd = ' rm -rf ' + localPath
        if sudo: cmd = 'sudo '+cmd
        self.doCmd(cmd)
        return True

# ================================================================================

def usage():
    print "usage: ", os.path.basename(sys.argv[0])," --type <type> [--dryRun] [--days <days>] [--sudo]"
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
    dType = None
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

    if dType:
        ac = LocalCleaner(dType, days, dryRun)
        ac.cleanArea(sudo)

