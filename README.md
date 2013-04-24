## What is this

A bunch of script which CMS uses for building integration builds. Scripts
contributed by a bunch of different people.

## Deployment

Clone the repository and get the secrets:

    git clone <repository>
    cd ib-scheduler
    scp -l $CMS_ADMIN_USER lxplus.cern.ch:~/private/cmssw_secrets.py .

where `CMS_ADMIN_USER` has to be asked to the relevant persons in CMS. You will
need a valid certificate for the CERN SSO login.

To create a build request do:

    ./autoIB.py request -a <architecture> -k -r '<release-tag>' --sync-back --repository "cms.week@TW" <package>

to build the same build request:

    ./autoIB.py process -j <jobs> --match-arch "<architecture-reg-exp>" --top-dir <workdir> --max-load <max-load-average>

## Development

Open a pull request for each new feature.
