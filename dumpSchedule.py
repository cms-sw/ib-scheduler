#!/usr/bin/env python

import os, sys

cmd = '/usr/bin/acrontab -l >/afs/cern.ch/cms/sdt/web/SDT/schedule.dump'

ret = os.system(cmd)
if ret != 0:
    print "Error executing cmd:",cmd,'ret=',ret
