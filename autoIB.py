#!/usr/bin/env python
# This script allows you to execute various misc test to automate IB building
# steps, in particular:
#
# - Reset the weekly repository.
# - Build and upload externals in the weekly repository.
# - Build and upload ibs in the weekly repository.
#
from optparse import OptionParser
import buildRequestAPI as api
import sys, os, socket
from urllib2 import urlopen
from urllib import urlencode
import xml.parsers.expat
from commands import getstatusoutput
from getpass import getuser
from time import strftime
from os.path import abspath, join, dirname, exists, expanduser
import re
from Lock import Lock
from datetime import datetime, timedelta
import ws_sso_content_reader
scriptPath = os.path.dirname( os.path.abspath(sys.argv[0]) )
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

from all_json import loads, dumps

DEFAULT_API_URL = "https://cmsgit.web.cern.ch/cmsgit/buildrequests"

def setTCUrl(url):
  global DEFAULT_API_URL
  DEFAULT_API_URL = url

def call(obj, method, **kwds):
  obj = str(obj).strip("/")
  print obj,":", method
  print kwds
  if method == "GET":
    opts = urlencode(kwds)
    result = ws_sso_content_reader.getContent(join(DEFAULT_API_URL, obj) + "?" + opts, None, method)
  elif method in ["POST", "PATCH", "DELETE"]:
    opts = dumps(kwds)
    result = ws_sso_content_reader.getContent(join(DEFAULT_API_URL, obj), opts, method)
    print result
  return loads(result)

try:
  from hashlib import sha1 as sha
  def hash(s):
    return sha(s).hexdigest()
except ImportError:
  import sha
  def hash(s):
    return sha.new(s).hexdigest()

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

def expandRelease(s, release):
  # The queue is always CMSSW_x_y_X
  queue = re.sub("(CMSSW_[0-9]+_[0-9]+).*", "\\1_X", release)
  s = s.replace("@RELEASE", release)
  s = s.replace("@QUEUE", queue)
  return s

# Sanitized caracters which could possibly allow execution of unwanted
# commands.
def sanitize(s):
  if not s:
    return ""
  return re.sub("[.]/", ".", re.sub("[^0-9a-zA-Z_,:./-]", "", s))
  
def format(s, **kwds):
  return s % kwds

def die(s):
  print s
  sys.exit(1)

