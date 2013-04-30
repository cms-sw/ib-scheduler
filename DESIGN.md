# A new build infrastructure

## Design goals and features description

This is a specification on how the new IB machinery is supposed to work.

The goal of this design is to provide a simple yet flexible and pluggable way
of doing build tasks, which are specified in form of a `spec` file present in
`CMSDIST` plus some additional attributes that specify a few configurable
parameters (See the section Build Task Specification). `cmsBuild` is used to do
the actual building, as usual.

The apt repository, <http://cmsrep.cern.ch/cmssw/>, is used to host result of
all build tasks, sometimes in form of RPMS, some other times in form of misc
files under the `WEB` subdirectory of the repository. This most notably allows
installable RPM distributions for Integration Builds (*IBs*).

In order to prevent bloating of the production `cms` repository, a
double-buffering-like technique, is used where two temporary repositories (e.g.
`cms.week0`, `cms.week1`) are alternatively reset on bi-weekly basis while the
system populates the other. This effectively provides a two weeks rolling
window which contains the results of build. This is particularly suitable for
automating all the tasks related to IBs as the time limited availability of
those is generally considered a more than acceptable tradeoff. The size of the
rolling window is just limited by the amount of space available in the apt
repository (2TB at the moment). Normal release builds will use the usual
central `cms` repository.

The actual build work is carried out by a pool of undifferentiated machines.
The machines themselves only need to be a viable CMSSW build machines but apart
from that no machine is actually bound to a given task. 

Tasks queue in the task queue are all unrelated and can be executed in
parallel. If tasks require some dependency this is implemented by the mean of
continuations (see below).

## Implementation notes

The design heavily relies on the fact that parallel uploads to the apt
repository can be done in a safe, transactional way and which can be
rolled-back at any moment. The new upload mechanism, in place since fall last
year, guarantees this.

