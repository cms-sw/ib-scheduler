#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import doCmd
import errno
import threading
import time
import tagCollectorAPI
import socket
import re

EMAIL_ADDR = "cmssdt-ibs@cern.ch"
# ================================================================================

def format(s, **k): 
  return s % k 

def die(s):
  print s
  sys.exit(1)

class BuildIB(object):
        
    def __init__(self, rel=None, arch=None, buildDir=None, noMail=False, dryRun=False, logFile=None, dryBuild=False, pid=None):
        if rel == None or arch == None:
            self._initArgs()
        else:
            self.rel = rel
            self.arch = arch
            self.buildDir = buildDir
            self.noMail = noMail
            self.dryRun = dryRun
            self.logFile = logFile
            self.pid = pid
        
        self.dryBuild = dryBuild
        self._initProps()
        self._cleanupOldTempDirs()
        self._deletePIDTempDirs()
        self._createTempDirs()
        self._setLogger()
        sys.stdout = self.logger
        sys.stderr = self.logger

    def __del__(self):
        if 'logger' in self.__dict__:
            self.logger._appendLogToFile(self.generalLogsFile) 
            if not self.noMail and '_arch' in self.__dict__ and 'cycname' in self.__dict__:
                cmd = 'cat ' + self.logger.logPath + ' | mail -s "IB for ' + self.cycname + '_X on ' + self._arch + ' finished" ' + EMAIL_ADDR
                doCmd.doCmd(cmd, dryRun=self.dryRun)
        self._deletePIDTempDirs()
    
    def _cleanupOldTempDirs(self):
        print "About to cleanup old temp directories ..."
        if 'scriptDir' in self.__dict__: 
            self._deleteStaleTempDirsHelper(self.scriptDir)
        if 'logDir' in self.__dict__: 
            self._deleteStaleTempDirsHelper(self.logDir)
    
    def _deleteStaleTempDirsHelper(self, childDir):
        daysToKeep = 2
        delDirOlder = time.time() - (86400 * daysToKeep)
        parentDir = os.path.dirname(childDir)
        listDir = os.listdir(parentDir)
        for dir in listDir:
            full_dir = os.path.join(parentDir, dir)
            if ( dir.isdigit() or (dir.startswith('p') and dir[1:].isdigit()) ) and os.path.isdir(full_dir) and os.path.getctime(full_dir) <= delDirOlder:
                shutil.rmtree(full_dir, True)
                print "%s is deleted " % str(full_dir)

    def _deletePIDTempDirs(self):
        print "About to delete temp directories with current pid ..."
        if 'scriptDir' in self.__dict__:
            shutil.rmtree(self.scriptDir, True)
            print "Deleted scriptDir %s" % str(self.scriptDir)
        if 'logDir' in self.__dict__: 
            shutil.rmtree(self.logDir, True)
            print "Deleted logDir %s" % str(self.logDir)

    def _createTempDirs(self):
        os.makedirs(self.scriptDir)
        os.makedirs(self.logDir)

    def _setLogger(self):
        import IBLogger
        self.logger = IBLogger.IBLogger(filename=self.logFile)

    def usage(self):
        print 'usage: ', os.path.basename(sys.argv[0]), \
            ' --releasecycle <rel> --architectures <arch> [--buildDir <dir>] [--logfile <logfile>] [--dryRun] [--nomail]'
        return

    def checkoutIBScripts(self):
        scriptPath = os.curdir
        import tagCollectorAPI as tc
        externals = tc.getReleaseExternal("CMSSW_"+self.cycname+"X", self._arch)
        svn_branch = 'trunk'
        if externals.has_key('INTBUILD'):
          svn_branch = externals['INTBUILD']
          if svn_branch == '': svn_branch = 'trunk'
        for d in ("IB", "scripts"):
          cmd = 'cd ' + self.scriptDir+'; svn -q co http://svn.cern.ch/guest/CMSIntBld/'+svn_branch+'/IntBuild/'+d
          doCmd.doCmd(cmd, dryRun=self.dryRun)
        return os.path.join(self.scriptDir, 'IB')

    def _doBuild(self, ib_scripts_path, ibName):
        if ib_scripts_path not in sys.path:
            sys.path.append(ib_scripts_path)

        (ibdate, ibstamp) = self.getIbdateIbstamp(ibName)
        
        print "\nIB stamp=%s\n" % str(ibstamp)
        print "\nIB self.cycname=%s\n" % str(self.cycname)
        print "\nIB self.cycname dot=%s\n" % str(self.cycname.replace('_', "."))
        print "\nIB self._arch=%s\n" % str(self._arch)
        print "\nIB ibName=%s\n" % str(ibName)
            
        sys_argv0_orig = sys.argv[0] 
        sys.argv[0] = os.path.join(ib_scripts_path, "buildManager.py")
            
        pwdOrig = os.getcwd()
        os.chdir(self.buildDir)
            
        import buildManager

        self.bmgr = buildManager.BuildManager(self.cycname.replace('_', "."), ibdate,
                    ibstamp)
        self.bmgr.setDryRun(self.dryRun)
        self.bmgr.checkout()
        self.bmgr.startBuild()
            
        sys.argv[0] = sys_argv0_orig
        os.chdir(pwdOrig)

    def startIbTestsWatcher(self, ib_scripts_path):
        print "Starting testWatcher"
        cmd = str(os.path.join(ib_scripts_path,'testWatcher.py')) + ' --pid ' + str(os.getpid()) + ' >> ' + str(self.logger.getLogFilePath()) + '.TestWatcher 2>&1 3>&1 &'
        doCmd.doCmd(cmd, dryRun=self.dryRun, usePopen=True)
        print "The testWatcher started"
        
    def startIBCancellationWatcher(self, ib_scripts_path, request_id):
        print "Starting IB Cancellation Watcher"
        cmd = str(os.path.join(ib_scripts_path,'IBCancellationWatcher.py')) + ' --request_id ' + str(request_id) + ' --pid ' + str(os.getpid()) + ' >> ' + str(self.logger.getLogFilePath()) + '.IBCancellationWatcher 2>&1 3>&1 &'
        doCmd.doCmd(cmd, dryRun=self.dryRun, usePopen=True)
        print "The IB Cancellation Watcher started"
            
    def checkIBScriptsPath(self, ib_scripts_path):
        if not os.path.exists(ib_scripts_path):
            print 'The directory with IB scripts [' + ib_scripts_path \
                + "] doesn't exists. Check it's checkout from svn..."
            sys.exit(errno.ENOENT)

    def isIBBuilt(self, ibName):
        builtIBs = []
        path = self.buildDir + '/cms/' + self._arch + '/cms/cmssw'
        try:
            builtIBs = os.listdir(path)
        except OSError:
            print 'OSError: cannot list ' + path
            return False
        return ibName in builtIBs

    def _initArgs(self):
        import getopt
        options = sys.argv[1:]

        try:
            (opts, args) = getopt.getopt(options, 'hnmb:r:a:l:', ['help',
                    'dryRun', 'nomail', 'buildDir=', 'releasecycle=',
                    'architectures=', 'logfile=', 'pid='])
        except getopt.GetoptError, e:
            print e.msg
            self.usage()
            sys.exit(-2)

        self.dryRun = False
        self.rel = None
        self.buildDir = None
        self.arch = None
        self.noMail = False
        self.logFile = None
        self.pid = None

        for (o, a) in opts:
            if o in ('-h', '--help'):
                self.usage()
                sys.exit()

            if o in ('-n', '--dryRun'):
                self.dryRun = True

            if o in ('-r', '--releasecycle'):
                self.rel = a

            if o in ('-b', '--buildDir'):
                self.buildDir = a

            if o in ('-a', '--architectures'):
                self.arch = a
            
            if o in ('-l', '--logfile'):
                self.logFile = a
            
            if o in ('-m', '--nomail'):
                self.noMail = True
            
            if o in ('-p', '--pid'):
                self.pid = a
    
    def _initProps(self):

        if not self.buildDir:
            self.diskdir = '/build1'
            if not os.path.exists(self.diskdir):
                self.diskdir = '/build'
            self.buildDir = os.path.join(self.diskdir, 'intBld')

        if not self.pid:
            self.pid = str(os.getpid())
        self.scriptDir = os.path.join(self.buildDir, 'IntBuild', self.pid)
        self.logDirGeneral = os.path.join(self.buildDir, 'logs')
        if not os.path.exists(self.scriptDir):
            os.makedirs(self.scriptDir)
        if not os.path.exists(self.logDirGeneral):
            os.makedirs(self.logDirGeneral)
        self.logDir = os.path.join(self.logDirGeneral, self.pid)
        if not self.logFile:
            self.logFile = os.path.join(self.logDir, 'intBld.log')
        self.generalLogsFile = os.path.join(self.logDirGeneral,
                'allIntBld.log')

    def isIBLocked(self):
        from Lock import Lock
        self.lock = Lock(os.path.join(self.buildDir, 'buildLock'))
        return not self.lock

    def getIbdateIbstamp(self, dateStr):
        import re
        from datetime import date
        regex = \
            re.compile('^CMSSW\w*(\d\d\d\d)-(\d\d)-(\d\d)-(\d\d\d\d)*$')
        m = regex.match(dateStr)
        weekDays = (
            'mon',
            'tue',
            'wed',
            'thu',
            'fri',
            'sat',
            'sun',
            )
        if m:
            return (m.group(1) + '-' + m.group(2) + '-' + m.group(3)
                    + '-' + m.group(4), weekDays[date(int(m.group(1)),
                    int(m.group(2)), int(m.group(3))).weekday()] + '-'
                    + m.group(4)[:len(m.group(4))-2])
        return (None, None)
    
    def getReleaseCycleByReleaseName(self, release_name):
        print "release_name = %s" % (release_name)
        g = re.match("CMSSW_([0-9]*)_([0-9]*)(_[A-Za-z][A-Za-z]+|)_([0-9X]*).*", release_name).groups()
        if not g:
            die("Invalid release name.")
        return format("%(major)s_%(minor)s%(extra)s",
                      major=g[0],
                      minor=g[1],
                      extra=g[2])

    def build(self):
        print 'Starting IB building process'
        print 'Checking the build lock...'
        if self.isIBLocked():
            from socket import gethostname
            print 'The lock is found!'
            print 'WARNING: A build is still running on ' + gethostname()
            self.noMail = True
        else:
            tryAgain = True
            maxSleep = 30*60
            sleep_time = 60
            while(tryAgain):
                tryAgain = False
                print 'Lock is not found!'
                print 'Will check new IB existence ...'
                data = tagCollectorAPI.getIBPendingRequests(self.rel, self.arch,
                    dryRun=self.dryRun)
                if data == None:
                    print "Pending IB requests are not found, exiting"
                    self.noMail = True
                    sys.exit(0)
                ibName = data['release_name']
                self._arch = data['architecture_name']
                self.cycname = self.getReleaseCycleByReleaseName(ibName)
                print "self.cycname=%s" % (self.cycname)
                
                if ibName == None or ibName.strip() == "":
                    print "Pending requests are not found. Stopping the build..."
                    sys.exit(0)
                elif not self.isIBBuilt(ibName):
                    print 'Request found for release ' + ibName + " and architecture " +  self._arch
                    print 'Will set status of the request to Building'
                    isIBRequestSetAsBuild = tagCollectorAPI.setRequestBuilding(data['id'], ibName, machine=socket.gethostname(), pid=os.getpid())
                    if not isIBRequestSetAsBuild:
                        print "Couldn't set the type of IB request " + str(data['id']) + " to Building... Will search for pending requests again..."
                        time.sleep(sleep_time)
                        maxSleep -= sleep_time
                        if maxSleep>0:
                            tryAgain = True
                        else:
                            print "Max sleep time has been reached, will stop the script"
                            sys.exit(0)
                        continue
                    try:
                        os.environ['SCRAM_ARCH'] = self._arch
                        ib_scripts_path = self.checkoutIBScripts()
                        self.checkIBScriptsPath(ib_scripts_path)
                        self.startIbTestsWatcher(ib_scripts_path)
                        self.startIBCancellationWatcher(ib_scripts_path, data['id'])
                        if not self.dryBuild:
                            self._doBuild(ib_scripts_path, ibName)
                        isSetToFinished = False
                        
                        while not isSetToFinished and maxSleep>0:
                            isSetToFinished = tagCollectorAPI.finishRequest(data['id'], 0,0,0,0,'http://cmssdt.cern.ch/SDT/cgi-bin/showIB.py')
                            if not isSetToFinished:
                                time.sleep(sleep_time)
                                maxSleep -= sleep_time
                    except:
                        isSetToFailed = False
                        while not isSetToFailed and maxSleep>0:
                            isSetToFailed = tagCollectorAPI.failRequest(data['id'], 0,0,0,0,'')
                            if not isSetToFailed:
                                time.sleep(sleep_time)
                                maxSleep -= sleep_time
                else:
                    print 'IB ' + ibName \
                        + ' has been already built here... Exiting'
                    self.noMail = True

def main():
    builder = BuildIB()
    builder.build()
    sys.exit(0)

if __name__ == '__main__':
    main()

