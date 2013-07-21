#!/usr/bin/env python
# A simple script which creates IBs in git.
from commands import getstatusoutput
from optparse import OptionParser
from datetime import datetime, timedelta
from time import strftime
import re

def expandDates(s):
  today = datetime.today()
  tw=str(int(today.strftime("%W")) % 2)
  nw=str(int((today + timedelta(days=7)).strftime("%W")) % 2)
  pw=str(int((today + timedelta(days=-7)).strftime("%W")) % 2)
  return strftime(s.replace("@TW", tw).replace("@NW", nw).replace("@PW", pw))

def format(s, **kwds):
  return s % kwds

def tagRelease(tag, branch, timestamp):
  (day, t) = timestamp.rsplit("-", 1)
  hour = t[0:2] + ":" + t[2:4]
  
  cmd = format("set -e;"
               "TEMP=`mktemp -d`;"
               "if [ -d /afs/cern.ch/cms/slc5_amd64_gcc472/external/git/1.8.3.1/etc/profile.d/init.sh ]; then"
               "  source /afs/cern.ch/cms/slc5_amd64_gcc472/external/git/1.8.3.1/etc/profile.d/init.sh;"
               "fi;"
               "git clone $REFERENCE -b %(branch)s git@github.com:cms-sw/cmssw.git $TEMP/cmssw;"
               "cd $TEMP/cmssw;"
               "git tag %(tag)s `git rev-list -n 1 --before='%(day)s %(hour)s' %(branch)s`;"
               "git push origin --tags;"
               "rm -rf $TEMP",
               day=day,
               hour=hour,
               branch=branch,
               tag=tag)
  err, out = getstatusoutput(cmd)
  if err:
    print "Error while executing command:"
    print cmd 
    print out
  

if __name__ == "__main__":
  parser = OptionParser()
  parser.add_option("-b", "--base", help="The release branch to use for this.", default=None, dest="base")
  parser.add_option("-D", "--date", help="Use this timestamp for the tag.", default=None, dest="timestamp")
  opts, args = parser.parse_args()
  if len(args) == 0:
    parser.error("You need to specify a tag")
  if len(args) > 1:
    parser.error("Too many tags")

  release = expandDates(args[0])
  if not opts.base:
    m = re.match("(CMSSW_[0-9]+_[0-9]+).*", release)
    if not m:
      parser.error("Could not determine the release branch, please provide one with -b, --base")
    opts.base = m.group(1) + "_X"

  if opts.timestamp:
    opts.timestamp = expandDates(opts.timestamp)
  else:
    m = re.match("CMSSW_[0-9]+_[0-9]+_.*?([0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4})$", release)
    if not m:
      parser.error("Could not determine date from release name. Please specify it via -D")
    opts.timestamp = m.group(1)
  
  tagRelease(release, opts.base, opts.timestamp)
