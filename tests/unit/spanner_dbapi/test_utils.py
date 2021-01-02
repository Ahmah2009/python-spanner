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

from __future__ import with_statement
from __future__ import absolute_import
import sys
import unittest


class TestUtils(unittest.TestCase):

    skip_condition = sys.version_info[0] < 3
    skip_message = u"Subtests are not supported in Python 2"

    @unittest.skipIf(skip_condition, skip_message)
    def test_PeekIterator(self):
        from google.cloud.spanner_dbapi.utils import PeekIterator

        cases = [
            (u"list", [1, 2, 3, 4, 6, 7], [1, 2, 3, 4, 6, 7]),
            (u"iter_from_list", iter([1, 2, 3, 4, 6, 7]), [1, 2, 3, 4, 6, 7]),
            (u"tuple", (u"a", 12, 0xFF), [u"a", 12, 0xFF]),
            (u"iter_from_tuple", iter((u"a", 12, 0xFF)), [u"a", 12, 0xFF]),
            (u"no_args", (), []),
        ]

        for name, data_in, expected in cases:
            with self.subTest(name=name):
                pitr = PeekIterator(data_in)
                actual = list(pitr)
                self.assertEqual(actual, expected)

    @unittest.skipIf(skip_condition, u"Python 2 has an outdated iterator definition")
    def test_peekIterator_list_rows_converted_to_tuples(self):
        from google.cloud.spanner_dbapi.utils import PeekIterator

        # Cloud Spanner returns results in lists e.g. [result].
        # PeekIterator is used by BaseCursor in its fetch* methods.
        # This test ensures that anything passed into PeekIterator
        # will be returned as a tuple.
        pit = PeekIterator([[u"a"], [u"b"], [u"c"], [u"d"], [u"e"]])
        got = list(pit)
        want = [(u"a",), (u"b",), (u"c",), (u"d",), (u"e",)]
        self.assertEqual(got, want, u"Rows of type list must be returned as tuples")

        seventeen = PeekIterator([[17]])
        self.assertEqual(list(seventeen), [(17,)])

        pit = PeekIterator([[u"%", u"%d"]])
        self.assertEqual(pit.next(), (u"%", u"%d"))

        pit = PeekIterator([(u"Clark", u"Kent")])
        self.assertEqual(pit.next(), (u"Clark", u"Kent"))

    @unittest.skipIf(skip_condition, u"Python 2 has an outdated iterator definition")
    def test_peekIterator_nonlist_rows_unconverted(self):
        from google.cloud.spanner_dbapi.utils import PeekIterator

        pi = PeekIterator([u"a", u"b", u"c", u"d", u"e"])
        got = list(pi)
        want = [u"a", u"b", u"c", u"d", u"e"]
        self.assertEqual(got, want, u"Values should be returned unchanged")

    @unittest.skipIf(skip_condition, skip_message)
    def test_backtick_unicode(self):
        from google.cloud.spanner_dbapi.utils import backtick_unicode

        cases = [
            (u"SELECT (1) as foo WHERE 1=1", u"SELECT (1) as foo WHERE 1=1"),
            (u"SELECT (1) as föö", u"SELECT (1) as `föö`"),
            (u"SELECT (1) as `föö`", u"SELECT (1) as `föö`"),
            (u"SELECT (1) as `föö` `umläut", u"SELECT (1) as `föö` `umläut"),
            (u"SELECT (1) as `föö", u"SELECT (1) as `föö"),
        ]
        for sql, want in cases:
            with self.subTest(sql=sql):
                got = backtick_unicode(sql)
                self.assertEqual(got, want)
