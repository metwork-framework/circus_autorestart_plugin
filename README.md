# circus_autorestart_plugin

[//]: # (automatically generated from https://github.com/metwork-framework/github_organization_management/blob/master/common_files/README.md)

**Status (master branch)**



[![Drone CI](http://metwork-framework.org:8000/api/badges/metwork-framework/circus_autorestart_plugin/status.svg)](http://metwork-framework.org:8000/metwork-framework/circus_autorestart_plugin)
[![Maintenance](https://github.com/metwork-framework/resources/blob/master/badges/maintained.svg)]()




## What is it ?

This is a [circus](https://circus.readthedocs.io) plugin to automatically restart
a watcher if a FS change is observed (with inotify) inside the watcher workdir.

You can provide some inclusions and exclusions to avoid restart for changes on specific files/directories
with a `gitignore` like syntax.

## Install

Add this to your `circus` configuration:

```
[plugin:autorestart]
use = circus_autorestart_plugin.CircusAutorestartPlugin
```

## Configure

To use this feature, your watcher must set (in its `circus` configuration) a `working_dir` with:

- `.autorestart_includes`
- (and/or) `.autorestart_excludes`

Both files follow `gitignore` syntax even there are some specific limitations to the [python wrapper used](https://github.com/mherrmann/gitignore_parser/issues/1).

The plugin add inotify watches to every subdirectories of the configured `working_dir` which don't
match with `.autorestart_excludes` (if it exists). The `working_dir` itself is always watched.

When a FS event is received, if the corresponding file matches `.autorestart_includes` (if it exists) and not matches `.autorestart_excludes` (if it exists), the watcher is killed (and
`circus` should restart it).

## Limitations

At this moment:

- we just kill the watcher (`SIGKILL`) and we hope than `circus` will relaunch it (be careful if your `circus` is not configured to do that).
- if a new directory is created, it's not automatically watched itself.
- it seems that the `gitignore` parser used [is not perfect](https://github.com/mherrmann/gitignore_parser/issues/1).






## Contributing guide

See [CONTRIBUTING.md](CONTRIBUTING.md) file.



## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) file.



## Sponsors

*(If you are officially paid to work on MetWork Framework, please contact us to add your company logo here!)*

[![logo](https://raw.githubusercontent.com/metwork-framework/resources/master/sponsors/meteofrance-small.jpeg)](http://www.meteofrance.com)
