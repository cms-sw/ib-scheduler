#!/usr/bin/python
# -*- coding: utf-8 -*-
from os import getpid, makedirs, kill
from os.path import join, getmtime
from commands import getstatusoutput
from time import sleep, time


def isProcessRunning(pid):
    running = False
    try:
        kill(pid, 0)
        running = True
    except:
        pass
    return running


class Lock(object):

    def __init__(
        self,
        dirname,
        checkStale=False,
        stableGap=600,
        ):
        self.piddir = dirname
        self.pidfile = join(self.piddir, 'pid')
        self.pid = str(getpid())
        self.locktime = 0
        self._hasLock = self._get()
        if not self._hasLock and self.locktime and checkStale \
            and time() - self.locktime >= stableGap:
            self._release(True)
            self._hasLock = self._get()

    def getLock(self, waitStep=2, maxTries=0):
        if waitStep <= 0:
            waitStep = 2
        while not self._hasLock:
            sleep(waitStep)
            self._hasLock = self._get()
            if maxTries > 0:
                maxTries -= 1
                if maxTries <= 0:
                    break
        return

    def __del__(self):
        self._release()

    def __nonzero__(self):
        return self._hasLock

    def _release(self, force=False):
        if not force and self._hasLock and self._get():
            force = True
        if force:
            getstatusoutput('rm -rf %s' % self.piddir)
        self.locktime = 0
        self._hasLock = False

    def _get(self, tries=3, success=3):
        if tries <= 0:
            return False
        pid = self._readPid()
        if pid:
            if pid == self.pid:
                if success <= 0:
                    return True
                sleep(0.001)
                return self._get(tries, success - 1)
            if isProcessRunning(int(pid)):
                return False
        self._create()
        sleep(1)
        return self._get(tries - 1, success)

    def _readPid(self):
        pid = None
        try:
            pid = open(self.pidfile).readlines()[0]
            self.locktime = getmtime(self.pidfile)
        except:
            pid = None
        return pid

    def _create(self):
        self._release(True)
        try:
            makedirs(self.piddir)
            lock = open(self.pidfile, 'w')
            lock.write(self.pid)
            lock.close()
        except:
            pass


