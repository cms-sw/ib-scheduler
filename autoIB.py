#!/usr/bin/env python
# This script allows you to execute various misc test to automate IB building steps, in particular:
#
# - Reset the weekly repository.
# - Build and upload externals in the weekly repository.
# - Build and upload ibs in the weekly repository.
#
from optparse import OptionParser
import tagCollectorAPI
import sys, os, socket
import urllib
from urllib2 import urlopen
import xml.parsers.expat
from commands import getstatusoutput
from getpass import getuser
from time import strftime
from os.path import abspath, join, dirname, exists
import re
from Lock import Lock
from datetime import datetime, timedelta
from cmssw_secrets import CMSSW_CVSPASS
try:
  from hashlib import sha1 as sha
  def hash(s):
    return sha(s).hexdigest()
except ImportError:
  import sha
  def hash(s):
    return sha.new(s).hexdigest()

TESTBED_URL="https://cmstags-dev.cern.ch/tc/"

def overloaded(maxLoad):
  err,out = getstatusoutput("uptime | sed -e 's/^.* //'")
  if err:
    return False 
  return float(out) > float(maxLoad)

# Replace @TW with the week number, modulo 2
# Replace @NW with the week number, modulo 2
# Replace @PW with the week number, modulo 2
def expandDates(s):
  today = datetime.today()
  tw=str(int(today.strftime("%W")) % 2)
  nw=str(int((today + timedelta(days=7)).strftime("%W")) % 2)
  pw=str(int((today + timedelta(days=-7)).strftime("%W")) % 2)
  return strftime(s.replace("@TW", tw).replace("@NW", nw).replace("@PW", pw))

# Sanitized caracters which could possibly allow execution of unwanted
# commands.
def sanitize(s):
  if not s:
    return ""
  return re.sub("[.]/", ".", re.sub("[^0-9a-zA-Z_,:./-]", "", s))
  
def format(s, **kwds):
  return s % kwds

