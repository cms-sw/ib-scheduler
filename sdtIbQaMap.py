StdIBQAMap = {
  'QALocal' :
  {
    'basePaths' : ['/build/cmsbuild','/build1/cmsbuild'],
    'dirsToDelete'  :
    {
      'own'   : ['stdTest-*/*/CMSSW_*','stdTest-*/*.log','stdTest/*.log','stdTest/*/CMSSW_*'],
      'sudo'  : [],
    },
    'daysToKeep': 2,
  },
  'QAWeb' : 
  {
    'basePaths' : ['/data'],
    'dirsToDelete'  : 
    {
      'own'   : ['intBld/incoming/*/*/CMSSW_*','intBld/incoming/vgCmds-CMSSW_*'],
      'sudo'  : ['intBld/incoming/qaInfo/CMSSW_*','sdt/sdtQA/intbld/CMSSW_*'],
    },
    'daysToKeep': 14,
  },
  'IBLocal' : 
  {
    'basePaths' : ['/build/intBld','/build1/intBld'],
    'dirsToDelete'  : 
    {
      'own'   : ['rc/*-*','cms/*/cms/cmssw/CMSSW_*'],
      'sudo'  : [],
    },
    'daysToKeep': 2,
  },
  'QAIgprof' :
  {
    'basePaths' : ['/afs/cern.ch/cms/sdt/web/qa/igprof/data'],
    'dirsToDelete'  :
    {
      'own'   : ['slc*/CMSSW_*','slc*/*/CMSSW_*'],
      'sudo'  : [],
    },
    'daysToKeep': 30,
  },
}


