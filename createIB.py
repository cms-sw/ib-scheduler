#!/usr/bin/env python

import sys, os
import tagCollectorAPI
from optparse import OptionParser
from all_json import loads,dumps

if __name__ == '__main__':
  parser = OptionParser(usage="%(prog)s [--dry-run] -r <release-cycle> -p <parent-release> <archs>")
  parser.add_option("-n", "--dry-run", dest="dryRun", action="store_true", help="Do not actually execute")
  parser.add_option("-r", "--releasecycle", dest="releaseCycles", help="Release cycle")
  parser.add_option("-p", "--parent-release", dest="parentRelease", help="Parent release")

  opts, args = parser.parse_args()
  if not args:
    parser.error("Please specify at least one architecture")
  if len(args) != 1:
    parser.error("Please specify one and only one release cycle you want to create an IB for.")
  architectures = args[0].split(',')

  json_archs = dumps([x.strip() for x in architectures])
  release = 'CMSSW_' + opts.releaseCycles.replace('.','_') + '_X'

  isReleaseCreated, snapshotName = tagCollectorAPI.mkSnapshot(release, architectures=json_archs, parentRelease=opts.parentRelease)
  if not isReleaseCreated:
    parser.error("Could not create release.")
  if not snapshotName:
    parser.error("Could not create snapshot.")
  tagCollectorAPI.createIBRequest(snapshotName, architectures)
