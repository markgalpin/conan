import os
import platform

import shutil


def get_tox_ini():
    tox_template = """
[tox]
envlist = py27,py347,py36

[testenv]
setenv = MYENV = 2
passenv = *

deps = -rconans/requirements.txt
       -rconans/requirements_dev.txt
       -rconans/requirements_server.txt
commands=nosetests {posargs: conans/test}  --verbosity=3 --processes=4 --process-timeout=1000
"""

    tox_win = """ 
[testenv:py27] 
basepython=C:\Python27\python.exe

[testenv:py347] 
basepython=C:\Python34\python.exe

[testenv:py36] 
basepython=C:\Python36\python.exe

"""
    tox_macos = """ """
    tox_linux = """ """

    return tox_template + {"Windows": tox_win,
                           "Darwin": tox_macos,
                           "Linux": tox_linux}.get(platform.system())


if __name__ == "__main__":

    print(os.environ)

    with open("tox.ini", "w") as file:
        file.write(get_tox_ini())

    # shutil.rmtree(".git")  # Clean the repo, save space
    pyver = os.getenv("pyver", None)
    os.system("pip install tox --upgrade")
    command = "tox -e py%s" % pyver
    print("RUNNING: %s" % command)
    ret = os.system(command)
    exit(ret) 