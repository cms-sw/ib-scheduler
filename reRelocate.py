#!/usr/bin/env python

import os, sys, glob, time, stat

oldPath = '/afs/.cern.ch/cms'
newPath = '/afs/cern.ch/cms'

maxAge = 1*24*60*60
maxAge = 1*60*30

def doCmd(cmd):

    print cmd
    ret = os.system(cmd)
    if ret != 0:
        print "ERROR from ", cmd, 'ret=', ret
        sys.exit(-1)

def reRelocateFile(fileName):

    # do not reRelocate the scram binary itself, it contains the path
    # to the scramdb which needs to be writeable for future additions
    # of releases.
    if fileName.strip().endswith('/bin/scram') : return

    cmd = 'sed -i -e "s|'+oldPath+'|'+newPath+'|g" '+fileName.strip()
    doCmd(cmd)
    
    return

def reRelocateDir(dirName):

    if os.path.exists(dirName+'/.SCRAM'):
        reRelocateDirRel(dirName)
    else:
        reRelocateDirNonRel(dirName)
    
def reRelocateDirRel(dirName):

    chkDirs = ['.SCRAM', 'config', 'etc', 'python']
    for chkDir in chkDirs:
        reRelocateDirFiles(os.path.join(dirName, chkDir))

    reRelocateScramToolFiles(dirName)    
            
def reRelocateDirNonRel(dirName):
    reRelocateDirFiles(dirName)

def reRelocateDirFiles(dirName):
    cmd = "find "+dirName+' -type f  -exec grep -H -c "'+oldPath+'" {} \;'
    pIn = os.popen(cmd)

    fileList = pIn.readlines()
    for one in fileList:
        try:
            fName, count = one.split(':')  
            if int(count) == 0: continue
            reRelocateFile(fName)
        except Exception, e:
            print "error splitting ", one
            print "      got : ", str(e)
            pass

def reRelocateScramToolFiles(dirIn):
    
    if not os.path.exists(dirIn+'/.SCRAM'): return

    cmd = 'find ' + dirIn + '/.SCRAM  -name *db.gz '
    pIn = os.popen(cmd)

    fileList = pIn.readlines()
    for fNameIn in fileList:
        fName = fNameIn.strip()
        cmd = 'gunzip -c '+fName.strip()+' | sed -e "s|'+oldPath+'|'+newPath+'|g" | gzip >tmpFile ; mv tmpFile '+fName.strip()
        doCmd(cmd)

def fixSymLinks(dirIn):
    
    from subprocess import Popen, PIPE
    cmd = 'find '+dirIn+ '  -type l '
    print cmd
    pIn = os.popen(cmd)

    fileList = pIn.readlines()
    for lNameIn in fileList:
        lName = lNameIn.strip()
        if lName.endswith('var/lib/rpm'): continue
        try:
            tgt = os.readlink(lName.strip())
            if tgt[0] == '/':
                newTgt = tgt.replace(oldPath,newPath)
                try:
                    os.unlink( lName.strip() )
                    os.symlink( newTgt, lName.strip() )
                    print 'reset symlink : '+lName.strip()+' -> '+newTgt
                except Exception, e:
                    print "ERROR unlinking/resymlinking ",lName, newTgt, ' got ', str(e)
                    
                # cmd = 'rm '+lName.strip()+'; ln -s '+newTgt+' '+lName
                # doCmd(cmd)
        except Exception, e:
            print "ERROR relocating symlink for ", lName, 'got:', str(e)
            pass

def reRelocateAll():

    os.chdir('/afs/.cern.ch/cms')
    
    print "in ", os.getcwd()

    arch = os.environ['SCRAM_ARCH']

    # get the dirs down to the version level, so we can check later
    inList = ['external', 'lcg', 'cms']
    dirList = []
    for inDir in inList:
        dirList += glob.glob(arch + '/'+inDir+'/*/*')

    # top level general :
    reRelocateFile('cmsset_default.sh')
    reRelocateFile('cmsset_default.csh')
    reRelocateDir('bin')
    reRelocateDir('common')

    # now the selected arch:
    for dir in dirList:
        if '/apt/' in dir : continue
        if '/rpm/' in dir : continue

        age = time.time() - os.stat(dir)[stat.ST_MTIME]
        if age > maxAge:
            print " ignoring old ", dir, ' age ', age
            continue # ignore previous installations to reduce the load on the server
        print " processing ", dir, ' age ', age
        reRelocateDir(dir)
        fixSymLinks(dir)

    # make sure the scram DB get's updated as well (as the dir may be too "old"):
    reRelocateDir(arch + '/' + 'lcg/SCRAMV1') 

    

reRelocateAll()


                                
