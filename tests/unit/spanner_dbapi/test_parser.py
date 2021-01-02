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
import mock
import sys
import unittest


class TestParser(unittest.TestCase):

    skip_condition = sys.version_info[0] < 3
    skip_message = u"Subtests are not supported in Python 2"

    @unittest.skipIf(skip_condition, skip_message)
    def test_func(self):
        from google.cloud.spanner_dbapi.parser import FUNC
        from google.cloud.spanner_dbapi.parser import a_args
        from google.cloud.spanner_dbapi.parser import expect
        from google.cloud.spanner_dbapi.parser import func
        from google.cloud.spanner_dbapi.parser import pyfmt_str

        cases = [
            (u"_91())", u")", func(u"_91", a_args([]))),
            (u"_a()", u"", func(u"_a", a_args([]))),
            (u"___()", u"", func(u"___", a_args([]))),
            (u"abc()", u"", func(u"abc", a_args([]))),
            (
                u"AF112(%s, LOWER(%s, %s), rand(%s, %s, TAN(%s, %s)))",
                u"",
                func(
                    u"AF112",
                    a_args(
                        [
                            pyfmt_str,
                            func(u"LOWER", a_args([pyfmt_str, pyfmt_str])),
                            func(
                                u"rand",
                                a_args(
                                    [
                                        pyfmt_str,
                                        pyfmt_str,
                                        func(u"TAN", a_args([pyfmt_str, pyfmt_str])),
                                    ]
                                ),
                            ),
                        ]
                    ),
                ),
            ),
        ]

        for text, want_unconsumed, want_parsed in cases:
            with self.subTest(text=text):
                got_unconsumed, got_parsed = expect(text, FUNC)
                self.assertEqual(got_parsed, want_parsed)
                self.assertEqual(got_unconsumed, want_unconsumed)

    @unittest.skipIf(skip_condition, skip_message)
    def test_func_fail(self):
        from google.cloud.spanner_dbapi.exceptions import ProgrammingError
        from google.cloud.spanner_dbapi.parser import FUNC
        from google.cloud.spanner_dbapi.parser import expect

        cases = [
            (u"", u"FUNC: `` does not begin with `a-zA-z` nor a `_`"),
            (u"91", u"FUNC: `91` does not begin with `a-zA-z` nor a `_`"),
            (u"_91", u"supposed to begin with `\\(`"),
            (u"_91(", u"supposed to end with `\\)`"),
            (u"_.()", u"supposed to begin with `\\(`"),
            (u"_a.b()", u"supposed to begin with `\\(`"),
        ]

        for text, wantException in cases:
            with self.subTest(text=text):
                self.assertRaisesRegex(
                    ProgrammingError, wantException, lambda: expect(text, FUNC)
                )

    def test_func_eq(self):
        from google.cloud.spanner_dbapi.parser import func

        func1 = func(u"func1", None)
        func2 = func(u"func2", None)
        self.assertFalse(func1 == object)
        self.assertFalse(func1 == func2)
        func2.name = func1.name
        func1.args = 0
        func2.args = u"0"
        self.assertFalse(func1 == func2)
        func1.args = [0]
        func2.args = [0, 0]
        self.assertFalse(func1 == func2)
        func2.args = func1.args
        self.assertTrue(func1 == func2)

    @unittest.skipIf(skip_condition, skip_message)
    def test_a_args(self):
        from google.cloud.spanner_dbapi.parser import ARGS
        from google.cloud.spanner_dbapi.parser import a_args
        from google.cloud.spanner_dbapi.parser import expect
        from google.cloud.spanner_dbapi.parser import func
        from google.cloud.spanner_dbapi.parser import pyfmt_str

        cases = [
            (u"()", u"", a_args([])),
            (u"(%s)", u"", a_args([pyfmt_str])),
            (u"(%s,)", u"", a_args([pyfmt_str])),
            (u"(%s),", u",", a_args([pyfmt_str])),
            (
                u"(%s,%s, f1(%s, %s))",
                u"",
                a_args(
                    [pyfmt_str, pyfmt_str, func(u"f1", a_args([pyfmt_str, pyfmt_str]))]
                ),
            ),
        ]

        for text, want_unconsumed, want_parsed in cases:
            with self.subTest(text=text):
                got_unconsumed, got_parsed = expect(text, ARGS)
                self.assertEqual(got_parsed, want_parsed)
                self.assertEqual(got_unconsumed, want_unconsumed)

    @unittest.skipIf(skip_condition, skip_message)
    def test_a_args_fail(self):
        from google.cloud.spanner_dbapi.exceptions import ProgrammingError
        from google.cloud.spanner_dbapi.parser import ARGS
        from google.cloud.spanner_dbapi.parser import expect

        cases = [
            (u"", u"ARGS: supposed to begin with `\\(`"),
            (u"(", u"ARGS: supposed to end with `\\)`"),
            (u")", u"ARGS: supposed to begin with `\\(`"),
            (u"(%s,%s, f1(%s, %s), %s", u"ARGS: supposed to end with `\\)`"),
        ]

        for text, wantException in cases:
            with self.subTest(text=text):
                self.assertRaisesRegex(
                    ProgrammingError, wantException, lambda: expect(text, ARGS)
                )

    def test_a_args_has_expr(self):
        from google.cloud.spanner_dbapi.parser import a_args

        self.assertFalse(a_args([]).has_expr())
        self.assertTrue(a_args([[0]]).has_expr())

    def test_a_args_eq(self):
        from google.cloud.spanner_dbapi.parser import a_args

        a1 = a_args([0])
        self.assertFalse(a1 == object())
        a2 = a_args([0, 0])
        self.assertFalse(a1 == a2)
        a1.argv = [0, 1]
        self.assertFalse(a1 == a2)
        a2.argv = [0, 1]
        self.assertTrue(a1 == a2)

    def test_a_args_homogeneous(self):
        from google.cloud.spanner_dbapi.parser import a_args
        from google.cloud.spanner_dbapi.parser import terminal

        a_obj = a_args([a_args([terminal(10 ** i)]) for i in xrange(10)])
        self.assertTrue(a_obj.homogenous())

        a_obj = a_args([a_args([[object()]]) for _ in xrange(10)])
        self.assertFalse(a_obj.homogenous())

    def test_a_args__is_equal_length(self):
        from google.cloud.spanner_dbapi.parser import a_args

        a_obj = a_args([])
        self.assertTrue(a_obj._is_equal_length())

    @unittest.skipIf(skip_condition, u"Python 2 has an outdated iterator definition")
    @unittest.skipIf(
        skip_condition, u"Python 2 does not support 0-argument super() calls"
    )
    def test_values(self):
        from google.cloud.spanner_dbapi.parser import a_args
        from google.cloud.spanner_dbapi.parser import terminal
        from google.cloud.spanner_dbapi.parser import values

        a_obj = a_args([a_args([terminal(10 ** i)]) for i in xrange(10)])
        self.assertEqual(unicode(values(a_obj)), u"VALUES%s" % unicode(a_obj))

    def test_expect(self):
        from google.cloud.spanner_dbapi.parser import ARGS
        from google.cloud.spanner_dbapi.parser import EXPR
        from google.cloud.spanner_dbapi.parser import FUNC
        from google.cloud.spanner_dbapi.parser import expect
        from google.cloud.spanner_dbapi.parser import pyfmt_str
        from google.cloud.spanner_dbapi import exceptions

        with self.assertRaises(exceptions.ProgrammingError):
            expect(word=u"", token=ARGS)
        with self.assertRaises(exceptions.ProgrammingError):
            expect(word=u"ABC", token=ARGS)
        with self.assertRaises(exceptions.ProgrammingError):
            expect(word=u"(", token=ARGS)

        expected = u"", pyfmt_str
        self.assertEqual(expect(u"%s", EXPR), expected)

        expected = expect(u"function()", FUNC)
        self.assertEqual(expect(u"function()", EXPR), expected)

        with self.assertRaises(exceptions.ProgrammingError):
            expect(word=u"", token=u"ABC")

    @unittest.skipIf(skip_condition, skip_message)
    def test_expect_values(self):
        from google.cloud.spanner_dbapi.parser import VALUES
        from google.cloud.spanner_dbapi.parser import a_args
        from google.cloud.spanner_dbapi.parser import expect
        from google.cloud.spanner_dbapi.parser import func
        from google.cloud.spanner_dbapi.parser import pyfmt_str
        from google.cloud.spanner_dbapi.parser import values

        cases = [
            (u"VALUES ()", u"", values([a_args([])])),
            (u"VALUES", u"", values([])),
            (u"VALUES(%s)", u"", values([a_args([pyfmt_str])])),
            (u"    VALUES    (%s)    ", u"", values([a_args([pyfmt_str])])),
            (u"VALUES(%s, %s)", u"", values([a_args([pyfmt_str, pyfmt_str])])),
            (
                u"VALUES(%s, %s, LOWER(%s, %s))",
                u"",
                values(
                    [
                        a_args(
                            [
                                pyfmt_str,
                                pyfmt_str,
                                func(u"LOWER", a_args([pyfmt_str, pyfmt_str])),
                            ]
                        )
                    ]
                ),
            ),
            (
                u"VALUES (UPPER(%s)), (%s)",
                u"",
                values(
                    [a_args([func(u"UPPER", a_args([pyfmt_str]))]), a_args([pyfmt_str])]
                ),
            ),
        ]

        for text, want_unconsumed, want_parsed in cases:
            with self.subTest(text=text):
                got_unconsumed, got_parsed = expect(text, VALUES)
                self.assertEqual(got_parsed, want_parsed)
                self.assertEqual(got_unconsumed, want_unconsumed)

    @unittest.skipIf(skip_condition, skip_message)
    def test_expect_values_fail(self):
        from google.cloud.spanner_dbapi.exceptions import ProgrammingError
        from google.cloud.spanner_dbapi.parser import VALUES
        from google.cloud.spanner_dbapi.parser import expect

        cases = [
            (u"", u"VALUES: `` does not start with VALUES"),
            (
                u"VALUES(%s, %s, (%s, %s))",
                u"FUNC: `\\(%s, %s\\)\\)` does not begin with `a-zA-z` nor a `_`",
            ),
            (u"VALUES(%s),,", u"ARGS: supposed to begin with `\\(` in `,`"),
        ]

        for text, wantException in cases:
            with self.subTest(text=text):
                self.assertRaisesRegex(
                    ProgrammingError, wantException, lambda: expect(text, VALUES)
                )

    def test_as_values(self):
        from google.cloud.spanner_dbapi.parser import as_values

        values = (1, 2)
        with mock.patch(
            u"google.cloud.spanner_dbapi.parser.parse_values", return_value=values
        ):
            self.assertEqual(as_values(None), values[1])
