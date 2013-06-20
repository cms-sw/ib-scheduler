#!/usr/bin/env python
# encoding: utf-8
"""
customIB.py

Created by Andreas Pfeiffer on 2008-05-29.
Copyright (c) 2008, 2009 CERN. All rights reserved.
"""

import sys
import getopt
import os, pwd
import time, socket
from stat import *

import sendMail

import tagCollectorAPI as tc

scriptPath = os.path.dirname( os.path.abspath(sys.argv[0]))

# ================================================================================

def informRequestor(addrTo, msg, platf):
    addrFrom = "cmsbuild@cern.ch"
    subj     = '[cib] results from customIB ('+platf+')'
    sendMail.sendMail(addrFrom, addrTo, subj, msg)
    return
		
# ================================================================================

class ServerError(Exception):
    def __init__(self, msg=''):
        Exception.__init__(self)
        self.msg = msg

# ================================================================================
    
class WebBasedRequestManager(object):
		
    def __init__(self):
        self.reset()
        self.doDeBuG = True
        self.platf = None

    # --------------------------------------------------------------------------------
		
    def reset(self):
        
	self.ref       = None
	self.tagList   = {}
        self.user      = {}
        self._stamp    = None
        self.id        = -1
        
    # --------------------------------------------------------------------------------
    
    def getLatestIB(self, queue):

        cmd =  'export SCRAM_ARCH='+self.platf+';'
        cmd += "scram list -c CMSSW | sort | grep '/"+queue+"_20' | awk '{print $3}' | tail -1"
        print "looking for latest in ", queue, ":", cmd
        pipe = os.popen(cmd)
        line = pipe.readlines()[0]
        pipe.close()
        line = os.path.basename(line.strip())
        if not line:
          raise("ERROR: Can not find release for queue "+queue+" for arch "+self.platf)

        return line

    # --------------------------------------------------------------------------------
		
    def getUserInfo(self, ret):
        self.user = { 'id' :   ret['author'],
                      'name' : ret['full_name'],
                      'mail' : ret['email'],
                      }

    # --------------------------------------------------------------------------------
		
    def getNewRequest(self, plat, jobId=None):

        self.reset()
        self.platf = plat

        ret = None
        if not jobId:
            try:
                ret = tc.getPendingRequests(architecture_pattern=plat,requestType="CIB")
                print "ret=" + str(ret)
                if not ret:
                    return None  # no requests pending at the moment
            except Exception, e:
                if 'Unable to perform' in str(e):
                    print "ERROR from TC - retrying ..."
                    return None   # assume temporary downtime of TC, retry later ... 
                print "Error getting request : "+str(e) 
                raise # unknown error, re-throw

        else:
            try:
                ret = tc.getRequestData(jobId)
            except Exception, e:
                if 'Unable to perform' in str(e):
                    print "ERROR from TC - retrying ..."
                    return None   # assume temporary downtime of TC, retry later ... 
                print "Error getting request for id "+jobId+": "+str(e) 
                raise # unknown error, re-throw
            

        if self.doDeBuG:
            print "--> got:", ret

        # map over the params ...
        self.id   = int(ret['id'])
        self.ref  = ret['release_name']
        latestIB = False
        if self.ref[-2:] == '_X' : latestIB = True
        
        if latestIB:
            try:
                self.ref = self.getLatestIB(self.ref)
            except Exception, e:
                print "ERROR when trying to find latest IB, aborting"
                print str(e)
                tc.commentRequest(self.id,"ERROR: Could not find latest IB for "+self.ref)
                self.setStatusBuilding(self.ref)
                tc.failRequest(self.id)
                informRequestor([ret['email']],"Sorry, can not process your custom IB request "+str(ret['id'])+" due to missing IB "+self.ref+" for SCRAM_ARCH "+plat,plat)
                return False
                
        self.tagList = ret['tags']
        self._stamp  = str(self.id)
        self.getUserInfo(ret)

        if self.doDeBuG:
            print "found request id ",self.id," for:"
            print "\tIB   :",self.ref
            print "\tuser :",self.user
            print "\tstamp:",self._stamp
            print "\ttags :"
            for p,t in self.tagList.items():
                print "\t",p, t
            print "\tuser-tests:"

        if not jobId:
            self.setStatusBuilding(self.ref)

        return True
    
    # --------------------------------------------------------------------------------
		
    def name(self):
        return self.id
    
    # --------------------------------------------------------------------------------

    def uploadLogs(self, logDirName, nWarn, nErr, tFail, tPass, utFail, utPass, topURL):
        self.doDeBuG = True
        print 'setting status to done'
        tc.finishRequest(request_id=self.id, build_errors=nErr, build_warnings=nWarn, tests_failed=tFail, tests_passed=tPass, results_url=topURL, unit_tests_passed=utPass, unit_tests_failed=utFail)
        sys.stdout.flush()
        sys.stderr.flush()

    # --------------------------------------------------------------------------------
    def setStatusBuilding(self, rel):
        if self.doDeBuG: print 'setting status to building for', self.id, rel
        tc.setRequestBuilding(request_id=self.id, release_name=rel, machine=socket.gethostname(), pid=os.getpid())
        sys.stdout.flush()
        sys.stderr.flush()
        
