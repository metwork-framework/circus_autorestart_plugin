from circus.plugins import CircusPlugin
from zmq.eventloop import ioloop
import os
import logging
from inotify_simple import flags, INotify
from gitignore_parser import parse_gitignore
from cached_property import cached_property

LOGGER = logging.getLogger("circus_autorestart_plugin")


def add_inotify_watch(inotify_handle, directory, include_function):
    """Register recursively directories to watch.

    Args:
        inotify_handle (inotify object): object that owns the file descriptors.
        directory (string): complete path of a directory to scan.
        include_function (function): function which takes a relative path as
            argument and which returns True if the file/directory must be
            monitored.

    """
    if not os.path.isdir(directory):
        return {}
    if not os.access(directory, os.R_OK):
        return {}
    wds = {}
    watch_flags = flags.CLOSE_WRITE | flags.CREATE |\
        flags.DELETE | flags.DELETE_SELF | flags.ATTRIB
    try:
        LOGGER.info("watch %s" % directory)
        wd = inotify_handle.add_watch(directory, watch_flags)
        wds[wd] = directory
    except Exception as e:
        LOGGER.warning("cannot watch %s: %s" % (directory, e))
    if not os.access(directory, os.R_OK):
        LOGGER.warning("cannot enter into %s" % directory)
        return wds
    for name in os.listdir(directory):
        fullpath = os.path.join(directory, name)
        if os.path.isdir(fullpath):
            if not include_function(fullpath):
                continue
            wds2 = add_inotify_watch(inotify_handle, fullpath,
                                     include_function)
            wds.update(wds2)
    return wds


class MonitoredWatcher(object):

    name = None
    working_dir = None
    inotify_handle = None
    wds = None

    def __init__(self, name, working_dir):
        self.name = name
        self.working_dir = working_dir

    def start_monitoring(self):
        self.inotify_handle = INotify()
        self.wds = add_inotify_watch(self.inotify_handle, self.working_dir,
                                     self.include_function)
        for wd, directory in self.wds.items():
            LOGGER.debug("%s monitored on wd:%i" % (directory, wd))

    @cached_property
    def exclude_matches(self):
        if os.path.exists("%s/.autorestart_excludes" % self.working_dir):
            return parse_gitignore("%s/.autorestart_excludes" %
                                   self.working_dir)
        else:
            return lambda x: False

    @cached_property
    def include_matches(self):
        if os.path.exists("%s/.autorestart_includes" % self.working_dir):
            return parse_gitignore("%s/.autorestart_includes" %
                                   self.working_dir)
        else:
            return lambda x: True

    def include_function(self, path, debug_output=True):
        # pylint: disable-msg=E1121
        imatches = self.include_matches
        ematches = self.exclude_matches
        if not os.path.isdir(path):
            if not imatches(path):
                if debug_output:
                    LOGGER.debug("path: %s excluded from monitoring "
                                 "(because of includes)" % path)
                return False
        if ematches(path):
            if debug_output:
                LOGGER.debug("path: %s excluded from monitoring "
                             "(because of excludes)" % path)
            return False
        return True

    def need_restart(self):
        result = False
        for event in self.inotify_handle.read(0):
            LOGGER.debug("inotify event received for watcher %s: %s" %
                         (self.name, event))
            wd = event.wd
            if wd not in self.wds:
                LOGGER.warning("bad file descriptor: %i ? => ignoring" % wd)
                continue
            fullpath = os.path.join(self.wds[wd], event.name)
            if result:
                continue
            if self.include_function(fullpath, debug_output=False):
                LOGGER.info("Restarting watcher: %s because of changes in %s" %
                            (self.name, fullpath))
                result = True
            else:
                LOGGER.debug("=> ignoring event")
        return result


class CircusAutorestartPlugin(CircusPlugin):

    name = "autorestart"
    periodic = None
    monitored_watchers = None

    def __init__(self, *args, **config):
        """Constructor."""
        super(CircusAutorestartPlugin, self).__init__(*args, **config)
        self.monitored_watchers = {}

    def initialize(self):
        """Initialize method called at plugin start.

        The method register the periodic callback of the ping() method
        and fill the monitored_watchers dict.
        """
        super(CircusAutorestartPlugin, self).initialize()
        self.fill_watchers(debug_output=True)
        self.periodic = ioloop.PeriodicCallback(self.ping, 1000, self.loop)
        self.periodic.start()
        self.periodic10 = ioloop.PeriodicCallback(self.fill_watchers, 10000,
                                                  self.loop)
        self.periodic10.start()

    def handle_recv(self, data):
        pass

    def is_watcher_active(self, watcher_name):
        """Return True if the watcher is in active state.

        Args:
            watcher_name: the name of the watcher (string).
        """
        msg = self.call("status", name=watcher_name)
        return (msg.get('status', 'unknown') == 'active')

    def ping(self):
        for monitored_watcher in self.monitored_watchers.values():
            need_restart = monitored_watcher.need_restart()
            if need_restart:
                if self.is_watcher_active(monitored_watcher.name):
                    LOGGER.info("killing watcher %s" % monitored_watcher.name)
                    self.call("kill", name=monitored_watcher.name, signum=9)

    def fill_watchers(self, debug_output=False):
        msg = self.call("list")
        if 'watchers' in msg:
            self.monitored_watchers = \
                {x: y for x, y in self.monitored_watchers.items()
                 if x in msg['watchers']}
            for watcher in msg['watchers']:
                if watcher in self.monitored_watchers:
                    continue
                msg = self.call("options", name=watcher)
                if 'options' in msg:
                    working_dir = msg['options'].get('working_dir', '')
                    if not os.path.exists("%s/.autorestart_includes" %
                                          working_dir) and \
                            not os.path.exists("%s/.autorestart_excludes" %
                                               working_dir):
                        if debug_output:
                            LOGGER.debug("ignoring %s watcher because we can't"
                                         " find %s/.autorestart_includes/"
                                         "excludes file" %
                                         (watcher, working_dir))
                        continue
                    monitored_watcher = MonitoredWatcher(watcher, working_dir)
                    self.monitored_watchers[watcher] = monitored_watcher
                    monitored_watcher.start_monitoring()
