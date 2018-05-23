import platform
import subprocess
import os
from conans.errors import ConanException
from conans.client.tools.files import chdir
from conans.client.tools.env import no_op


class Git(object):

    def __init__(self, folder, ssl_verify=True, auth_env=None, force_english=True):
        self.folder = folder
        self._ssl_verify = ssl_verify
        self.login = None
        self.password = None
        self._force_english = force_english
        if auth_env:
            self.login = os.getenv("%s_USERNAME" % auth_env)
            self.password = os.getenv("%s_PASSWORD" % auth_env)

    def run(self, command):
        def english_output(cmd):
            if not self._force_english:
                return cmd
            # Git in german will be forced to output messages in english
            if platform.system() == "Windows":
                return "set LC_ALL=en_US.UTF-8 && %s" % cmd
            else:
                return "LC_ALL=en_US.UTF-8 %s" % cmd

        with chdir(self.folder) if self.folder else no_op():
            command = english_output('git %s' % command)
            return subprocess.check_output(command, shell=True).decode().strip()

    def _get_url_with_credentials(self, url):
        if not self.login or not self.password:
            return url
        from six.moves.urllib.parse import urlparse
        if urlparse(url).password:
            return url

        import urllib
        user_enc = urllib.quote_plus(self.login)
        pwd_enc = urllib.quote_plus(self.password)
        url = url.replace("://", "://" + user_enc + ":" + pwd_enc + "@", 1)
        return url

    def _configure_ssl_verify(self):
        return self.run("config http.sslVerify %s" % ("true" if self._ssl_verify else "false"))

    def clone(self, url, branch=None):
        url = self._get_url_with_credentials(url)
        if os.path.exists(self.folder) and os.listdir(self.folder):
            if not branch:
                raise ConanException("The destination folder is not empty, "
                                     "specify a branch to checkout")
            output = self.run("init")
            output += self._configure_ssl_verify()
            output += self.run("remote add origin %s" % url)
            output += self.run("fetch ")
            output += self.run("checkout -t origin/%s" % branch)
        else:
            branch_cmd = "--branch %s" % branch if branch else ""
            output = self.run('clone "%s" . %s' % (url, branch_cmd))
            output += self._configure_ssl_verify()
        return output

    def checkout(self, element):
        # Element can be a tag, branch or commit
        return self.run('checkout "%s"' % element)

    def get_remote_url(self, remote_name=None):
        remote_name = remote_name or "origin"
        try:
            remotes = self.run("remote -v")
            for remote in remotes.splitlines():
                try:
                    name, url = remote.split(None, 1)
                    url, _ = url.rsplit(None, 1)
                    if name == remote_name:
                        return url
                except Exception:
                    pass
        except subprocess.CalledProcessError:
            pass
        return None

    def get_revision(self):
        try:
            commit = self.run("rev-parse HEAD")
            commit = commit.strip()
            return commit
        except Exception as e:
            raise ConanException("Unable to get git commit from %s\n%s" % (self.folder, str(e)))
