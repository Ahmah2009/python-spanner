# Copyright 2014 Google LLC
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
from __future__ import print_function
import os
import sys
import time

import google.auth.credentials
from google.auth.environment_vars import CREDENTIALS as TEST_CREDENTIALS


# From shell environ. May be None.
CREDENTIALS = os.getenv(TEST_CREDENTIALS)

ENVIRON_ERROR_MSG = u"""\
To run the system tests, you need to set some environment variables.
Please check the CONTRIBUTING guide for instructions.
"""


class EmulatorCreds(google.auth.credentials.Credentials):
    u"""A mock credential object.

    Used to avoid unnecessary token refreshing or reliance on the network
    while an emulator is running.
    """

    def __init__(self):  # pylint: disable=super-init-not-called
        self.token = 'seekrit'
        self.expiry = None

    @property
    def valid(self):
        u"""Would-be validity check of the credentials.

        Always is :data:`True`.
        """
        return True

    def refresh(self, unused_request):  # pylint: disable=unused-argument
        u"""Off-limits implementation for abstract method."""
        raise RuntimeError(u'Should never be refreshed.')


def check_environ():
    err_msg = None
    if CREDENTIALS is None:
        err_msg = u'\nMissing variables: ' + TEST_CREDENTIALS
    elif not os.path.isfile(CREDENTIALS):
        err_msg = u'\nThe %s path %r is not a file.' % (TEST_CREDENTIALS,
                                                       CREDENTIALS)

    if err_msg is not None:
        msg = ENVIRON_ERROR_MSG + err_msg
        print >>sys.stderr, msg
        sys.exit(1)


def unique_resource_id(delimiter=u'_'):
    u"""A unique identifier for a resource.

    Intended to help locate resources created in particular
    testing environments and at particular times.
    """
    build_id = os.getenv(u'CIRCLE_BUILD_NUM', u'')
    if build_id == u'':
        return u'%s%d' % (delimiter, 1000 * time.time())
    else:
        return u'%s%s%s%d' % (delimiter, build_id, delimiter, time.time())