EXTERNAL_INFO_URL="https://raw.github.com/cms-sw/cmsdist/IB/%s/stable/config.map"
# Get external information from github.
# See http://cms-sw.github.io/cmsdist/ 
# for the format of the config.map file.
def getExternalsTags(release_queue, architecture):
  # Get the mapping between architecture and release
  url = EXTERNAL_INFO_URL % release_queue
  try:
    data = urlopen(url).read()
  except:
    die("Unable to find CMSDIST information for release queue %s." % release_queue)
  lines = [x.strip().split(";") for x in data.split("\n") if x.strip()]
  archInfo = {}
  for line in lines:
    parts = dict(x.split("=") for x in line)
    if not "SCRAM_ARCH" in parts:
      die("Bad file format for config.map")
    if parts["SCRAM_ARCH"] == architecture:
      archInfo = dict(parts)
      break
  if not archInfo.get("CMSDIST_TAG", None) or not archInfo.get("PKGTOOLS_TAG", None):
    die(format("Could not find architecture %(architecture)s for release series %(release_queue)s.\n"
               "Please update `config.map' file in the CMSDIST branch IB/%(release_queue)s/stable",
               release_queue=release_queue,
               architecture=architecture))
  return {"PKGTOOLS": archInfo["PKGTOOLS_TAG"],
          "CMSDIST": archInfo["CMSDIST_TAG"]}

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
  parser.add_option("--api-url", metavar="URL", dest="apiUrl", help="Specify API endpoint URL", default=DEFAULT_API_URL)
  parser.add_option("--max-load", type="int", metavar="LOAD", dest="maxLoad", help="Do not execute if average last 15 minutes load > LOAD", default=8)
  opts, args = parser.parse_args()
  setTCUrl(opts.apiUrl)
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
  tasks = call("/", "GET", 
               release_match=opts.matchRelease,
               architecture_match=opts.matchArch,
               state="Pending")
  print tasks
  if not len(tasks):
    if opts.debug:
      print "Nothing to be done which matches release %s and architecture %s" % (opts.matchArch, opts.matchRelease)
    sys.exit(1)
  # Look up for a hostname-filter option in the payload and if it is there,
  # make sure we match it.
  runnableTask = None
  for task in tasks:
    if not "payload" in task:
      continue
    if re.match(task["payload"].get("hostnameFilter", ".*"), socket.gethostname()):
      runnableTask = task
      break
  if not runnableTask:
    print "Nothing to be done on this machine."
    sys.exit(1)
  # Default payload options.
  payload = {"debug": False}
  payload.update(runnableTask["payload"])

  # We can now specify tags in the format repository:tag to pick up branches
  # from different people.
  payload["pkgtools_remote"] = "cms-sw"
  payload["cmsdist_remote"] = "cms-sw"
  if ":" in payload["PKGTOOLS"]:
    payload["pkgtools_remote"], payload["PKGTOOLS"] = payload["PKGTOOLS"].split(":", 1)
  if ":" in payload["CMSDIST"]:
    payload["cmsdist_remote"], payload["CMSDIST"] = payload["CMSDIST"].split(":", 1)
  
  if opts.dryRun:
    print "Dry run. Not building"
    sys.exit(1)

  ok = call(runnableTask["id"], "PATCH", 
            url="http://cmssdt.cern.ch/SDT/tc-ib-logs/%s/log.%s.html" % (socket.gethostname(), runnableTask["id"]),
            machine=socket.gethostname(),
            pid=os.getpid(),
            state="Running")
  if not ok:
    print "Could not change request %s state to building" % runnableTask["id"] 
    sys.exit(1)
  
  # Build the package.
  # We gracefully handle any exception (broken pipe, ctrl-c, SIGKILL)
  # by failing the request if they happen. We also always cat 
  # the log for this build in a global log file.
  log = ""
  getstatusoutput(format(
    "echo 'Log not sync-ed yet' > %(workdir)s/log.%(task_id)s;\n"
    "%(here)s/syncLogs.py %(workdir)s",
    task_id=runnableTask["id"],
    here=thisPath, 
    workdir=opts.workdir))
  try:
    print "Building..."
    error, log = getstatusoutput(format("set -e ;\n"
       "mkdir -p %(workdir)s/%(task_id)s ;\n"
       "export CMS_PATH=%(workdir)s/cms ;\n"
       "cd %(workdir)s ;\n"
       "( echo 'Building %(package)s using %(cmsdistRemote)s:%(cmsdistTag)s';\n"
       "  rm -rf %(task_id)s;\n"
       "  git clone git://github.com/%(cmsdistRemote)s/cmsdist.git %(task_id)s/CMSDIST || git clone https://:@git.cern.ch/kerberos/CMSDIST.git %(task_id)s/CMSDIST;\n"
       "  pushd %(task_id)s/CMSDIST; git checkout %(cmsdistTag)s; popd;\n"
       "  PKGTOOLS_TAG=\"`echo %(pkgtoolsTag)s | sed -e's/\\(V[0-9]*-[0-9]*\\).*/\\1-XX/'`\";\n"
       "  git clone git://github.com/%(pkgtoolsRemote)s/pkgtools.git %(task_id)s/PKGTOOLS || git clone https://:@git.cern.ch/kerberos/PKGTOOLS.git %(task_id)s/PKGTOOLS;\n"
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
       "  PKG_BUILD=`find %(workdir)s/cms/RPMS/%(architecture)s -name \"*%(package)s*\"| sed -e's|.*/||g;s|-1-1.*||g'`;\n"
       "  set +x ;\n"
       "  echo Build completed. you can now install the package built by doing: ;\n"
       "  echo \"wget http://cmsrep.cern.ch/cmssw/cms/bootstrap.sh\" ;\n"
       "  echo \"sh -x ./bootstrap.sh setup -path w -arch %(architecture)s -r %(repository)s >& bootstrap_%(architecture)s.log \";\n"
       "  echo \"(source w/%(architecture)s/external/apt/*/etc/profile.d/init.sh ; apt-get install $PKG_BUILD )\" ;\n"
       "  echo AUTOIB SUCCESS) 2>&1 | tee %(workdir)s/log.%(task_id)s",
       workdir=opts.workdir,
       debug=payload["debug"] == True and "--debug" or "",
       cmsdistTag=sanitize(payload["CMSDIST"]),
       pkgtoolsTag=sanitize(payload["PKGTOOLS"]),
       cmsdistRemote=sanitize(payload["cmsdist_remote"]),
       pkgtoolsRemote=sanitize(payload["pkgtools_remote"]),
       architecture=sanitize(runnableTask["architecture"]),
       release_name=sanitize(re.sub("_[A-Z]+_X", "_X", runnableTask["release"])),
       base_release_name=re.sub("_[^_]*patch[0-9]*$", "", sanitize(payload["release"])),
       real_release_name=sanitize(payload["release"]),
       package=sanitize(payload["package"]),
       repository=sanitize(payload["repository"]),
       syncBack=payload["syncBack"] == True and "--sync-back" or "",
       ignoreErrors=payload["ignoreErrors"] == True and "-k" or "",
       tmpRepository=sanitize(payload["tmpRepository"]),
       task_id=runnableTask["id"],
       jobs=opts.jobs,
       builders=opts.builders))
    getstatusoutput(format("echo 'Task %(task_id)s completed successfully.' >> %(workdir)s/log.%(task_id)s",
                           workdir=opts.workdir,
                           task_id=runnableTask["id"]))
  except Exception, e:
    log = open(format("%(workdir)s/log.%(task_id)s", workdir=opts.workdir, task_id=runnableTask["id"])).read()
    log += "\nInterrupted externally."
    log += str(e)
    getstatusoutput(format("echo 'Interrupted externally' >> %(workdir)s/log.%(task_id)s",
                           workdir=opts.workdir,
                           task_id=runnableTask["id"]))
    
  error, saveLog = getstatusoutput(format("set -e ;\n"
       "echo '#### Log file for %(task_id)s' >> %(workdir)s/log ;\n"
       "cat %(workdir)s/log.%(task_id)s >> %(workdir)s/log",
       workdir=opts.workdir,
       task_id=runnableTask["id"]))
  
  getstatusoutput("%s/syncLogs.py %s" % (thisPath, opts.workdir))
  if not "AUTOIB SUCCESS" in log:
    call(runnableTask["id"], "PATCH", 
         state="Failed", 
         url="http://cmssdt.cern.ch/SDT/tc-ib-logs/%s/log.%s.html" % (socket.gethostname(), runnableTask["id"] ))
    print log
    print saveLog
    sys.exit(1)
  
  call(runnableTask["id"], "PATCH", 
       state="Completed", 
       url="http://cmssdt.cern.ch/SDT/tc-ib-logs/%s/log.%s.html" % (socket.gethostname(), runnableTask["id"]))

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
    options.update(getExternalsTags(expandRelease("@QUEUE", payload["release"]), architecture))
    call("", "POST",
         release=sanitize(payload["release"]),
         architecture=sanitize(architecture),
         repository=sanitize(payload["repository"]),
         tmpRepository=sanitize(payload["tmpRepository"]),
         syncBack=payload["syncBack"],
         debug=payload["debug"],
         ignoreErrors=payload["ignoreErrors"],
         package=sanitize(package),
         PKGTOOLS=options["PKGTOOLS"],
         CMSDIST=options["CMSDIST"],
         continuations=options["continuations"]
        )

