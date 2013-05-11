#!/usr/bin/env python

from distutils.core import setup
setup(name='IB Scheduler',
      version='1.0',
      description='CMS IB Utilities',
      author='CMS Collaboration',
      author_email='hn-cms-sw-develtools@@cern.ch',
      url='http://cmssdt.cern.ch',
      py_modules=["tagCollectorAPI",
                  "ws_sso_content_reader",
                  "all_json",
                  "Lock"],
      scripts=['autoIB.py']
     )