The tag collector is used to keep track of all the requested build tasks and
effectively act as a task queue. Those request are marked of type `TASK-<hash>`
inside the database and they can be observed in the usual [custom
IB](https://cmstags.cern.ch/tc/#CustomIBs) page. The `<hash>` part is a unique
identifier for a class of build tasks, for example building a cmssw release. At
the moment this is merely the name of the package being built. 

A new script
[`CmsIntBld/IntBuild/script/autoIB.py`](http://svnweb.cern.ch/world/wsvn/CMSIntBld/trunk/IntBuild/scripts/autoIB.py)
has been introduced which can be used to control the whole process of queueing
tasks in the tag collector task queue as well as listing and processing them.

The script acts as a driver for different sub-commands, ala cvs or git, which
then do the actual job. The list of commands currently supported is:

- `request [options] -r <release-name> -a <architecure> <package>`: enqueue a request to build `<package>` associated to a given `<release-name>` and `<architecture>` pair.  The rest of the options allow to better specify what the payload looks like and how 
- `process`: pick a task from the tag queue.
- `list`: list the pending tasks
- `cancel <task_id>`: cancel the given `<task_id>`

This consolidates most of the scripts which were previously being used under a
single script and works for both cases of publishing a build request in tag
collector, processing requests on client nodes as well as performing some
maintenance tasks.

Particular attention is given to make sure that most of the options match their
`cmsBuild` counterpart when they are passed on to it.

### Queuing a new task

Queueing a new task is done by the `autoIB.py request` command.

In general tasks can also be queued manually, however the most common usage is
done by `cmsbuild` user's `acrontab` to schedule the IB jobs.

Queueing by hand is nevertheless interesting for the case in which one wants to
do a one time build and upload action, e.g. a release, or some new external to
be tested before integration in the normal build workflow. 


#### Basic usage

All tasks refer to building and uploading some spec file in `CMSDIST`, so that
adding new tasks is simply a matter of implementing the appropriate spec file.

Besides the name of the spec file to build and upload, one can specify the
source repository (e.g. `--repository cms`), the destination repository (e.g.
`--upload-tmp-repository weekly1` for `cms.weekly1`) and whether or not the
system needs to sync back (via the usual `--sync-back` flag which is there in
`cmsBuild`). This allows us to control whether or not an upload needs to end up
in the official repository or in some test one. E.g:

  autoIB.py request -a slc5_amd64_gcc472 \
             -r 'CMSSW_6_2_X_%Y-%m-%d-1400' \
             --repository cms \
             --upload-tmp-repository week1 \
             cmssw

will queue building of a CMSSW IB and upload it in a temporary repository
called `cms.week1`. Notice that the release name will always be substituted in
your `cmssw.spec`, regardless of what package you are building.

A special package called `dummy` which can be used to always build and upload
something. This can be used in the case one needs to create a temporary
repository to be populated later.

Moreover all the options are passed through `strftime` and a filter which
replaces the special strings `@TW` and `@NW` to refer to the week number in the
year, current week and next week respectively, modulo 2. This is useful to
alternate repositories every other week.

A few other build options which are commonly available in cmsBuild are
available:

- `--ignore-compilation-error` or `-k` which can be handy to create IB packages.

#### Specifying continuations

It is sometimes desirable to schedule tasks only after the successful
completion of another, possibly unrelated, task.

This is supported by `autoIB.py` via the `--continuations` option.

Such an option takes a comma separated list of pairs `<package>:<architecture>`
to be scheduled after the completion of the task they are attached to. All the
other options in the task will stay the same and the tasks specified will be
executed in parallel.

In case there is need for continuations of continuations they can be specified
by adding one or more additional list, separating them via a semi-colon. E.g.:

  cmssw:slc5_amd64_gcc472,cmssw:slc6_amd64_gcc472;\
  cmssw-validation:slc5_amd64_gcc472,cmssw-extra-tests:slc6_amd64_gcc472,\
  dummy:slc7_amd64_gcc500
  
in this case the additional continuations will be scheduled added only to the
task which have a matching architecture. In the above case this means:

- building `cmssw` for both `slc5_amd64_gcc472` and `slc6_amd64_gcc472` will be
  scheduled once the main task completes.
- `cmssw-validation` will be run as a continuation of the `slc5` `cmssw`, while
  `cmssw-extra-tests` will be scheduled when the `slc6` build completes.
  `dummy` will not be scheduled because there is no initial continuation which
  uses its architecture.

By exploiting the usage of the `%cmsroot/WEB/` area provided by the new upload
mechanism of `cmsBuild`, rpm building can be used to publish result of complex
processing tasks on the web. For example those coming from running release
validation steps and so on. This will hopefully consolidate all the different
"post-build" steps which we currently have into one single kind of workflow.

#### Overriding contents of CMSDIST / PKGTOOLS

Sometimes it's useful for testing purposes to be able to override `CMSDIST` and
/ or `PKGTOOLS` tags or even single files into `CMSDIST`.

Overriding tags can be done by using the `--cmsdist TAG` and `--pkgtools TAG`
options.

Overriding single files in `CMSDIST` can be done by using the `--override`
option instead. It take a comma separate list of `file:revision` pairs. So for
example one could use:

  --override scram-project-build.spec:1.125

to overide `scram-project-build.spec` with revision `1.125`.

### Processing tasks

The tasks queued by the `request` sub-command described above can be processed
using the `process` sub-command. Such a command takes two options
`--match-arch` and `--match-release` which can be used to restrict the kind of
tasks that it will process.

An additional option `--top-dir <top-dir>` can be used to specify in which
directory the processing will happen. There a directory which has the same name
as the request id in tag collector will contain a checkout of the requested
`PKGTOOLS` / `CMSDIST` instances.

`PKGTOOLS` will use `<top-dir>/b` as its own workdir, while the log file of the
process will be found in `<top-dir>/log.<request_id>`. The autoIB command will
also take care of synchronizing those log files and those coming from the build
itself into to `http://cmssdt.cern.ch/SDT/tc-ib-logs/<machine-name>`. The tasks
in tag collector will be updated so that they will point to their own log.

A few other build options which are commonly present in `cmsBuild` are also
available:

- `--builders` which can be used to specify how many packages build in parallel
  in one single task.
- `--jobs` or `-j` which specifies how many threads to use to build a single
  package

#### Opportunistic resource usage

Some machine are available for users to so some occasional heavy duty tasks,
however most of the machines are idle for large part of the time.

`autoIB.py` provides means to use those machines in an opportunistic way via
the `--max-load <load>` option which can be used to avoid processing a task
while the machine is being used by someone else and its loads exceeds the
`<load>` specified.

Future extensions of the system might include time based limitations of on the
kind of task being executed, i.e. more powerful machines will do more time
consuming jobs.

#### Post-processing logs

Two kind of build logs are available when building a package. The first one is
the log of `cmsBuild` process itself and then there is the `rpmbuild` build
logs for each one of the packages being built. The former is stored in
`<top-dir>/log.<request-id>` while those of the latter kind are found in the
usual `<top-dir>/b/BUILD/<architecture>/<group>/<package>/<version>/log`
location for a given package.

Every time `autoIB.py process` is invoked, those logs are synchronized to a web
directory, so that one can follow the progress of a build from the web. Links
to the logs are updated in tag collector as soon as they are available and
presented in the [task report view](https://cmstags.cern.ch/tc/#CustomIBs). 

This is done by a `syncLogs.py` script which is invoked at the beginning of
every `autoIB.py` process, regardless or not if there is another process
already running. This allows having an almost live updating of logs.

The same helper script takes care of improving the logs so that they are more
browser friendly. Additional decorations to the logs can be put there but keep
in mind that such a decoration is run every single time `autoIB.py process` is
run, so it needs to be as quick as possible to avoid interfering with the
normal processing of tasks. However, given the design decision of processing
all the tasks using `cmsBuild`, a better approach to this would be to have an
HTML mode for its logs so that they can be immediately used.

### Deployment

#### Deploying server

There is no server component specific to the new IB infrastructure. The new
design depends on Tag Collector and the apt server, but those are supposed to
be already existing and working regardless of how we build IBs.

#### Deploying clients

Deploying clients is as easy as checking out the `CMSIntBld` from svn and
adding the appropriate line in the `crontab` / `acrontab`. The user performing
the build should have `cmsbuild` password-less certificate and key in
`~/.globus` and its `id_dsa` in `~/.ssh` so that it can get payloads from
`cmstags.cern.ch` in an authenticated manner and upload results to
`cmsrep.cern.ch`. For the same reason the firewall of the build machine should
allow reaching the two above mentioned servers.

### Security issues.

Since the service allows building RPMs remotely and uploading them to a web
server, security must be a major concern.

All the user provided options are considered unsafe by the `autoIB.py process`
which provides to sanitize all of them as they come from the payload.

Moreover due to the fact that tasks are specified as `spec` files in `CMSDIST`
malicious payloads have to be committed there first, which is only possible for
a restricted number of cms users.

The build jobs themselves, run as the unprivileged `cmsbuild` user.

Finally only CMS SSO authenticated users can submit build jobs. 

## A working testbed.

A working testbed of the IB infrastructure is currently being put in place. It
uses the production tag collector, the [cmssdt website](http://cmssdt.cern.ch)
and two temporary repositories `cms.week1` and `cms.week0` to run a number of
IBs and related tasks. In particular:

- The two repositories contain bi-daily RPMs for the the `CMSSW_6_2_X` IB, on
  `slc5_amd64_gcc472`.
- A short matrix is run at the completion of the builds. Its results are
  published here: <http://cmsrep.cern.ch/cmssw/cms.week1/WEB/ib-results/>
- For linux machines, `acrontab` is currently used to schedule builds. Current
  testbed description can be found
  [here](http://svnweb.cern.ch/world/wsvn/CMSIntBld/trunk/deploy/cms-ib-sched/acrontab).
  New infrastructure is defined at the end.
- Examples on how to use a `CMSSW` build to run some tests and publish results
  can be found
  [here](http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/cmssw-validation.spec?revision=1.17&view=markup).

### Installing releases on AFS

Installing releases on `AFS` is done via the
`CmsIntBld/scripts/autoInstaller.sh` script. Such a script takes care of
installing releases in `/afs/cern.ch/cms/sw/ReleaseCandidates/vol{0,1}` from
the `cms.week{0,1}` repositories. The script takes care of cleaning and
bootstrapping the area every week, alternating: one week `vol0` and the other
`vol1`.

## Known issues with the current specification and its implementation

- Multiple continuations are not implemented yet. Only one level of
  continuations works correctly.
- Currently the build area is scratched every time. While this is not a big
  deal, it could result in high-loads on `cmsrep.cern.ch` when N IBs start at
  the same time. We should get a list of all the package which were built,
  delete them and try to install them from server.
- Find a better name for `autoIB.py`
- Describe the naming of tasks in tag collector.
- Add paragraph on stats about the system, SLOC, etc.
- Add paragraph about future work.
- Restrict ability to submit build jobs to only certain privileged users? Allow
  `autoIb.py` to only process requests coming from certain users? 