def listTasks():
  # Get the first task from the list
  # Check if we know what to do
  # Mark it as started
  # Start doing it
  parser = OptionParser(usage="%prog list [options]")
  parser.add_option("--match-arch", metavar="REGEX", dest="matchArch", help="Limit architectures to those matching REGEX", default=".*")
  parser.add_option("--match-release", metavar="REGEX", dest="matchRelease", help="Limit releases to those matching REGEX", default=".*")
  parser.add_option("--state", metavar="Running,Pending,Completed,Failed", dest="state", help="Show requests in the given state", default="Running")
  parser.add_option("--format", metavar="FORMAT", dest="format", help="Output format", default="%i: %p %r %a")
  parser.add_option("--api-url", metavar="URL", dest="apiUrl", help="Specify API endpoint", default=DEFAULT_API_URL)
  opts, args = parser.parse_args()
  setTCUrl(opts.apiUrl)
  results = call("/", "GET", 
                 release_match=opts.matchRelease,
                 architecture_match=opts.matchArch,
                 state=opts.state)
  if not results:
    sys.exit(1)
  replacements = [("i", "id"),
                  ("p", "package"),
                  ("a", "architecture"),
                  ("r", "release"),
                  ("s", "state")]
  opts.format = opts.format.replace("%", "%%")
  for x, y in replacements:
    opts.format = opts.format.replace("%%" + x, "%(" + y + ")s")
  results = [x.update(x["payload"]) or x for x in results]
  print "\n".join([opts.format % x for x in results])


