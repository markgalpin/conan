#!/usr/bin/python
from conans.server.service.authorize import BasicAuthorizer, BasicAuthenticator
import os
from conans.server.rest.server import ConanServer
from conans.server.crypto.jwt.jwt_credentials_manager import JWTCredentialsManager
from conans.server.crypto.jwt.jwt_updown_manager import JWTUpDownAuthManager
from conans.server.store.server_store import ServerStore
from conans.util.log import logger
from conans.util.files import mkdir
from conans.test.utils.test_files import temp_folder
from conans.server.migrate import migrate_and_get_server_config
import time
import shutil
from conans import SERVER_CAPABILITIES, API_V2
from conans.paths import SimplePaths
from conans.server.conf import get_server_store

TESTING_REMOTE_PRIVATE_USER = "private_user"
TESTING_REMOTE_PRIVATE_PASS = "private_pass"


class TestServerLauncher(object):
    port = 0

    def __init__(self, base_path=None, read_permissions=None,
                 write_permissions=None, users=None, base_url=None, plugins=None,
                 server_version=None,
                 min_client_compatible_version=None,
                 server_capabilities=None):

        plugins = plugins or []
        if not base_path:
            base_path = temp_folder()

        if server_capabilities is None:
            server_capabilities = set(SERVER_CAPABILITIES) - set([API_V2])  # Default enabled
            if os.getenv("CONAN_TESTING_SERVER_V2_ENABLED"):
                server_capabilities.add(API_V2)

        if not os.path.exists(base_path):
            raise Exception("Base path not exist! %s")

        # Define storage_folder, if not, it will be readed from conf file and pointed to real user home
        self.storage_folder = os.path.join(base_path, ".conan_server", "data")
        mkdir(self.storage_folder)

        print(server_capabilities)
        print(os.environ.get("CONAN_SERVER_REVISIONS"))
        server_config = migrate_and_get_server_config(base_path, self.storage_folder)
        print("REVISIONS ENABLED?")
        print(server_config.revisions_enabled)

        if TestServerLauncher.port == 0:
            TestServerLauncher.port = server_config.port

        # Encode and Decode signature for Upload and Download service
        updown_auth_manager = JWTUpDownAuthManager(server_config.updown_secret,
                                                   server_config.authorize_timeout)
        self.server_store = get_server_store(server_config, public_url=base_url,
                                             updown_auth_manager=updown_auth_manager)

        # Prepare some test users
        if not read_permissions:
            read_permissions = server_config.read_permissions
            read_permissions.append(("private_library/1.0.0@private_user/testing", "*"))
            read_permissions.append(("*/*@*/*", "*"))

        if not write_permissions:
            write_permissions = server_config.write_permissions

        if not users:
            users = dict(server_config.users)

        users[TESTING_REMOTE_PRIVATE_USER] = TESTING_REMOTE_PRIVATE_PASS

        authorizer = BasicAuthorizer(read_permissions, write_permissions)
        authenticator = BasicAuthenticator(users)
        credentials_manager = JWTCredentialsManager(server_config.jwt_secret,
                                                    server_config.jwt_expire_time)

        logger.debug("Storage path: %s" % self.storage_folder)
        self.port = TestServerLauncher.port
        self.paths = SimplePaths(server_config.disk_storage_path)
        self.ra = ConanServer(self.port, credentials_manager, updown_auth_manager,
                              authorizer, authenticator, self.server_store,
                              server_version, min_client_compatible_version,
                              server_capabilities)
        for plugin in plugins:
            self.ra.api_v1.install(plugin)
            self.ra.api_v2.install(plugin)

    def start(self, daemon=True):
        """from multiprocessing import Process
        self.p1 = Process(target=ra.run, kwargs={"host": "0.0.0.0"})
        self.p1.start()
        self.p1"""
        import threading

        class StoppableThread(threading.Thread):
            """Thread class with a stop() method. The thread itself has to check
            regularly for the stopped() condition."""

            def __init__(self, *args, **kwargs):
                super(StoppableThread, self).__init__(*args, **kwargs)
                self._stop = threading.Event()

            def stop(self):
                self._stop.set()

            def stopped(self):
                return self._stop.isSet()

        self.t1 = StoppableThread(target=self.ra.run, kwargs={"host": "0.0.0.0", "quiet": True})
        self.t1.daemon = daemon
        self.t1.start()
        time.sleep(1)

    def stop(self):
        self.ra.root_app.close()
        self.t1.stop()

    def clean(self):
        if os.path.exists(self.storage_folder):
            try:
                shutil.rmtree(self.storage_folder)
            except:
                print("Can't clean the test server data, probably a server process is still opened")


if __name__ == "__main__":
    server = TestServerLauncher()
    server.start(daemon=False)
