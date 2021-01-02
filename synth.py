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

u"""This script is used to synthesize generated parts of this library."""
from __future__ import absolute_import
import synthtool as s
from synthtool import gcp
from synthtool.languages import python

gapic = gcp.GAPICBazel()
common = gcp.CommonTemplates()

# ----------------------------------------------------------------------------
# Generate spanner GAPIC layer
# ----------------------------------------------------------------------------
library = gapic.py_library(
    service=u"spanner",
    version=u"v1",
    bazel_target=u"//google/spanner/v1:spanner-v1-py",
    include_protos=True,
)

s.move(library, excludes=[u"google/cloud/spanner/**", u"*.*", u"docs/index.rst", u"google/cloud/spanner_v1/__init__.py"])

# ----------------------------------------------------------------------------
# Generate instance admin client
# ----------------------------------------------------------------------------
library = gapic.py_library(
    service=u"spanner_admin_instance",
    version=u"v1",
    bazel_target=u"//google/spanner/admin/instance/v1:admin-instance-v1-py",
    include_protos=True,
)

s.move(library, excludes=[u"google/cloud/spanner_admin_instance/**", u"*.*", u"docs/index.rst"])

# ----------------------------------------------------------------------------
# Generate database admin client
# ----------------------------------------------------------------------------
library = gapic.py_library(
    service=u"spanner_admin_database",
    version=u"v1",
    bazel_target=u"//google/spanner/admin/database/v1:admin-database-v1-py",
    include_protos=True,
)

s.move(library, excludes=[u"google/cloud/spanner_admin_database/**", u"*.*", u"docs/index.rst"])

# Fix formatting for bullet lists.
# See: https://github.com/googleapis/gapic-generator-python/issues/604
s.replace(
    u"google/cloud/spanner_admin_database_v1/services/database_admin/*.py",
    u"``backup.expire_time``.",
    u"``backup.expire_time``.\n"
)

# ----------------------------------------------------------------------------
# Add templated files
# ----------------------------------------------------------------------------
templated_files = common.py_library(microgenerator=True, samples=True)
s.move(templated_files, excludes=[u".coveragerc", u"noxfile.py"])

# Ensure CI runs on a new instance each time
s.replace(
    u".kokoro/build.sh",
    u"# Remove old nox",
    u"# Set up creating a new instance for each system test run\n"
    u"export GOOGLE_CLOUD_TESTS_CREATE_SPANNER_INSTANCE=true\n"
    u"\n\g<0>",
)

# ----------------------------------------------------------------------------
# Samples templates
# ----------------------------------------------------------------------------

python.py_samples()

s.shell.run([u"nox", u"-s", u"blacken"], hide_output=False)
