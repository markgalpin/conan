import argparse
import os
import platform
from contextlib import contextmanager

winpylocation = {"py27": "C:\\Python27amd64\\python.exe",
                 "py36": "python.exe"}

macpylocation = {"py27": "/usr/local/bin/python",
                 "py37": "/usr/local/bin/python3"}

linuxpylocation = {"py27": "/usr/bin/python2.7",
                   "py34": "/usr/bin/python3.4",
                   "py36": "/usr/bin/python3.6",
                   "py37": "/usr/bin/python3.7"}


def get_environ(tmp_path):
    if platform.system() == "Windows":
        return {"CONAN_BASH_PATH": "c:/tools/msys64/usr/bin/bash",
                "CONAN_USER_HOME_SHORT": os.path.join(tmp_path, ".conan")}
    return {}


class Extender(argparse.Action):
    """Allows to use the same flag several times in a command and creates a list with the values.
       For example:
           conan install MyPackage/1.2@user/channel -o qt:value -o mode:2 -s cucumber:true
           It creates:
           options = ['qt:value', 'mode:2']
           settings = ['cucumber:true']
    """
    def __call__(self, parser, namespace, values, option_strings=None):  # @UnusedVariable
        # Need None here incase `argparse.SUPPRESS` was supplied for `dest`
        dest = getattr(namespace, self.dest, None)
        if not hasattr(dest, 'extend') or dest == self.default:
            dest = []
            setattr(namespace, self.dest, dest)
            # if default isn't set to None, this method might be called
            # with the default as `values` for other arguments which
            # share this destination.
            parser.set_defaults(**{self.dest: None})

        try:
            dest.extend(values)
        except ValueError:
            dest.append(values)


@contextmanager
def environment_append(env_vars):
    old_env = dict(os.environ)
    for name, value in env_vars.items():
        if isinstance(value, list):
            env_vars[name] = os.pathsep.join(value)
            if name in old_env:
                env_vars[name] += os.pathsep + old_env[name]
    os.environ.update(env_vars)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_env)


@contextmanager
def chdir(newdir):
    old_path = os.getcwd()
    os.chdir(newdir)
    try:
        yield
    finally:
        os.chdir(old_path)
