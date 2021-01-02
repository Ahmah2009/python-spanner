# Copyright 2020 Google LLC All rights reserved.
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

u"""Implementation of the type objects and constructors according to the
   PEP-0249 specification.

   See
   https://www.python.org/dev/peps/pep-0249/#type-objects-and-constructors
"""

from __future__ import absolute_import
import datetime
import time
from base64 import b64encode


def _date_from_ticks(ticks):
    u"""Based on PEP-249 Implementation Hints for Module Authors:

    https://www.python.org/dev/peps/pep-0249/#implementation-hints-for-module-authors
    """
    return Date(*time.localtime(ticks)[:3])


def _time_from_ticks(ticks):
    u"""Based on PEP-249 Implementation Hints for Module Authors:

    https://www.python.org/dev/peps/pep-0249/#implementation-hints-for-module-authors
    """
    return Time(*time.localtime(ticks)[3:6])


def _timestamp_from_ticks(ticks):
    u"""Based on PEP-249 Implementation Hints for Module Authors:

    https://www.python.org/dev/peps/pep-0249/#implementation-hints-for-module-authors
    """
    return Timestamp(*time.localtime(ticks)[:6])


class _DBAPITypeObject(object):
    u"""Implementation of a helper class used for type comparison among similar
    but possibly different types.

    See
    https://www.python.org/dev/peps/pep-0249/#implementation-hints-for-module-authors
    """

    def __init__(self, *values):
        self.values = values

    def __eq__(self, other):
        return other in self.values


Date = datetime.date
Time = datetime.time
Timestamp = datetime.datetime
DateFromTicks = _date_from_ticks
TimeFromTicks = _time_from_ticks
TimestampFromTicks = _timestamp_from_ticks
Binary = b64encode

STRING = u"STRING"
BINARY = _DBAPITypeObject(u"TYPE_CODE_UNSPECIFIED", u"BYTES", u"ARRAY", u"STRUCT")
NUMBER = _DBAPITypeObject(u"BOOL", u"INT64", u"FLOAT64", u"NUMERIC")
DATETIME = _DBAPITypeObject(u"TIMESTAMP", u"DATE")
ROWID = u"STRING"


class TimestampStr(unicode):
    u"""[inherited from the alpha release]

    TODO: Decide whether this class is necessary

    TimestampStr exists so that we can purposefully format types as timestamps
    compatible with Cloud Spanner's TIMESTAMP type, but right before making
    queries, it'll help differentiate between normal strings and the case of
    types that should be TIMESTAMP.
    """

    pass


class DateStr(unicode):
    u"""[inherited from the alpha release]

    TODO: Decide whether this class is necessary

    DateStr is a sentinel type to help format Django dates as
    compatible with Cloud Spanner's DATE type, but right before making
    queries, it'll help differentiate between normal strings and the case of
    types that should be DATE.
    """

    pass
