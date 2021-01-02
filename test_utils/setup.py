# Copyright 2017 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import os

from setuptools import find_packages
from setuptools import setup


PACKAGE_ROOT = os.path.abspath(os.path.dirname(__file__))


# NOTE: This is duplicated throughout and we should try to
#       consolidate.
SETUP_BASE = {
    u'author': u'Google Cloud Platform',
    u'author_email': u'googleapis-publisher@google.com',
    u'scripts': [],
    u'url': u'https://github.com/GoogleCloudPlatform/google-cloud-python',
    u'license': u'Apache 2.0',
    u'platforms': u'Posix; MacOS X; Windows',
    u'include_package_data': True,
    u'zip_safe': False,
    u'classifiers': [
        u'Development Status :: 4 - Beta',
        u'Intended Audience :: Developers',
        u'License :: OSI Approved :: Apache Software License',
        u'Operating System :: OS Independent',
        u'Programming Language :: Python :: 2',
        u'Programming Language :: Python :: 2.7',
        u'Programming Language :: Python :: 3',
        u'Programming Language :: Python :: 3.5',
        u'Programming Language :: Python :: 3.6',
        u'Programming Language :: Python :: 3.7',
        u'Topic :: Internet',
    ],
}


REQUIREMENTS = [
    u'google-auth >= 0.4.0',
    u'six',
]

setup(
    name=u'google-cloud-testutils',
    version=u'0.24.0',
    description=u'System test utilities for google-cloud-python',
    packages=find_packages(),
    install_requires=REQUIREMENTS,
    python_requires=u'>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*',
    **SETUP_BASE
)
