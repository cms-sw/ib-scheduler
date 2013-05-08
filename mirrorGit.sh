#!/bin/sh
MIRROR=/afs/cern.ch/cms/git-cmssw-mirror
CERN_REPO=https://:@git.cern.ch/kerberos
cd $MIRROR/cmssw.git ; git config http.postBuffer 209715200 ; git remote update origin ; git push --mirror $CERN_REPO/CMSSW.git
cd $MIRROR/cmsdist.git ; git config http.postBuffer 209715200 ; git remote update origin ; git push --mirror $CERN_REPO/CMSDIST.git
cd $MIRROR/pkgtools.git ; git config http.postBuffer 209715200 ; git remote update origin ; git push --mirror $CERN_REPO/PKGTOOLS.git
cd $MIRROR/cmssw-config.git ; git config http.postBuffer 209715200 ; git remote update origin ; git push --mirror $CERN_REPO/CMSSW/config.git
cd $MIRROR/SCRAM.git ; git config http.postBuffer 209715200 ; git remote update origin ; git push --mirror $CERN_REPO/SCRAM.git
cd $MIRROR/ib-scheduler.git ; git config http.postBuffer 209715200 ; git remote update origin ; git push --mirror $CERN_REPO/ib-scheduler.git
