#!/usr/bin/env python
import os, sys, tagCollectorAPI, socket, re
from optparse import OptionParser
from datetime import datetime
from os import unlink
from Lock import Lock

DEFAULT_TESTS = "perfMatrix,1of1"
DEFAULT_BUILDPATH = "/build/cmsbuild/stdTest"
DEFAULT_CMSPATH = "/afs/cern.ch/cms"
DEFAULT_SVN = 'http://svn.cern.ch/guest/CMSIntBld/trunk/IntBuild'

def format(s, **k): 
  return s % k 

def die(s):
  print s
  sys.exit(1)

# ================================================================================
def startTest(ibName, cycle, testDir, tests,arch):
  logFile = os.path.join(testDir, 'fullLog-'+cycle+'-'+arch+'-'+datetime.now().strftime('%Y%m%d-%H%M')+'.log')
  cmd = format('rm -rf %(testDir)s/%(pid)s; mkdir -p %(testDir)s/%(pid)s;'
               'svn -q co %(svn)s/IB %(testDir)s/%(pid)s/IB >%(logFile)s 2>&1;'
               'svn -q co %(svn)s/QA %(testDir)s/%(pid)s/QA >%(logFile)s 2>&1;'
               '%(testDir)s/%(pid)s/QA/standaloneTesterNew.py --plat %(arch)s --buildDir %(testDir)s --release %(ibName)s --only "%(tests)s" > %(logFile)s 2>&1 ;'
               'rm -rf %(testDir)s/%(pid)s',
               testDir=testDir,
               svn=DEFAULT_SVN,
               logFile=logFile,
               pid=str(os.getpid()),
               cycle=cycle,
               arch=arch,
               ibName=ibName,
               tests=tests)
  os.system(cmd)
  if os.path.getsize(logFile) == 0:
    unlink(logFile)
    return

  cmd = format('cat %(logFile)s | mail -s "QA tests finished for %(cycle)s cycle: %(tests)s" "cmssdt-ibs@cern.ch"', 
               tests=tests,
               cycle=cycle,
               logFile=logFile)
  os.system(cmd)

# ================================================================================
  
def getCycleNameByReleaseName(release_name):
  g = re.match("CMSSW_([0-9]*)_([0-9]*)(_[A-Za-z][A-Za-z]+|)_([0-9X]*).*", release_name).groups()
  if not g:
    die("Invalid release name.")
  return format("%(major)s.%(minor)s%(extra)s",
                major=g[0],
                minor=g[1],
                extra=g[2].replace("_", "."))

def processScheduledQARequest(requestId, ibName, arch, buildpath=DEFAULT_BUILDPATH, cmspath=DEFAULT_CMSPATH, tests=DEFAULT_TESTS):
  cycle = getCycleNameByReleaseName(ibName)
  os.environ["SCRAM_ARCH"]=arch
  os.environ["CMSINTBLD_CMS_PATH"]=cmspath
  tagCollectorAPI.setRequestBuilding(requestId, ibName,machine=socket.gethostname(), pid=os.getpid())
  startTest(ibName, cycle, buildpath, tests, arch)
  tagCollectorAPI.finishRequest(requestId)
  
def getLock(buildpath):
  return Lock(os.path.join(buildpath,'lock'),True,60*60*20)

if __name__ == "__main__" :
  parser = OptionParser(usage="%(prog)s [--test <tests>][--buildpath <buildpath>] [--cmspath <cmspath>]")
  parser.add_option("-t", "--test", dest="tests", help="Tests to run", default=DEFAULT_TESTS)
  parser.add_option("-b", "--buildpath", dest="buildpath", help="Path to build directory", default=DEFAULT_BUILDPATH)
  parser.add_option("-c", "--cmspath", dest="cmspath", help="Path to shared cms directory", default=DEFAULT_CMSPATH)
  
  opts, args = parser.parse_args()
  if args:
    parser.error("%(prog)s does not take any argument")

  lock = getLock(opts.buildpath)
  if not lock:
    sys.exit(0)

  qaData = tagCollectorAPI.getQAPendingRequests()
  if not qaData:
    print "Pending QA requests are not found, exiting."
    sys.exit(0)
  processScheduledQARequest(qaData['id'],
                            qaData['release_name'], 
                            qaData['architecture_name'], 
                            buildpath=opts.buildpath, 
                            cmspath=opts.cmspath, 
                            tests=opts.tests)
  lock = None