# This will request to build a package in the repository.
# - Setup a few parameters for the request
# - Get PKGTOOLS and CMSDIST from TC if they are not passed
# - Create the request.
def requestBuildPackage():
  parser = OptionParser()
  parser.add_option("--release", "-r", metavar="RELEASE", dest="release", help="Specify release.", default=None)
  parser.add_option("--architecture", "-a", metavar="ARCHITECTURE", dest="architecture", help="Specify architecture", default=None)
  parser.add_option("--repository", "-d", metavar="REPOSITORY NAME", dest="repository", help="Specify repository to use for bootstrap", default="cms")
  parser.add_option("--upload-tmp-repository", metavar="REPOSITORY SUFFIX", dest="tmpRepository", help="Specify repository suffix to use for upload", default=getuser())
  parser.add_option("--pkgtools", metavar="TAG", dest="pkgtools", help="Specify PKGTOOLS version to use. You can specify <user>:<tag> to try out a non official tag.", default=None)
  parser.add_option("--cmsdist", metavar="TAG", dest="cmsdist", help="Specify CMSDIST tag branch to use. You can specify <user>:<tag> to try out a non official tag.", default=None)
  parser.add_option("--hostname-filter", metavar="HOSTNAME-REGEX", dest="hostnameFilter", help="Specify a given regular expression which must be matched by the hostname of the builder machine.", default=".*")
  parser.add_option("--sync-back", metavar="BOOL", dest="syncBack", action="store_true", help="Specify whether or not to sync back the repository after upload", default=False)
  parser.add_option("--ignore-compilation-errors", "-k", metavar="BOOL", dest="ignoreErrors", help="When supported by the spec, ignores compilation errors and still packages the available build products", action="store_true", default=False)
  parser.add_option("--api-url", metavar="url", dest="apiUrl", help="Specify the url for the API", default=DEFAULT_API_URL)
  parser.add_option("--continuations", metavar="SPEC", dest="continuations", help="Specify a comma separated list of task:architecture which need to be scheduled after if this task succeeds", default="")
  parser.add_option("--debug", metavar="BOOL", dest="debug", help="Add cmsbuild debug information", action="store_true", default=False)
  parser.add_option("--dry-run", "-n", metavar="BOOL", dest="dryRun", help="Do not push the request to tag collector", action="store_true", default=False)
  opts, args = parser.parse_args()
  if len(args) != 2:
    parser.error("You need to specify a package")
  setTCUrl(opts.apiUrl)

  if not opts.repository:
    parser.error("Please specify a repository")
  if not opts.release:
    parser.error("Please specify a release")
  if not opts.architecture:
    parser.error("Please specify an architecture")

  options = {}
  options["hostnameFilter"] = opts.hostnameFilter
  options["release"] = expandDates(opts.release)
  options["release_queue"] = expandRelease("@QUEUE", options["release"])
  options["architecture"] = opts.architecture
  options["repository"] = expandRelease(expandDates(opts.repository).replace("@ARCH", options["architecture"]), options["release"])
  options["tmpRepository"] = expandDates(opts.tmpRepository)
  options["syncBack"] = opts.syncBack
  options["package"] = expandDates(args[1])
  options["continuations"] = opts.continuations.replace("@ARCH", options["architecture"])

  options["ignoreErrors"] = opts.ignoreErrors
  options["debug"] = opts.debug

  if opts.cmsdist and opts.continuations:
    print format("WARNING: you have specified --pkgtools to overwrite the PKGTOOLS tag coming from tag collector.\n"
                 "However, this will happen only for %(package)s, continuations will still fetch those from the tagcolletor.", package=options["package"])

  if opts.cmsdist and opts.continuations:
    print format("WARNING: you have specified --cmsdist to overwrite the PKGTOOLS tag coming from tag collector.\n"
                 "However, this will happen only for %(package)s, continuations will still fetch those from the tagcolletor.", package=options["package"])

  # Get the mapping between architecture and release
  options.update(getExternalsTags(options["release_queue"], options["architecture"]))
 
  if opts.pkgtools:
    options["PKGTOOLS"] = sanitize(expandRelease(opts.pkgtools, options["release"]).replace("@ARCH", options["architecture"]))
  if opts.cmsdist:
    options["CMSDIST"] = sanitize(expandRelease(opts.cmsdist, options["release"]).replace("@ARCH", options["architecture"]))
  if not options.get("CMSDIST"):
    print "Unable to find CMSDIST for releases %s on %s" % (options["release"], options["architecture"])
    sys.exit(1)
  if not options.get("PKGTOOLS"):
    print "Unable to find PKGTOOLS for releases %s on %s" % (options["release"], options["architecture"])
    sys.exit(1)
  if opts.dryRun:
    print "Dry run specified, the request would look like:\n %s" % str(options)
    sys.exit(1)
  call("", "POST", **options)

