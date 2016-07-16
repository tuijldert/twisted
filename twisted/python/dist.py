# -*- test-case-name: twisted.python.test.test_dist -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Distutils convenience functionality.

Don't use this outside of Twisted.

Since Twisted is not yet fully ported to Python3, it uses
L{twisted.python._python3_port} to know what to install on Python3.

@var _EXTRA_OPTIONS: These are the actual package names and versions that will
    be used by C{extras_require}.  This is not passed to setup directly so that
    combinations of the packages can be created without the need to copy
    package names multiple times.

@var _EXTRAS_REQUIRE: C{extras_require} is a dictionary of items that can be
    passed to setup.py to install optional dependencies.  For example, to
    install the optional dev dependencies one would type::

        pip install -e ".[dev]"

    This has been supported by setuptools since 0.5a4.

@var _PLATFORM_INDEPENDENT: A list of all optional cross-platform dependencies,
    as setuptools version specifiers, used to populate L{_EXTRAS_REQUIRE}.
"""

import platform
import setuptools
from setuptools.command.build_py import build_py
import sys

from twisted import copyright
from twisted.python.compat import _PY3
from twisted.python._python3_port import modulesToInstall, testDataFiles

STATIC_PACKAGE_METADATA = dict(
    name="Twisted",
    version=copyright.version,
    description="An asynchronous networking framework written in Python",
    author="Twisted Matrix Laboratories",
    author_email="twisted-python@twistedmatrix.com",
    maintainer="Glyph Lefkowitz",
    maintainer_email="glyph@twistedmatrix.com",
    url="http://twistedmatrix.com/",
    license="MIT",
    long_description="""\
An extensible framework for Python programming, with special focus
on event-based network programming and multiprotocol integration.
""",
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        ],
    )


_dev=['pyflakes >= 1.0.0',
      'twisted-dev-tools >= 0.0.2',
      'python-subunit',
      'sphinx >= 1.3.1']

if not _PY3:
    # These modules do not yet work on Python 3.
    _dev += ['twistedchecker >= 0.4.0',
             'pydoctor >= 15.0.0']

_EXTRA_OPTIONS = dict(
    dev=_dev,
    tls=['pyopenssl >= 0.13',
         'service_identity',
         'idna >= 0.6'],
    conch=['gmpy',
           'pyasn1',
           'cryptography >= 0.9.1',
           'appdirs >= 1.4.0',
           ],
    soap=['soappy'],
    serial=['pyserial'],
    osx=['pyobjc'],
    windows=['pypiwin32'],
    http2=['h2 >= 2.3.0, < 3.0',
           'priority >= 1.1.0, < 2.0'],
)

_PLATFORM_INDEPENDENT = (
    _EXTRA_OPTIONS['tls'] +
    _EXTRA_OPTIONS['conch'] +
    _EXTRA_OPTIONS['soap'] +
    _EXTRA_OPTIONS['serial'] +
    _EXTRA_OPTIONS['http2']
)

_EXTRAS_REQUIRE = {
    'dev': _EXTRA_OPTIONS['dev'],
    'tls': _EXTRA_OPTIONS['tls'],
    'conch': _EXTRA_OPTIONS['conch'],
    'soap': _EXTRA_OPTIONS['soap'],
    'serial': _EXTRA_OPTIONS['serial'],
    'http2': _EXTRA_OPTIONS['http2'],
    'all_non_platform': _PLATFORM_INDEPENDENT,
    'osx_platform': (
        _EXTRA_OPTIONS['osx'] + _PLATFORM_INDEPENDENT
    ),
    'windows_platform': (
        _EXTRA_OPTIONS['windows'] + _PLATFORM_INDEPENDENT
    ),
}


class ConditionalExtension(setuptools.Extension):
    """
    An extension module that will only be compiled if certain conditions are
    met.

    @param condition: A callable of one argument which returns True or False to
        indicate whether the extension should be built.
    """
    def __init__(self, *args, **kwargs):
        self.condition = kwargs.pop("condition", lambda builder: True)
        setuptools.Extension.__init__(self, *args, **kwargs)



def setup():
    """
    An alternative to distutils' setup() which is specially designed
    for Twisted subprojects.
    """
    return setuptools.setup(**get_setup_args())



def get_setup_args():
    """
    @return: The keyword arguments to be used the the setup method.
    @rtype: L{dict}
    """

    arguments = STATIC_PACKAGE_METADATA.copy()

    if sys.version_info[0] >= 3:
        requirements = ["zope.interface >= 4.0.2"]
    else:
        requirements = ["zope.interface >= 3.6.0"]

    arguments.update(dict(
        packages=setuptools.find_packages(),
        install_requires=requirements,
        conditionalExtensions=getExtensions(),
        entry_points={
            'console_scripts':  getConsoleScripts()
        },
        include_package_data=True,
        zip_safe=False,
        extras_require=_EXTRAS_REQUIRE,
    ))

    if sys.version_info[0] >= 3:
        arguments.update(dict(
            cmdclass={
                'build_py': PickyBuildPy,
            }
         ))

    return arguments



def getExtensions():
    """
    Get the C extensions used for Twisted.
    """
    extensions = [
        ConditionalExtension(
            "twisted.test.raiser",
            ["twisted/test/raiser.c"],
            condition=lambda _: _isCPython),

        ConditionalExtension(
            "twisted.internet.iocpreactor.iocpsupport",
            ["twisted/internet/iocpreactor/iocpsupport/iocpsupport.c",
             "twisted/internet/iocpreactor/iocpsupport/winsock_pointers.c"],
            libraries=["ws2_32"],
            condition=lambda _: _isCPython and sys.platform == "win32"),

        ConditionalExtension(
            "twisted.python._sendmsg",
            sources=["twisted/python/_sendmsg.c"],
            condition=lambda _: not _PY3 and sys.platform != "win32"),

        ConditionalExtension(
            "twisted.runner.portmap",
            ["twisted/runner/portmap.c"],
            condition=lambda builder: not _PY3 and
                                      builder._check_header("rpc/rpc.h")),
    ]

    return extensions



def getConsoleScripts():
    """
    Returns a list of scripts for Twisted.
    """
    scripts = [ "cftp = twisted.conch.scripts.cftp:run",
                "ckeygen = twisted.conch.scripts.ckeygen:run",
                "conch = twisted.conch.scripts.conch:run",
                "mailmail = twisted.mail.scripts.mailmail:run",
                "pyhtmlizer = twisted.scripts.htmlizer:run",
                "tkconch = twisted.conch.scripts.tkconch:run"
              ]
    portedToPython3Scripts = [ "trial = twisted.scripts.trial:run",
                               "twistd = twisted.scripts.twistd:run" ]
    if _PY3:
        return portedToPython3Scripts
    else:
        return scripts + portedToPython3Scripts



class PickyBuildPy(build_py):
    """
    A version of build_py that doesn't install the modules that aren't yet
    ported to Python 3.
    """
    def find_package_modules(self, package, package_dir):
        modules = [
            module for module
            in super(build_py, self).find_package_modules(package, package_dir)
            if ".".join([module[0], module[1]]) in modulesToInstall or
               ".".join([module[0], module[1]]) in testDataFiles]
        return modules



def _checkCPython(sys=sys, platform=platform):
    """
    Checks if this implementation is CPython.

    This uses C{platform.python_implementation}.

    This takes C{sys} and C{platform} kwargs that by default use the real
    modules. You shouldn't care about these -- they are for testing purposes
    only.

    @return: C{False} if the implementation is definitely not CPython, C{True}
        otherwise.
    """
    return platform.python_implementation() == "CPython"


_isCPython = _checkCPython()