# ================================================================================
class CustomIBProcessor(object):
    """docstring for CustomIBProcessor"""
    def __init__(self, uploadOnly=False, user=None, jobId=None, platform=None):

        self.reset()

        self.uploadOnly = uploadOnly
        self.user       = user
        self.jobId      = jobId

        self.platf = platform
        if not self.platf:
            self.platform = 'slc4_ia32_gcc345'
        
        self.topDir = '/build/cmsbuild/customIB_TC/'+self.platf

        import socket
        self.hostName = socket.gethostname()
        if '.' in self.hostName:
            self.hostName = self.hostName.split('.')[0]

        hostDir = os.path.join( self.topDir, self.hostName)
        if not os.path.exists( hostDir ):
            print "creating dir ",hostDir
            os.makedirs(hostDir)

        self.stopFileName = os.path.join(hostDir, 'cib.stop')
        self.pidFileName = os.path.join(hostDir, 'cib.pid')
        self.pid = str( os.getpid() ) # we need the string version anyway

        self.reqMgr = None
        
        self.errWarn = {}
        self.logURL = 'http://cern.ch/cms-sdt/sdtInternal/customIB/'

        try:
            self.reqMgr = WebBasedRequestManager()
        except ServerError, e:
            print str(e)
            pass

        self._runTests = True
        self.topWebDir = None
                
        return

    # --------------------------------------------------------------------------------

    def __delete__(self):
        del self.reqMgr
        self.reqMgr = None
        pass
    
    # --------------------------------------------------------------------------------

    def reset(self):
        
        return
    
    # --------------------------------------------------------------------------------
		
    def stopRequested(self):

        if os.path.exists( self.stopFileName ):
            return True

        return False
    
    # --------------------------------------------------------------------------------
		
    def isRunning(self):

        if not os.path.exists( self.pidFileName ):
            pidFile = open(self.pidFileName, 'w')
            pidFile.write(self.pid +'\n')
            pidFile.close()
            return False # no process was running yet on the machine
        else:
            pidOther = open(self.pidFileName, 'r').readlines()[0].strip()
            pipe = os.popen('ps -o args= -p ' + pidOther )
            lines = pipe.readlines()

            if ( (len(lines) > 0) and ('processCustomIBRequest' in lines[0]) ):
                print "process already running on "+self.hostName+" pid=", pidOther
                return True
            else:
                print "found orphaned pid file ("+pidOther+") overriding ..."
                return False
        
        return False
    
    # --------------------------------------------------------------------------------
		
    def runTests(self):

        self._runTests = True

        return
    
    # --------------------------------------------------------------------------------
	
    def getNumberOfCPUs(self):
        try:
            res = open('/proc/cpuinfo').read().count('processor\t:')
            if res > 0:
                return str(res)
        except IOError:
            print "IOError occured, will use POSIX to find out nr of procs"
            return str(os.sysconf('SC_NPROCESSORS_ONLN'))
        
    # --------------------------------------------------------------------------------
    	
    def action(self):

        self.show()

        startDir = os.getcwd()
        
        topDir = self.topDir
        buildDir = os.path.join(topDir,self.user['id'],self._stamp)
        
        # make sure we start in a clean environment: remove any old build area
        if os.path.exists(buildDir):
            os.system('rm -rf '+buildDir)
            
        os.makedirs(buildDir)
            
        os.chdir(buildDir)

        testNames = ['runTheMatrix.py -s -i all', 'runTheMatrix.py --command "-n 200" -l 4.22', 'addOnTests.py']
        #testNames = ['runTheMatrix.py -s -i all', 'addOnTests.py']
        
        logFileName = os.path.join(os.getcwd(), 'customIB-build-'+self._stamp+'.log')
        dqmLogName  = os.path.join(os.getcwd(), 'customIB-dqm-'+self._stamp+'.log')
        testLogName  = os.path.join(os.getcwd(), 'customIB-tests-'+self._stamp+'.log')

        topAFS = os.path.join('/afs', 'cern.ch', 'cms', 'sdt', 'internal', 'requests', 'customIB', self.platf)
        topURL = 'http://cmssdt.cern.ch/SDT/cgi-bin/showCIB.py/'+self.platf

        userStamp = '/' + self.user['id'] + '/' + self._stamp
        self.topWebDir = topURL + userStamp
        self.topWebListDir = topURL.replace('showCIB','listDir') + '/sdtInternal/customIB'+userStamp

        self.topAFSDir = topAFS + userStamp
        if not os.path.exists(self.topAFSDir):
            os.makedirs(self.topAFSDir)

        
        logFileNameWeb = os.path.join(self.topWebDir, 'customIB-build-'+self._stamp+'.log')
        logFileNameAFS = os.path.join(self.topAFSDir, 'customIB-build-'+self._stamp+'.log')

        testLogNameWeb = os.path.join(self.topWebDir, 'customIB-tests-'+self._stamp+'.log')
        testLogNameAFS = os.path.join(self.topAFSDir, 'customIB-tests-'+self._stamp+'.log')

        diffLogNameWeb = os.path.join(self.topWebDir, 'customIB-diff-'+self._stamp+'.log')
        diffLogNameWeb = diffLogNameWeb.replace('showCIB.py', 'showDiff.py')
        diffLogNameAFS = os.path.join(self.topAFSDir, 'customIB-diff-'+self._stamp+'.log')
        
        dqmLogNameAFS = os.path.join(self.topAFSDir, 'customIB-dqm-'+self._stamp+'.log')

        cmdFile = open('doIt.sh', 'w')
        cmdFile.write('# set -x \n')
        cmdFile.write('source /afs/cern.ch/cms/cmsset_default.sh \n')
        cmdFile.write('export SCRAM_ARCH=' + self.platf + '\n')
        cmdFile.write('cmsrel ' + self.ref + '\n')
        cmdFile.write('cd '+self.ref+'/src' + '\n')
        cmdFile.write('cmsenv' + '\n')
        for p, v in self.tagList.items():
            cmdFile.write('addpkg -z '+p+' '+v + '\n')
        cmdFile.write('checkdeps -a -A ' + '\n')
        # cmdFile.write('addpkg -z Utilities/ReleaseScripts V00-06-04 \n')
        
        cmdFile.write('showtags -t -d -r --wrtBase >'+diffLogNameAFS+' 2>&1 \n')
        cmdFile.write('\n')

        # make sure we run scram b after adding all the tags including the ones for the tests    
        cmdFile.write('scram b -j 8 ' + '\n\n')
        cmdFile.write('RET=$?\n')
        cmdFile.write('echo "scram b returned "$RET \n')
        cmdFile.write('\n')
        cmdFile.write('if [ "x$RET" != "x0" ]; then exit $RET ; fi \n\n')
        
        totalCPUn = self.getNumberOfCPUs() 
        cmdFile.write('echo "running unit tests:"\n')
        timeoutScript = os.path.join(scriptPath, 'timeout3.sh')
        cmdFile.write(timeoutScript + ' -t 3600 scram b runtests -j ' + totalCPUn + '\n\n')
        cmdFile.write('echo "finished running of the unit tests"\n\n')
        
        cmdFile.write('mkdir tests ; cd tests\n')
        cmdFile.write('export PYTHONPATH=.:$PYTHONPATH\n')
        
        numberOfProcesses = int(totalCPUn) / 2
        for testName in testNames:
            cmdFile.write('\n'+testName+' -j ' + str(numberOfProcesses) + ' >>' + testLogName+' 2>&1 & ' + '\n')
        cmdFile.write('wait \n') # we need to wait for the background test job(s)

        # make sure we exit with the exit code from the build, as this will be checked later on:
        cmdFile.write('\nexit $RET\n')
        
        cmdFile.close()
        
        ret = os.system('chmod +x ./doIt.sh ; ./doIt.sh >'+logFileName+' 2>&1 ')
        print "running doIt retured: ", ret
        
        externals = tc.getReleaseExternal(self.ref, self.platf)
        cmdDqmFile = open('doDQMComparison.sh', 'w')
        cmdDqmFile.write('cd %s\n' % (self.ref,))
        cmdDqmFile.write('cvs -Q co -r %s CMSDIST\n' % (externals['CMSDIST'],))
        cmdDqmFile.write('cvs -Q co -r %s PKGTOOLS\n' % (externals['PKGTOOLS'],))
        cmdDqmFile.write('svn --quiet co https://svn.cern.ch/reps/CMSIntBld/trunk/IntBuild/IB\n')
        cmdDqmFile.write('PKGTOOLS/cmsBuild -a %s build cmssw-dqm-reference-deployer\n' % (self.platf,))
        report = self.platf+'/'+self.user['id']+'/'+self._stamp

        cmdDqmFile.write(timeoutScript + ' -t 7200 IB/CompareBuildWithReference.py -b %s -r %s -p %s -c %s -t %s --report_path /afs/cern.ch/work/c/cmsbuild/public/customIB/%s --custom_ib --report_relative_path %s/\n\n' % ('.', '$PWD', self.platf, self.ref[6]+'.' + self.ref[8], self.ref, report, report,))
        cmdDqmFile.write('RET=$?\n')
        cmdDqmFile.write('echo "scram b returned "$RET \n')
        cmdDqmFile.write('\n')
        cmdDqmFile.write('\nexit $RET\n')
        cmdDqmFile.close()
        ret2 = os.system('chmod +x ./doDQMComparison.sh ; ./doDQMComparison.sh >'+dqmLogName+' 2>&1 ')
        print "running doDQMComparison retured: ", ret2

        startDir = os.getcwd()


        try:
            os.system('cp '+logFileName+' '+logFileNameAFS)
        except:
            print "Error copying log files to AFS"
            pass

        errLines = None
        try:
            res = os.popen("grep 'gmake: ' "+logFileName)
            errLines = res.readlines()
            res.close()
        except:
            pass
        nErr = len(errLines)
        
        totalUnitTestLines = None
        try:
            res = os.popen("grep '===== Test' "+logFileName)
            totalUnitTestLines = res.readlines()
            res.close()
        except:
            pass
        nUnitTestTotal = len(totalUnitTestLines)
        
        errUnitTestLines = None
        try:
            res = os.popen("grep 'had ERRORS' "+logFileName + " | grep 'test'")
            errUnitTestLines = res.readlines()
            res.close()
        except:
            pass
        nUnitTestErr = len(errUnitTestLines)
        nUnitTestPassed = nUnitTestTotal - nUnitTestErr

        warnLines = None
        try:
            res = os.popen("grep -i 'warning' "+logFileName)
            warnLines = res.readlines()
            res.close()
        except:
            pass
        nWarn = len(warnLines)
        
        try:
            os.system('cp '+testLogName+' '+testLogNameAFS )
        except:
            print "Error copying log files to AFS"
            pass
        
        failLines = None
        try:
            res = os.popen("grep 'FAIL' "+testLogName)
            failLines = res.readlines()
            res.close()
        except:
            pass
        nFail = len(failLines)
        
        passLines = None
        try:
            res = os.popen("grep 'PASS' "+testLogName)
            passLines = res.readlines()
            res.close()
        except:
            pass
        nPass = len(passLines)
        
        try:
            os.system('cp '+dqmLogName+' '+dqmLogNameAFS )
        except:
            print "Error copying log files to AFS"
            pass

        try:
            cmd = 'cd '+self.ref+'/src; tar cf - `find tests -name \*log` | (cd  '+self.topAFSDir+' ; tar xf - )'
            print "going to copy test logs via:",cmd
            os.system(cmd)
            cmd = 'cd '+self.ref+'/src; tar cf - `find tests -name \*pkl` | (cd  '+self.topAFSDir+' ; tar xf - )'
            print "going to copy test log pkl files via:",cmd
            os.system(cmd)
        except:
            print "Error copying test log files to AFS"
            pass

        try:
            # Flag logs are ready to request-manager
            self.reqMgr.uploadLogs(self.topAFSDir, nWarn, nErr, nFail, nPass, nUnitTestErr, nUnitTestPassed, self.topWebDir)
        except Exception, e:
            print "ERROR when uploading logs, continuing ...", str(e)
            pass
        
        # send out mail to user
        msg =  "Hi "+self.user['name'].split(' ')[0]+',\n\n\n'
        msg += 'your custom IB for : \n'
        tagNames = self.tagList.keys()
        tagNames.sort()
        for p in tagNames:
            t = self.tagList[p]
            msg += '   ' + p + ' ' + t + '\n'
        msg += '\nfor architecture : ' + self.platf + '\n'
        msg += '\nbased on : ' + self.ref + '\n'
        msg += '\non host : ' + self.hostName + ' has finished, more information is available at: \n'
        msg += '\n'+self.topWebDir+'\n\n'

        if nWarn != 0:
            msg += '   build had '+str(nWarn)+' warnings. Please check and fix these.\n'

        if ret == 0:
            msg += '   tests Failed  : '+ str(nFail) +'\n'
            msg += '   tests Passed  : '+ str(nPass) +'\n\n'
        else:
            msg += '   build had errors, no tests were run. \n\n'
            
        informRequestor([self.user['mail']],msg,self.platf)
        os.chdir(startDir)
        
        return
    
    # --------------------------------------------------------------------------------
		
    def handleUpload(self):

        userName = self.user
        print 'uploading logs for user', userName,' id ', self.jobId, 'arch', self.platf
            
        self._stamp    = self.jobId
        self.id        = self.jobId
        tc.finishRequest(request_id=self.id, build_errors=0, build_warnings=1, tests_failed=2, tests_passed=3, results_url=None, unit_tests_passed=4, unit_tests_failed=5)        
        return

    # --------------------------------------------------------------------------------
		
    def handleRequest(self):

        self.reset()                    # make sure lists/maps are empty

        if self.reqMgr.getNewRequest(self.platf) :

            print 'processing request ', self.reqMgr.name()
            
            self.ref       = self.reqMgr.ref    
            self.tagList   = self.reqMgr.tagList
            self.user      = self.reqMgr.user   
            self._stamp    = self.reqMgr._stamp
            self.id        = self.reqMgr.id

            self.action()
            
        return
    

    # --------------------------------------------------------------------------------
		
    def process(self):

        if self.uploadOnly :
            self.handleUpload()
            return
            
        # make sure only one copy per machine is running ...
        if self.isRunning() : return

        print "\n",'-'*80,'\nRestarting at',time.asctime()
        sys.stdout.flush()

        pidFile = open(self.pidFileName, 'w')
        pidFile.write(self.pid +'\n')
        pidFile.close()
        print 'pid file written: ', self.pid
        sys.stdout.flush()
        
        while True:
            try:
                self.handleRequest()
            except ServerError, e:
                print str(e)
                pass
            except Exception, e:
                print "Processing request had problems:", str(e)
                try:
                    print " msg is", e.msg
                except AttributeError:
                    pass
                print "continuing ..."
                pass

            if self.stopRequested() :
                print "stop request found ... exiting at ", time.asctime()
                os.unlink( self.stopFileName )  # remove the stop file so the next job can start clean 
                if not self.uploadOnly :
                    os.unlink(self.pidFileName)
                break # clean stop here ...

            sleep_time = 1*60 #sleep five minutes
            print "\n" + time.asctime() + " Going to sleep for " + str(sleep_time) + " seconds"
            sys.stdout.flush()
            time.sleep(sleep_time)
            
        return


    # --------------------------------------------------------------------------------
		
    def show(self):
        """docstring for show"""

        print "request for custom IB"
        for k,v in self.tagList.items():
            print "\ttag   : "+ k + " : " + v
        print "\tuser  :", self.user
        print "\tref   :", self.ref
        print "\tstamp :", self._stamp
        return

# ================================================================================

def Usage(msg):
    print msg
    sys.exit(-1)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    try:
        opts, args = getopt.getopt(argv[1:], "hv", ["help",'uploadLogs','user=','id=','platform='])
    except getopt.error, msg:
        raise Usage(msg)

    # option processing
    uploadOnly = False
    user  = None
    jobId = None
    platf = None
    
    for option, value in opts:
        if option == "-v":
            verbose = True
        if option in ("-h", "--help"):
            raise Usage(help_message)
        if option in ('--uploadLogs',):
            uploadOnly = True
        if option in ('--user',):
            user = value
        if option in ('--id',):
            jobId = value
        if option in ('--platform',):
            platf = value

    if not platf:
        msg = "ERROR required option platform not given !"
        raise Usage(msg)

    cibp = CustomIBProcessor(uploadOnly, user, jobId, platf)
    cibp.process()
    
# ================================================================================

if __name__ == "__main__":
	sys.exit(main())