def cancel():
  parser = OptionParser(usage="%prog cancel <request-id>")
  parser.add_option("--api-url", metavar="url", dest="apiUrl", help="Specify the url for the API", default=DEFAULT_API_URL)
  opts, args = parser.parse_args()
  setTCUrl(opts.apiUrl)
  if not len(args):
    print "Please specify a request id."
  ok = call(args[1], "DELETE")
  if not ok:
    print "Error while cancelling request %s" % args[1]
    sys.exit(1)

def reschedule():
  parser = OptionParser(usage="%prog reschedule <request-id>")
  parser.add_option("--api-url", metavar="url", dest="apiUrl", help="Specify the url for the API", default=DEFAULT_API_URL)
  opts, args = parser.parse_args()
  setTCUrl(opts.apiUrl)
  if not len(args):
    print "Please specify a request id."
  ok = call(args[1], "PATCH",
            pid="",
            machine="",
            url="",
            state="Pending")
  if not ok:
    print "Error while rescheduling request %s" % args[1]
    sys.exit(1)


COMMANDS = {"process": process, 
            "cancel": cancel,
            "list":  listTasks,
            "request": requestBuildPackage,
            "reschedule": reschedule
           }

if __name__ == "__main__":
  os.environ["LANG"] = "C"
  commands = [x for x in sys.argv[1:] if not x.startswith("-")]
  if len(commands) == 0 or not commands[0] in COMMANDS.keys():
    print "Usage: autoIB.py <command> [options]\n"
    print "Where <command> can be among the following:\n"
    print "\n".join(COMMANDS.keys())
    print "\nUse `autoIB.py <command> --help' to get more detailed help."
    sys.exit(1)
  command = commands[0]
  COMMANDS[command]()