def process():
  # Get the first task from the list
  # Check if we know what to do
  # Mark it as started
  # Start doing it
  parser = OptionParser(usage="%prog process [options]")
  parser.add_option("--match-arch", metavar="REGEX", dest="matchArch", help="Limit architectures to those matching REGEX", default=".*")
  parser.add_option("--match-release", metavar="REGEX", dest="matchRelease", help="Limit releases to those matching REGEX", default=".*")
  parser.add_option("--work-dir", "--top-dir", metavar="PATH", dest="workdir", help="Work dir where processing happens", default=None)
  parser.add_option("--jobs", "-j", type="int", metavar="N", dest="jobs", help="Number of parallel building threads", default=1)
  parser.add_option("--builders", type="int", metavar="N", dest="builders", help="Number of packages built in parallel", default=1)
  parser.add_option("--debug", metavar="PATH", dest="debug", help="Print out what's happening", action="store_true", default=False)
  parser.add_option("--dry-run", "-n", metavar="BOOL", dest="dryRun", help="Do not execute", action="store_true", default=False)
  parser.add_option("--testbed", metavar="BOOL", dest="useTestBed", help="Use the testbed tag collector to ", action="store_true", default=False)
  parser.add_option("--max-load", type="int", metavar="LOAD", dest="maxLoad", help="Do not execute if average last 15 minutes load > LOAD", default=8)
  opts, args = parser.parse_args()
  if not opts.workdir:
    print "Please specify a workdir"
    sys.exit(1)

  if exists("/etc/iss.nologin"):
    print "/etc/iss.nologin found. Not doing anything and waiting for machine out of maintainance mode."
    sys.exit(1)
  opts.workdir = abspath(opts.workdir)
  thisPath=dirname(__file__)
  getstatusoutput(format(
    "%(here)s/syncLogs.py %(workdir)s",
    here=thisPath, 
    workdir=opts.workdir))
  lockPath = join(opts.workdir, "cms", ".cmsLock")
  lock = Lock(lockPath, True, 60*60*12)
  if not lock:
    if opts.debug:
      print "Lock found in %s" % lockPath
    sys.exit(1)
  lock.__del__()
   
  if overloaded(opts.maxLoad):
    print "Current load exceeds maximum allowed of %s." % opts.maxLoad
    sys.exit(1)
  options = {"release_pattern": opts.matchRelease,
             "architecture_pattern": opts.matchArch}
  if opts.useTestBed:
    options["tcBaseURL"] = TESTBED_URL
  tasks = tagCollectorAPI.listPendingTasks(**options)
  print tasks
  if not len(tasks):
    if opts.debug:
      print "Nothing to be done which matches release %s and architecture %s" % (opts.matchArch, opts.matchRelease)
    sys.exit(1)
  # Look up for a hostname-filter option in the payload and if it is there,
  # make sure we match it.
  runnableTask = None
  for task in tasks:
    if re.match(task.get("hostname-filter", ".*"), sockets.hostname()):
      runnableTask = task
      break
  if not runnableTask:
    print "Nothing to be done on this machine."
    sys.exit(1)
  # Default payload options.
  payload = {"debug": False}
  task_id, architecture_name, release_name, payloadNew = runnableTask
  payload.update(payloadNew)

  # We can now specify tags in the format repository:tag to pick up branches
  # from different people.
  payload["pkgtools_remote"] = "cms-sw"
  payload["cmsdist_remote"] = "cms-sw"
  if ":" in payload["PKGTOOLS"]:
    payload["pkgtools_remote"], payload["PKGTOOLS"] = payload["PKGTOOLS"].split(":", 1)
  if ":" in payload["CMSDIST"]:
    payload["cmsdist_remote"], payload["CMSDIST"] = payload["CMSDIST"].split(":", 1)
  
  if not payload.has_key("build-task"):
    print "Request task %s is not a valid build task" % task_id
    sys.exit(1)

  buildTask = payload["build-task"]
  if not buildTask in ["build-package"]:
    print "Unknown task for request %s: %s" % (task_id, buildTask)
    sys.exit(1)

  if opts.dryRun:
    print "Dry run. Not building"
    sys.exit(1)

  options = {"request_id": task_id,
             "release_name": release_name,
             "machine": socket.gethostname(),
             "pid": os.getpid()}
  if opts.useTestBed:
    options["tcBaseURL"] = TESTBED_URL
  options["results_url"] = "http://cmssdt.cern.ch/SDT/tc-ib-logs/%s/log.%s.html" % (socket.gethostname(), task_id)
  ok = tagCollectorAPI.setRequestBuilding(**options)
  if not ok:
    print "Could not change request %s state to building" % task_id
    sys.exit(1)
  
  # Build the package.
  # We gracefully handle any exception (broken pipe, ctrl-c, SIGKILL)
  # by failing the request if they happen. We also always cat 
  # the log for this build in a global log file.
  log = ""
  getstatusoutput(format(
    "echo 'Log not sync-ed yet' > %(workdir)s/log.%(task_id)s;\n"
    "%(here)s/syncLogs.py %(workdir)s",
    task_id=task_id,
    here=thisPath, 
    workdir=opts.workdir))
  try:
    print "Building..."
    error, log = getstatusoutput(format("set -e ;\n"
       "mkdir -p %(workdir)s/%(task_id)s ;\n"
       "export CMS_PATH=%(workdir)s/cms ;\n"
       "cd %(workdir)s ;\n"
       "( export CVSROOT=:pserver:anonymous@cmssw.cvs.cern.ch/local/reps/CMSSW ;\n"
       "  export CVS_PASSFILE=%(workdir)s/.cvspass ;\n"
       "  echo '/1 :pserver:anonymous@cmscvs.cern.ch:/cvs_server/repositories/CMSSW %(cvspass)s' > $CVS_PASSFILE ;\n"
       "  echo '/1 :pserver:anonymous@cmssw.cvs.cern.ch:2401/cvs/CMSSW %(cvspass)s' >> $CVS_PASSFILE ;\n"
       "  echo '/1 :pserver:anonymous@cmssw.cvs.cern.ch:2401/cvs_server/repositories/CMSSW %(cvspass)s' >> $CVS_PASSFILE ;\n"
       "  echo '/1 :pserver:anonymous@cmscvs.cern.ch/local/reps/CMSSW %(cvspass)s' >> $CVS_PASSFILE ;\n"
       "  echo '/1 :pserver:anonymous@cmssw.cvs.cern.ch/local/reps/CMSSW %(cvspass)s' >> $CVS_PASSFILE ;\n"
       "  echo '/1 :pserver:anonymous@cmssw.cvs.cern.ch:2401/local/reps/CMSSW %(cvspass)s' >> $CVS_PASSFILE ;\n"
       "  echo '/1 :pserver:anonymous@cmscvs.cern.ch:2401/local/reps/CMSSW %(cvspass)s' >> $CVS_PASSFILE ;\n"
       "  echo '/1 :pserver:anonymous@cmssw.cvs.cern.ch:2401/local/reps/CMSSW %(cvspass)s' >> $CVS_PASSFILE;\n"
       "  echo 'Building %(package)s using %(cmsdistRemote)s:%(cmsdistTag)s';\n"
       "  git clone git://github.com/%(cmsdistRemote)s/cmsdist.git %(task_id)s/CMSDIST;\n"
       "  pushd %(task_id)s/CMSDIST; git checkout %(cmsdistTag)s; popd;\n"
       "  PKGTOOLS_TAG=\"`echo %(pkgtoolsTag)s | sed -e's/\\(V[0-9]*-[0-9]*\\).*/\\1-XX/'`\";\n"
       "  git clone git://github.com/%(pkgtoolsRemote)s/pkgtools.git %(task_id)s/PKGTOOLS\n"
       "  pushd %(task_id)s/PKGTOOLS; git checkout $PKGTOOLS_TAG; popd;\n"
       "  echo \"### RPM cms dummy `date +%%s`\n%%prep\n%%build\n%%install\n\" > %(task_id)s/CMSDIST/dummy.spec ;\n"
       "  set -x ;\n"
       "  rm -rf %(workdir)s/cms %(workdir)s/b ;\n"
       "  perl -p -i -e 's/### RPM cms cmssw.*/### RPM cms cmssw %(base_release_name)s/' %(task_id)s/CMSDIST/cmssw.spec ;\n"
       "  perl -p -i -e 's/### RPM cms cmssw-ib .*/### RPM cms cmssw-ib %(base_release_name)s/' %(task_id)s/CMSDIST/cmssw-ib.spec ;\n"
       "  perl -p -i -e 's/### RPM cms cmssw-qa .*/### RPM cms cmssw-qa %(base_release_name)s/' %(task_id)s/CMSDIST/cmssw-qa.spec ;\n"
       "  perl -p -i -e 's/### RPM cms cmssw-validation .*/### RPM cms cmssw-validation %(base_release_name)s/' %(task_id)s/CMSDIST/cmssw-validation.spec ;\n"
       "  perl -p -i -e 's/### RPM cms cmssw-patch.*/### RPM cms cmssw-patch %(real_release_name)s/' %(task_id)s/CMSDIST/cmssw-patch.spec ;\n"
       "  %(workdir)s/%(task_id)s/PKGTOOLS/cmsBuild %(debug)s --new-scheduler --cmsdist %(workdir)s/%(task_id)s/CMSDIST %(ignoreErrors)s --builders %(builders)s -j %(jobs)s --repository %(repository)s --architecture %(architecture)s --work-dir %(workdir)s/cms build %(package)s ;\n"
       "  %(workdir)s/%(task_id)s/PKGTOOLS/cmsBuild %(debug)s --new-scheduler --cmsdist %(workdir)s/%(task_id)s/CMSDIST --repository %(repository)s --upload-tmp-repository %(tmpRepository)s %(syncBack)s --architecture %(architecture)s --work-dir %(workdir)s/cms upload %(package)s ;\n"
       "  PKG_BUILT=`find %(workdir)s/cms/RPMS/%(architecture)s -name \"*%(package)s*\"| sed -e's|.*/\\([^+]*+[^+]*+[^.]*\\).*|\\1|'`;\n"
       "  set +x ;\n"
       "  echo Build completed. you can now install the package built by doing: ;\n"
       "  echo wget http://cmsrep.cern.ch/cmssw/cms/bootstrap.sh ;\n"
       "  echo sh -x ./bootstrap.sh setup -path w -arch %(architecture)s -r %(repository)s >& bootstrap_%(architecture)s.log ;\n"
       "  echo \"(source w/%(architecture)s/external/apt/*/etc/profile.d/init.sh ; apt-get install $PKG_BUILD )\" ;\n"
       "  echo AUTOIB SUCCESS) 2>&1 | tee %(workdir)s/log.%(task_id)s",
       workdir=opts.workdir,
       cvspass=CMSSW_CVSPASS,
       debug=payload["debug"] == True and "--debug" or "",
       cmsdistTag=sanitize(payload["CMSDIST"]),
       pkgtoolsTag=sanitize(payload["PKGTOOLS"]),
       cmsdistRemote=sanitize(payload["cmsdist_remote"]),
       pkgtoolsRemote=sanitize(payload["pkgtools_remote"]),
       architecture=sanitize(architecture_name),
       release_name=sanitize(release_name),
       base_release_name=re.sub("_[^_]*patch[0-9]*$", "", sanitize(payload["real_release_name"])),
       real_release_name=sanitize(payload["real_release_name"]),
       package=sanitize(payload["package"]),
       repository=sanitize(payload["repository"]),
       syncBack=payload["syncBack"] == True and "--sync-back" or "",
       ignoreErrors=payload["ignoreErrors"] == True and "-k" or "",
       tmpRepository=sanitize(payload["tmpRepository"]),
       task_id=task_id,
       jobs=opts.jobs,
       builders=opts.builders))
    getstatusoutput(format("echo 'Task %(task_id)s completed successfully.' >> %(workdir)s/log.%(task_id)s",
                           workdir=opts.workdir,
                           task_id=task_id))
  except Exception, e:
    log = open(format("%(workdir)s/log.%(task_id)s", workdir=opts.workdir, task_id=task_id)).read()
    log += "\nInterrupted externally."
    log += str(e)
    getstatusoutput(format("echo 'Interrupted externally' >> %(workdir)s/log.%(task_id)s",
                           workdir=opts.workdir,
                           task_id=task_id))
    
  error, saveLog = getstatusoutput(format("set -e ;\n"
       "echo '#### Log file for %(task_id)s' >> %(workdir)s/log ;\n"
       "cat %(workdir)s/log.%(task_id)s >> %(workdir)s/log",
       workdir=opts.workdir,
       task_id=task_id))
  
  getstatusoutput("%s/syncLogs.py %s" % (thisPath, opts.workdir))
  if not "AUTOIB SUCCESS" in log:
    tagCollectorAPI.failRequest(request_id=task_id, results_url="http://cmssdt.cern.ch/SDT/tc-ib-logs/%s/log.%s.html" % (socket.gethostname(), task_id))
    print log
    print saveLog
    sys.exit(1)
  
  tagCollectorAPI.finishRequest(request_id=task_id, results_url="http://cmssdt.cern.ch/SDT/tc-ib-logs/%s/log.%s.html" % (socket.gethostname(), task_id))

  # Here we are done processing the job. Now schedule continuations.
  if not "continuations" in payload:
    sys.exit(0)
  continuationsSpec = payload["continuations"] or ""
  continuations = [x for x in continuationsSpec.split(";")]
  if len(continuations) == 0:
    sys.exit(0)
  
  if len(continuations) != 1:
    print "WARNING: multiple continuations not supported yet"
  
  if opts.debug:
    print continuations
  nextTasks = [p.split(":", 1) for p in continuations[0].split(",") if ":" in p]
    
  for package, architecture in nextTasks:
    options = {}
    options["build-task"] = "build-package"
    options["release_name"] = sanitize(release_name)
    options["real_release_name"] = sanitize(payload["real_release_name"])
    options["architecture_name"] = sanitize(architecture)
    options["repository"] = sanitize(payload["repository"])
    options["tmpRepository"] = sanitize(payload["tmpRepository"])
    options["syncBack"] = payload["syncBack"]
    options["debug"] = payload["debug"]
    options["ignoreErrors"] = payload["ignoreErrors"]
    options["package"] = sanitize(package)
    # Notice that continuations will not support overriding CMSDIST and
    # PKGTOOLS completely.
    # 
    # We do not want that because there could be cases where
    # the first step is done for one architecture, while the second 
    # step is done for another.
    options["PKGTOOLS"] = sanitize(payload["PKGTOOLS"])
    options["CMSDIST"] = sanitize(payload["CMSDIST"])
    # For the moment do not support continuations of continuations.
    options["continuations"] = ""
    cmsdistTagUrl = "http://cmstags.cern.ch/tc/public/ReleaseExternalsXML?" + urllib.urlencode({"release": options["release_name"], 
                                                                                         "architecture": options["architecture_name"]})
    try:
      data = urlopen(cmsdistTagUrl).read()
    except:
      print "Unable to find release %s for %s." % (options["release_name"],  options["architecture_name"])
      sys.exit(1)
    p = xml.parsers.expat.ParserCreate()
    tags = {}
    def start_element(name, attrs):
      if name != "external":
        return
      tags[str(attrs["external"].strip())] = str(attrs["tag"].strip())
    p.StartElementHandler = start_element
    p.Parse(data)
    options.update(tags)
    if opts.useTestBed:
      options["tcBaseURL"] = TESTBED_URL
    options["request_type"] = "TASK-%s" % hash(options["package"])[0:8]
    tagCollectorAPI.createTaskRequest(**options)

