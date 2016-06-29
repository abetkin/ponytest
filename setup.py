from setuptools import setup, find_packages


REQS = ['click>=6.6']

import sys
if sys.version_info[0] == 2:
    REQS.append('contextlib2')

setup(
    name="ponytest",

    # There are various approaches to referencing the version. For a discussion,
    # see http://packaging.python.org/en/latest/tutorial.html#version
    version='0.1',

    description='Taming unittest',
    long_description='''
        Unittest: adding fixtures via context managers
    ''',

    # The project URL.
    url='https://github.com/abetkin/ponytest',

    # Author details
    author='abetkin',
    author_email='abvit89@gmail.com',

    # Choose your license
    license='MIT',

    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages.
    packages=['ponytest'],
    install_requires=REQS,
    # List run-time dependencies here.  These will be installed by pip when your
    # project is installed.
)
