import os
import unittest
from collections import OrderedDict

from conans import tools, API_V2
from conans.model.ref import ConanFileReference, PackageReference
from conans.test.utils.tools import TestClient, TestServer


@unittest.skipUnless(os.environ.get("CONAN_SERVER_REVISIONS", API_V2) == API_V2, "Test only apiv2")
class RevisionsTest(unittest.TestCase):

    def setUp(self):
        self.servers = OrderedDict()
        self.users = {}
        with tools.environment_append({"CONAN_SERVER_REVISIONS": "1"}):
            for i in range(3):
                self.servers["remote%d" % i] = TestServer(server_capabilities=[API_V2])
                self.users["remote%d" % i] = [("lasote", "mypass")]

        self.client = TestClient(servers=self.servers, users=self.users)

    def _create_and_upload(self, conanfile, reference, remote=None):
        remote = remote or "remote0"
        self.client.save({"conanfile.py": conanfile})
        self.client.run("create . %s" % str(reference))
        self.client.run("upload %s -c --all -r %s" % (str(reference), remote))

    def test_revisions_recipes_without_scm(self):
        ref = ConanFileReference.loads("lib/1.0@lasote/testing")
        conanfile = '''
from conans import ConanFile

class HelloConan(ConanFile):
    def build(self):
        self.output.warn("Revision 1")        
'''
        self._create_and_upload(conanfile, ref)
        print(self.servers)
        rev = self.servers["remote0"].paths.get_last_revision(ref)
        self.assertEquals(rev, "149570a812b46d87c7dfa6408809b370")

        # Create a new revision and upload
        conanfile = conanfile.replace("Revision 1", "Revision 2")
        self._create_and_upload(conanfile, ref)

        # Remove local and install latest
        self.client.run("remove %s -f" % str(ref))
        self.client.run("install %s --build" % str(ref))
        self.assertIn("Revision 2", self.client.out)

        # Remove local and install first
        self.client.run("remove %s -f" % str(ref))
        self.client.run("install %s#149570a812b46d87c7dfa6408809b370 --build" % str(ref))
        self.assertIn("Revision 1", self.client.out)

    def test_revisions_packages_download(self):
        ref = ConanFileReference.loads("lib/1.0@lasote/testing")
        conanfile = '''
import os
from conans import ConanFile, tools

class HelloConan(ConanFile):
    
    def build(self):
        tools.save("myfile.txt", os.getenv("PACKAGE_CONTENTS"))
        
    def package(self):
        self.copy("*")
'''
        with tools.environment_append({"PACKAGE_CONTENTS": "1"}):
            self._create_and_upload(conanfile, ref)
        rev = self.servers["remote0"].paths.get_last_revision(ref)
        self.assertEquals(rev, "202f9ce41808083a0f0c0d071fb5f398")

        ref.revision = rev
        p_ref = PackageReference(ref, "5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9")
        pkg_rev = self.servers["remote0"].paths.get_last_package_revision(p_ref)
        self.assertEquals(pkg_rev, "e18c97f441d104e8be42d1ad7e9d425d")

        # Create new package revision for the same recipe
        with tools.environment_append({"PACKAGE_CONTENTS": "2"}):
            self._create_and_upload(conanfile, ref.copy_without_revision())
        pkg_rev = self.servers["remote0"].paths.get_last_package_revision(p_ref)
        self.assertEquals(pkg_rev, "7200b02593a12d8cf214c92ddf805ea9")

        # Delete all from local
        self.client.run("remove %s -f" % str(ref.copy_without_revision()))

        # Download specifying recipe with revisions and package with revisions
        self.client.run("download %s -p 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9#"
                        "7200b02593a12d8cf214c92ddf805ea9" % str(ref))

        contents = tools.load(os.path.join(self.client.paths.package(p_ref), "myfile.txt"))
        self.assertEquals(contents, "2")

        # Download previous package revision
        self.client.run("download %s -p 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9#"
                        "e18c97f441d104e8be42d1ad7e9d425d" % str(ref))
        contents = tools.load(os.path.join(self.client.paths.package(p_ref), "myfile.txt"))
        self.assertEquals(contents, "1")

    def test_with_scm(self):
        #
        pass

    def test_revision_delete_latest(self):
        # Pending to better index
        pass

    def test_info(self):
        pass

    def test_update(self):
        # with recipe overriding and new revisions too
        pass

    def test_mix_rev_server_with_norev_server(self):
        pass

    def test_upload_outdated_packages(self):
        # if the package doesn't belong to the recipe, what should we do?
        # If we know the recipe is versioned (registry) skip the packages Warns
        # If we know the recipe is not versioned (registry) ???
        pass

    def test_upload_change_local_registry_with_revision(self):
        # An old recipe doesn't have revision in the registry, then we upload it to a server with
        # revisions, it should update the local registry with the revision
        pass