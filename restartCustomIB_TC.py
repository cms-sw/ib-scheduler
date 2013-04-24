#!/usr/bin/env python

import socket, os, sys, time
scriptPath = os.path.dirname(os.path.abspath(sys.argv[0]))

def restartCIB(platf):
    host = socket.gethostname().split('.')[0]
    
    hostDir = os.path.join('/build/cmsbuild/customIB_TC/',platf,host)
    if not os.path.exists(hostDir):
        os.makedirs(hostDir)
        
    pidFileName  = hostDir + '/cib.pid'
    stopFileName = hostDir + '/cib.stop'
    logFileName  = hostDir + '/cib.log'
    
    # tell running process to stop
    os.system('touch '+stopFileName)

    time.sleep(20) # just wait a bit before continuing and checking ...
    
    pidFound = True
    pid = -1
    try:
        pidFile = open(pidFileName, 'r')
        lines = pidFile.readlines()
        pidFile.close()
        pid = lines[0][:-1]
    except IOError:
        pidFound = False
        
    while pidFound:
        print '.',
        sys.stdout.flush()
        psPipe = os.popen('ps -o args= -p '+pid)
        stat = psPipe.readlines()
        print len(stat),stat
        if len(stat) == 0 :
            print "Process no longer running"
            break
        elif 'processCustomIBRequest' not in stat[0]:
            print 'ERROR did not find correct process for pid', pid
            raise "ABORTING"

        time.sleep(60) # the process checks every 15 sec, so wait a bit longer
    
    print "old process stopped successfully."
    
    # cleanup - just in case ...
    os.system('rm -f '+stopFileName)
    
    # rotate log file
    stamp = time.strftime('%Y%m%d-%H%M')
    os.system('mv '+logFileName+ ' '+logFileName+'-'+stamp)
    os.system('gzip '+logFileName+'-'+stamp)
    
    cmsPath = None
    try:
        cmsPath = os.environ['CMS_PATH']
    except KeyError:
        print "CMS_PATH not found, fallling back to hardcoded version"
        cmsPath = '/afs/cern.ch/cms'
    
        if not cmsPath:
            print "FATAL ERROR: could not determine cmsPath !! ABORTING. ", sys.argv[0]
            sys.exit(-1)
    
    cmd = "export PATH="+cmsPath+"/bin:${PATH} ;"
    cmd += 'source '+cmsPath+'/cmsset_default.sh;'
    cmd += 'nohup '+scriptPath+'/processCustomIBRequest_TC.py --plat '+platf+' >>'+hostDir+'/cib.log 2>&1 '
    ret = os.system(cmd)
    print "restart cmd finished with ret = ", ret

def Usage(msg):
    print msg
    print "\nusage: ",sys.argv[0]," --platform <plat> "
    sys.exit(-1)

def main(argv=None):

    import getopt
    if argv is None:
        argv = sys.argv

    try:
        opts, args = getopt.getopt(argv[1:], "hv", ["help",'platform='])
    except getopt.error, msg:
        raise Usage(msg)

    # option processing
    platf = None
    
    for option, value in opts:
        if option == "-v":
            verbose = True
        if option in ("-h", "--help"):
            raise Usage(help_message)
        if option in ('--platform',):
            platf = value

    if not platf:
        msg = "ERROR required option platform not given !"
        raise Usage(msg)

    restartCIB(platf)

# ================================================================================

if __name__ == "__main__":
	sys.exit(main())
