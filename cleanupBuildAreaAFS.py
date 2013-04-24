#!/usr/bin/env python
 
import os, sys, time, stat

scriptPath = os.path.dirname( os.path.abspath(sys.argv[0]) )
if scriptPath not in sys.path:
    sys.path.append(scriptPath)


# ================================================================================

def usage():
    print "usage: ", os.path.basename(sys.argv[0])," [--platform <arch>] [--dryRun]"
    return

def main():

    import getopt
    options = sys.argv[1:]
    try:
        opts, args = getopt.getopt(options, 'h', 
                                   ['help','dryRun','platform='])
    except getopt.GetoptError:
        usage()
        sys.exit(-2)

    dryRun = False
    plats = ['slc*','osx*']
    
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
            
        if o in ('--dryRun',):
            dryRun = True

        if o in ('--platform',):
            plats = a.split(',')

    if len(plats)>0:
        scriptDir = '/tmp/IntBuild'
        cmd = 'rm -rf '+scriptDir+'; mkdir -p '+scriptDir+'; svn -q co http://svn.cern.ch/guest/CMSIntBld/trunk/IntBuild/IB '+scriptDir+'/IB'
        ret = os.system(cmd)
        script = scriptDir+'/IB/cleanupAFS.py '
        for plat in plats:
            cmd = script+' --plat "'+plat+'"'
            print "going to execute:", cmd
            ret = os.system(cmd)
            if ret != 0:
                 print "Error ", ret, ' from command ',cmd
        os.system('rm -rf '+scriptDir)

if __name__ == "__main__" :
    main()
