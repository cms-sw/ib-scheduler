#!/usr/bin/env python
import os,sys,re, getpass
import time, datetime

thisPath = os.path.abspath(sys.argv[0])
try:                  scriptPath = os.path.abspath(__file__)
except Exception, e : scriptPath = thisPath

class Process:
  def __init__(self):
    self.child = []
    self.cmd = ''
    self.arg = ''
    self.ppid = 0
    self.stime = None
    self.xinfo = []

  def data(self, ppid, cmd, arg, stime, xinfo):
    self.cmd = cmd
    self.arg = arg
    self.ppid = ppid
    self.xinfo = xinfo.split()    
    self.stime = datetime.datetime.today() - datetime.datetime(*time.strptime(stime, '%a %b %d %H:%M:%S %Y')[0:6])
    self.stime = (self.stime.days*86400)+self.stime.seconds

  def addChild(self, pid):
    self.child.append(pid)

class ProcessTree:
  def __init__(self, user=None, detail=False, xinfo=None,show=False):
    self.allProcesses(user, xinfo)
    self.detail = detail
    self.show = show

  def allProcesses(self, user=None, xinfo=None):
    if not user: user = getpass.getuser()
    cmd = 'ps -ao '
    if xinfo: cmd += xinfo+','
    cmd += 'pid,ppid,lstart,comm,args -U %s -u %s' % (user,user)
    pipe = os.popen(cmd)
    res = pipe.readlines()
    pipe.close()
    self.all = {}
    pRE = re.compile('^\s*(.*\s+|)(\d+)\s+(\d+)\s+([A-Za-z]{3} [A-Za-z]{3} \s*\d{1,2} \d\d:\d\d:\d\d \d{4})\s+([^\s]+)\s*(.*)$')
    xpid = os.getpid()
    for pros in res:
      m = pRE.match(pros)
      if m:
         pid = m.group(2)
         ppid = m.group(3)
         if (int(pid) == xpid): continue
         if not self.all.has_key(ppid): self.all[ppid]=Process()
         if not self.all.has_key(pid):  self.all[pid]=Process()
         self.all[pid].data(ppid, m.group(5), m.group(6), m.group(4),m.group(1))
         self.all[ppid].addChild(pid)
    return

  def updateSelected(self, command=None, args=None, xpid=None):
    if not command: command = '.+'
    if not args:    args    = '.*'
    self.selected = {}
    self.selectedTree = []
    cRE = re.compile(command)
    aRE = re.compile('.*'+args+'.*')
    for pid in self.all:
      if xpid:
        if (pid == xpid):
          self._addChildren(pid)
          break
      elif cRE.match(self.all[pid].cmd) and aRE.match(self.all[pid].arg): self._addChildren(pid)
    for p in self.selected: self.dumpParentTree(p)

  def dumpParentTree(self, pid):
    if pid in self.selectedTree: return
    ppid = self.all[pid].ppid
    if ppid in self.selected: self.dumpParentTree(ppid)
    else: self.printInfo(pid)

  def printInfo(self, pid, tab=''):
     if not (pid in self.selected): return
     cmd = self.all[pid].cmd
     arg = self.all[pid].arg
     stime = str(self.all[pid].stime)
     if not self.detail:
       cmd = cmd[0:25]
       arg = arg[0:120]  
     if self.show: print tab+pid+'  '+self.all[pid].ppid+'  '+stime+'  '+'  '.join(self.all[pid].xinfo)+'  '+cmd+' '+arg
     self.selectedTree.append(pid)
     for p in self.all[pid].child: self.printInfo(p, tab+'  ')

  def _addChildren(self, pid):
    self.selected[pid]=1
    for p in self.all[pid].child: self._addChildren(p)

  def killSelected(self, command, args, xpid):
    if not xpid:
      if (not command) or (not args): return
    self.updateSelected(command, args, xpid)
    if not self.selected: return
    cmd = 'kill -9 '
    for pid in self.selected: cmd += pid+' '
    print 'Running ',cmd
    pipe = os.popen(cmd)
    res = pipe.readlines()
    pipe.close()
    return
# ================================================================================

def usage():
  print "usage:", os.path.basename(sys.argv[0]), " --cycle <releaseCycle> [--platfrom <SCRAM_ARCH>]"
  return

# ================================================================================

def checkRemoteStdTests(cycle, user, kill):
  precmd = "ps -ao args -U %s -u %s | grep '^ssh '" % (user, user)
  cmd = precmd + " | grep CMSSW_%s_X_20 | awk '{print $4}' | sed 's|.*/CMSSW_|CMSSW_|;s|/cmdFile.*||' | sort | uniq" %  (cycle)
  pipe = os.popen(cmd)
  rels = pipe.readlines()
  pipe.close()
  for rel in rels:
    rel = rel.strip('\n')
    print "Release "+rel
    cmd = precmd + " | grep %s | awk '{print $3}' | sort | uniq" % (rel)
    pipe = os.popen(cmd)
    machs = pipe.readlines()
    pipe.close()
    cscript = os.path.join(os.environ["HOME"], os.path.basename(scriptPath))
    for mach in machs:
      mach = mach.strip('\n')
      cmd = 'cp -u %s %s; ssh %s "%s --command tcsh --args /%s/cmdFile" %s'
      cmd = cmd % (scriptPath, cscript, mach, cscript, rel, kill)
      print "cmd> %s" % (cmd)
      pipe = os.popen(cmd)
      for line in pipe.readlines(): print line.strip('\n')
      pipe.close()
  return

def main():
  import getopt
  options = sys.argv[1:]
  try:
    opts, args = getopt.getopt(options, 'h',['help', 'kill', 'detail', 'cycle=', 'user=', 'command=', 'args=','pid=','pinfo='])
  except getopt.GetoptError, msg:
    print msg
    usage()
    sys.exit(-2)

  cyc     = None
  command = None
  args    = None
  user    = getpass.getuser()
  xpid    = None
  kill    = ''
  detail  = False
  xinfo   = None
  for o, a in opts:
    if o in ('-h', '--help'):
      usage()
      sys.exit()
    elif o in ('--cycle',):
      cyc = a
    elif o in ('--user'):
      user = a
    elif o in ('--detail'):
      detail = True
    elif o in ('--command'):
      command = a
    elif o in ('--args'):
      args = a
    elif o in ('--kill', '-k'):
      kill = o
    elif o in ('--pid'):
      xpid = a
    elif o in ('--pinfo'):
      xinfo = a
  if cyc:
    checkRemoteStdTests(cyc,user,kill)
  else:
    x = ProcessTree(user, detail, xinfo,True)
    if kill: x.killSelected  (command, args, xpid)
    else:    x.updateSelected(command, args, xpid)
  return

# ================================================================================
if __name__ == "__main__": sys.exit(main())
