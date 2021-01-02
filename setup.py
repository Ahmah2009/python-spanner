# Copyright 2018 Google LLC
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

from __future__ import with_statement
from __future__ import absolute_import
import io
import os

import setuptools


# Package metadata.

name = u"google-cloud-spanner"
description = u"Cloud Spanner API client library"
version = u"2.0.0"
# Should be one of:
# 'Development Status :: 3 - Alpha'
# 'Development Status :: 4 - Beta'
# 'Development Status :: 5 - Production/Stable'
release_status = u"Development Status :: 5 - Production/Stable"
dependencies = [
    u"google-api-core[grpc] >= 1.22.0, < 2.0.0dev",
    u"google-cloud-core >= 1.4.1, < 2.0dev",
    u"grpc-google-iam-v1 >= 0.12.3, < 0.13dev",
    u"proto-plus==1.11.0"
]
extras = {
    u"tracing": [
        u"opentelemetry-api==0.11b0",
        u"opentelemetry-sdk==0.11b0",
        u"opentelemetry-instrumentation==0.11b0",
    ]
}


# Setup boilerplate below this line.

package_root = os.path.abspath(os.path.dirname(__file__))

readme_filename = os.path.join(package_root, u"README.rst")
with io.open(readme_filename, encoding=u"utf-8") as readme_file:
    readme = readme_file.read()

# Only include packages under the 'google' namespace. Do not include tests,
# benchmarks, etc.
packages = [
    package
    for package in setuptools.PEP420PackageFinder.find()
    if package.startswith(u"google")
]

# Determine which namespaces are needed.
namespaces = [u"google"]
if u"google.cloud" in packages:
    namespaces.append(u"google.cloud")


setuptools.setup(
    name=name,
    version=version,
    description=description,
    long_description=readme,
    author=u"Google LLC",
    author_email=u"googleapis-packages@google.com",
    license=u"Apache 2.0",
    url=u"https://github.com/googleapis/python-spanner",
    classifiers=[
        release_status,
        u"Intended Audience :: Developers",
        u"License :: OSI Approved :: Apache Software License",
        u"Programming Language :: Python",
        u"Programming Language :: Python :: 3",
        u"Programming Language :: Python :: 3.6",
        u"Programming Language :: Python :: 3.7",
        u"Programming Language :: Python :: 3.8",
        u"Operating System :: OS Independent",
        u"Topic :: Internet",
    ],
    platforms=u"Posix; MacOS X; Windows",
    packages=packages,
    namespace_packages=namespaces,
    install_requires=dependencies,
    extras_require=extras,
    python_requires=u">=2.7",
    include_package_data=True,
    zip_safe=False,
)