def listTasks():
  # Get the first task from the list
  # Check if we know what to do
  # Mark it as started
  # Start doing it
  parser = OptionParser(usage="%prog list [options]")
  parser.add_option("--match-arch", metavar="REGEX", dest="matchArch", help="Limit architectures to those matching REGEX", default=".*")
  parser.add_option("--match-release", metavar="REGEX", dest="matchRelease", help="Limit releases to those matching REGEX", default=".*")
  parser.add_option("--testbed", metavar="BOOL", dest="useTestBed", help="Use the testbed tag collector to ", action="store_true", default=False)
  opts, args = parser.parse_args()
  options = {"release_pattern": opts.matchRelease,
             "architecture_pattern": opts.matchArch}
  if opts.useTestBed:
    options["tcBaseURL"] = TESTBED_URL
  results = tagCollectorAPI.listPendingTasks(**options)
  if not results:
    sys.exit(1)
  print "\n".join([str(x[0]) for x in results])

# This will request to build a package in the repository.
# - Setup a few parameters for the request
# - Get PKGTOOLS and CMSDIST from TC if they are not passed
# - Create the request.
def requestBuildPackage():
  parser = OptionParser()
  parser.add_option("--release", "-r", metavar="RELEASE", dest="release_name", help="Specify release.", default=None)
  parser.add_option("--architecture", "-a", metavar="ARCHITECTURE", dest="architecture_name", help="Specify architecture", default=None)
  parser.add_option("--repository", "-d", metavar="REPOSITORY NAME", dest="repository", help="Specify repository to use for bootstrap", default="cms")
  parser.add_option("--upload-tmp-repository", metavar="REPOSITORY SUFFIX", dest="tmpRepository", help="Specify repository suffix to use for upload", default=getuser())
  parser.add_option("--pkgtools", metavar="TAG", dest="pkgtools", help="Specify PKGTOOLS version to use. You can specify <user>:<tag> to try out a non official tag.", default=None)
  parser.add_option("--cmsdist", metavar="TAG", dest="cmsdist", help="Specify CMSDIST tag branch to use. You can specify <user>:<tag> to try out a non official tag.", default=None)
  parser.add_option("--hostname-filter", metavar="HOSTNAME-REGEX", dest="hostnameFilter", help="Specify a given regular expression which must be matched by the hostname of the builder machine.", default=".*")
  parser.add_option("--sync-back", metavar="BOOL", dest="syncBack", action="store_true", help="Specify whether or not to sync back the repository after upload", default=False)
  parser.add_option("--ignore-compilation-errors", "-k", metavar="BOOL", dest="ignoreErrors", help="When supported by the spec, ignores compilation errors and still packages the available build products", action="store_true", default=False)
  parser.add_option("--testbed", metavar="BOOL", dest="useTestBed", help="Use the testbed tag collector to ", action="store_true", default=False)
  parser.add_option("--continuations", metavar="SPEC", dest="continuations", help="Specify a comma separated list of task:architecture which need to be scheduled after if this task succeeds", default="")
  parser.add_option("--debug", metavar="BOOL", dest="debug", help="Add cmsbuild debug information", action="store_true", default=False)
  opts, args = parser.parse_args()
  if len(args) != 2:
    print "You need to specify a package"
    sys.exit(1)
  if not opts.repository:
    print "Please specify a repository"
    sys.exit(1)
  options = {}
  options["build-task"] = "build-package"
  options["hostnameFilter"] = opts.hostnameFilter
  options["real_release_name"] = expandDates(opts.release_name)
  options["release_name"] = re.sub("_[A-Z]+_X", "_X", options["real_release_name"])
  options["architecture_name"] = opts.architecture_name
  options["repository"] = expandDates(opts.repository)
  options["tmpRepository"] = expandDates(opts.tmpRepository)
  options["syncBack"] = opts.syncBack
  options["package"] = expandDates(args[1])
  options["continuations"] = opts.continuations
  options["ignoreErrors"] = opts.ignoreErrors
  options["debug"] = opts.debug
  if opts.useTestBed:
    options["tcBaseURL"] = TESTBED_URL
  options["request_type"] = "TASK-%s" % hash(expandDates(args[1] + options["real_release_name"]))[0:8]

  if opts.cmsdist and opts.continuations:
    print format("WARNING: you have specified --pkgtools to overwrite the PKGTOOLS tag coming from tag collector.\n"
                 "However, this will happen only for %(package)s, continuations will still fetch those from the tagcolletor.", package=options["package"])

  if opts.cmsdist and opts.continuations:
    print format("WARNING: you have specified --cmsdist to overwrite the PKGTOOLS tag coming from tag collector.\n"
                 "However, this will happen only for %(package)s, continuations will still fetch those from the tagcolletor.", package=options["package"])

  cmsdistTagUrl = "http://cmstags.cern.ch/tc/public/ReleaseExternalsXML?" + urllib.urlencode({"release": options["release_name"], 
                                                                                       "architecture": options["architecture_name"]})
  try:
    data = urlopen(cmsdistTagUrl).read()
  except:
    print "Unable to find release %s for %s." % (options["release_name"],  options["architecture_name"])
    sys.exit(1)
  p = xml.parsers.expat.ParserCreate()
  tags = {}
  def start_element(name, attrs):
    if name != "external":
      return
    tags[str(attrs["external"].strip())] = str(attrs["tag"].strip())
  p.StartElementHandler = start_element
  p.Parse(data)
  options.update(tags)
  if opts.pkgtools:
    options["PKGTOOLS"] = sanitize(opts.pkgtools)
  if opts.cmsdist:
    options["CMSDIST"] = sanitize(opts.cmsdist)
  if not options.get("CMSDIST"):
    print "Unable to find CMSDIST for releases %s on %s" % (options["release_name"], options["architecture_name"])
    sys.exit(1)
  if not options.get("PKGTOOLS"):
    print "Unable to find PKGTOOLS for releases %s on %s" % (options["release_name"], options["architecture_name"])
    sys.exit(1)
  tagCollectorAPI.createTaskRequest(**options)

def cancel():
  parser = OptionParser(usage="%prog cancel <request-id>")
  opts, args = parser.parse_args()
  if not len(args):
    print "Please specify a request id."
  ok = tagCollectorAPI.cancelRequest(args[1])
  if not ok:
    print "Error while cancelling request %s" % args[1]
    sys.exit(1)

COMMANDS = {"process": process, 
            "cancel": cancel,
            "list":  listTasks,
            "request": requestBuildPackage}

if __name__ == "__main__":
  commands = [x for x in sys.argv[1:] if not x.startswith("-")]
  if len(commands) == 0 or not commands[0] in COMMANDS.keys():
    print "Usage: autoIB.py <command> [options]\n"
    print "Where <command> can be among the following:\n"
    print "\n".join(COMMANDS.keys())
    print "\nUse `autoIB.py <command> --help' to get more detailed help."
    sys.exit(1)
  command = commands[0]
  COMMANDS[command]()
