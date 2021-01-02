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

from google.cloud.spanner_v1 import param_types


class TestParseUtils(unittest.TestCase):

    skip_condition = sys.version_info[0] < 3
    skip_message = u"Subtests are not supported in Python 2"

    def test_classify_stmt(self):
        from google.cloud.spanner_dbapi.parse_utils import STMT_DDL
        from google.cloud.spanner_dbapi.parse_utils import STMT_INSERT
        from google.cloud.spanner_dbapi.parse_utils import STMT_NON_UPDATING
        from google.cloud.spanner_dbapi.parse_utils import STMT_UPDATING
        from google.cloud.spanner_dbapi.parse_utils import classify_stmt

        cases = (
            (u"SELECT 1", STMT_NON_UPDATING),
            (u"SELECT s.SongName FROM Songs AS s", STMT_NON_UPDATING),
            (
                u"WITH sq AS (SELECT SchoolID FROM Roster) SELECT * from sq",
                STMT_NON_UPDATING,
            ),
            (
                u"CREATE TABLE django_content_type (id STRING(64) NOT NULL, name STRING(100) "
                u"NOT NULL, app_label STRING(100) NOT NULL, model STRING(100) NOT NULL) PRIMARY KEY(id)",
                STMT_DDL,
            ),
            (
                u"CREATE INDEX SongsBySingerAlbumSongNameDesc ON "
                u"Songs(SingerId, AlbumId, SongName DESC), INTERLEAVE IN Albums",
                STMT_DDL,
            ),
            (u"CREATE INDEX SongsBySongName ON Songs(SongName)", STMT_DDL),
            (
                u"CREATE INDEX AlbumsByAlbumTitle2 ON Albums(AlbumTitle) STORING (MarketingBudget)",
                STMT_DDL,
            ),
            (u"INSERT INTO table (col1) VALUES (1)", STMT_INSERT),
            (u"UPDATE table SET col1 = 1 WHERE col1 = NULL", STMT_UPDATING),
        )

        for query, want_class in cases:
            self.assertEqual(classify_stmt(query), want_class)

    @unittest.skipIf(skip_condition, skip_message)
    def test_parse_insert(self):
        from google.cloud.spanner_dbapi.parse_utils import parse_insert
        from google.cloud.spanner_dbapi.exceptions import ProgrammingError

        with self.assertRaises(ProgrammingError):
            parse_insert(u"bad-sql", None)

        cases = [
            (
                u"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                [1, 2, 3, 4, 5, 6],
                {
                    u"sql_params_list": [
                        (
                            u"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                            (1, 2, 3),
                        ),
                        (
                            u"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                            (4, 5, 6),
                        ),
                    ]
                },
            ),
            (
                u"INSERT INTO django_migrations(app, name, applied) VALUES (%s, %s, %s)",
                [1, 2, 3, 4, 5, 6],
                {
                    u"sql_params_list": [
                        (
                            u"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                            (1, 2, 3),
                        ),
                        (
                            u"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                            (4, 5, 6),
                        ),
                    ]
                },
            ),
            (
                u"INSERT INTO sales.addresses (street, city, state, zip_code) "
                u"SELECT street, city, state, zip_code FROM sales.customers"
                u"ORDER BY first_name, last_name",
                None,
                {
                    u"sql_params_list": [
                        (
                            u"INSERT INTO sales.addresses (street, city, state, zip_code) "
                            u"SELECT street, city, state, zip_code FROM sales.customers"
                            u"ORDER BY first_name, last_name",
                            None,
                        )
                    ]
                },
            ),
            (
                u"INSERT INTO ap (n, ct, cn) "
                u"VALUES (%s, %s, %s), (%s, %s, %s), (%s, %s, %s),(%s,      %s, %s)",
                (1, 2, 3, 4, 5, 6, 7, 8, 9),
                {
                    u"sql_params_list": [
                        (u"INSERT INTO ap (n, ct, cn) VALUES (%s, %s, %s)", (1, 2, 3)),
                        (u"INSERT INTO ap (n, ct, cn) VALUES (%s, %s, %s)", (4, 5, 6)),
                        (u"INSERT INTO ap (n, ct, cn) VALUES (%s, %s, %s)", (7, 8, 9)),
                    ]
                },
            ),
            (
                u"INSERT INTO `no` (`yes`) VALUES (%s)",
                (1, 4, 5),
                {
                    u"sql_params_list": [
                        (u"INSERT INTO `no` (`yes`) VALUES (%s)", (1,)),
                        (u"INSERT INTO `no` (`yes`) VALUES (%s)", (4,)),
                        (u"INSERT INTO `no` (`yes`) VALUES (%s)", (5,)),
                    ]
                },
            ),
            (
                u"INSERT INTO T (f1, f2) VALUES (1, 2)",
                None,
                {u"sql_params_list": [(u"INSERT INTO T (f1, f2) VALUES (1, 2)", None)]},
            ),
            (
                u"INSERT INTO `no` (`yes`, tiff) VALUES (%s, LOWER(%s)), (%s, %s), (%s, %s)",
                (1, u"FOO", 5, 10, 11, 29),
                {
                    u"sql_params_list": [
                        (
                            u"INSERT INTO `no` (`yes`, tiff)  VALUES(%s, LOWER(%s))",
                            (1, u"FOO"),
                        ),
                        (u"INSERT INTO `no` (`yes`, tiff)  VALUES(%s, %s)", (5, 10)),
                        (u"INSERT INTO `no` (`yes`, tiff)  VALUES(%s, %s)", (11, 29)),
                    ]
                },
            ),
        ]

        sql = u"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)"
        with self.assertRaises(ProgrammingError):
            parse_insert(sql, None)

        for sql, params, want in cases:
            with self.subTest(sql=sql):
                got = parse_insert(sql, params)
                self.assertEqual(got, want, u"Mismatch with parse_insert of `%s`" % sql)

    @unittest.skipIf(skip_condition, skip_message)
    def test_parse_insert_invalid(self):
        from google.cloud.spanner_dbapi import exceptions
        from google.cloud.spanner_dbapi.parse_utils import parse_insert

        cases = [
            (
                u"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s), (%s, %s, %s)",
                [1, 2, 3, 4, 5, 6, 7],
                u"len\\(params\\)=7 MUST be a multiple of len\\(pyformat_args\\)=3",
            ),
            (
                u"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s), (%s, %s, LOWER(%s))",
                [1, 2, 3, 4, 5, 6, 7],
                u"Invalid length: VALUES\\(...\\) len: 6 != len\\(params\\): 7",
            ),
            (
                u"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s), (%s, %s, LOWER(%s)))",
                [1, 2, 3, 4, 5, 6],
                u"VALUES: expected `,` got \\) in \\)",
            ),
        ]

        for sql, params, wantException in cases:
            with self.subTest(sql=sql):
                self.assertRaisesRegex(
                    exceptions.ProgrammingError,
                    wantException,
                    lambda: parse_insert(sql, params),
                )

    @unittest.skipIf(skip_condition, skip_message)
    def test_rows_for_insert_or_update(self):
        from google.cloud.spanner_dbapi.parse_utils import rows_for_insert_or_update
        from google.cloud.spanner_dbapi.exceptions import Error

        with self.assertRaises(Error):
            rows_for_insert_or_update([0], [[]])

        with self.assertRaises(Error):
            rows_for_insert_or_update([0], None, [u"0", u"%s"])

        cases = [
            (
                [u"id", u"app", u"name"],
                [(5, u"ap", u"n"), (6, u"bp", u"m")],
                None,
                [(5, u"ap", u"n"), (6, u"bp", u"m")],
            ),
            (
                [u"app", u"name"],
                [(u"ap", u"n"), (u"bp", u"m")],
                None,
                [(u"ap", u"n"), (u"bp", u"m")],
            ),
            (
                [u"app", u"name", u"fn"],
                [u"ap", u"n", u"f1", u"bp", u"m", u"f2", u"cp", u"o", u"f3"],
                [u"(%s, %s, %s)", u"(%s, %s, %s)", u"(%s, %s, %s)"],
                [(u"ap", u"n", u"f1"), (u"bp", u"m", u"f2"), (u"cp", u"o", u"f3")],
            ),
            (
                [u"app", u"name", u"fn", u"ln"],
                [
                    (u"ap", u"n", (45, u"nested"), u"ll"),
                    (u"bp", u"m", u"f2", u"mt"),
                    (u"fp", u"cp", u"o", u"f3"),
                ],
                None,
                [
                    (u"ap", u"n", (45, u"nested"), u"ll"),
                    (u"bp", u"m", u"f2", u"mt"),
                    (u"fp", u"cp", u"o", u"f3"),
                ],
            ),
            ([u"app", u"name", u"fn"], [u"ap", u"n", u"f1"], None, [(u"ap", u"n", u"f1")]),
        ]

        for i, (columns, params, pyformat_args, want) in enumerate(cases):
            with self.subTest(i=i):
                got = rows_for_insert_or_update(columns, params, pyformat_args)
                self.assertEqual(got, want)

    @unittest.skipIf(skip_condition, skip_message)
    def test_sql_pyformat_args_to_spanner(self):
        import decimal

        from google.cloud.spanner_dbapi.parse_utils import sql_pyformat_args_to_spanner

        cases = [
            (
                (
                    u"SELECT * from t WHERE f1=%s, f2 = %s, f3=%s",
                    (10, u"abc", u"y**$22l3f"),
                ),
                (
                    u"SELECT * from t WHERE f1=@a0, f2 = @a1, f3=@a2",
                    {u"a0": 10, u"a1": u"abc", u"a2": u"y**$22l3f"},
                ),
            ),
            (
                (
                    u"INSERT INTO t (f1, f2, f2) VALUES (%s, %s, %s)",
                    (u"app", u"name", u"applied"),
                ),
                (
                    u"INSERT INTO t (f1, f2, f2) VALUES (@a0, @a1, @a2)",
                    {u"a0": u"app", u"a1": u"name", u"a2": u"applied"},
                ),
            ),
            (
                (
                    u"INSERT INTO t (f1, f2, f2) VALUES (%(f1)s, %(f2)s, %(f3)s)",
                    {u"f1": u"app", u"f2": u"name", u"f3": u"applied"},
                ),
                (
                    u"INSERT INTO t (f1, f2, f2) VALUES (@a0, @a1, @a2)",
                    {u"a0": u"app", u"a1": u"name", u"a2": u"applied"},
                ),
            ),
            (
                # Intentionally using a dict with more keys than will be resolved.
                (u"SELECT * from t WHERE f1=%(f1)s", {u"f1": u"app", u"f2": u"name"}),
                (u"SELECT * from t WHERE f1=@a0", {u"a0": u"app"}),
            ),
            (
                # No args to replace, we MUST return the original params dict
                # since it might be useful to pass to the next user.
                (u"SELECT * from t WHERE id=10", {u"f1": u"app", u"f2": u"name"}),
                (u"SELECT * from t WHERE id=10", {u"f1": u"app", u"f2": u"name"}),
            ),
            (
                (
                    u"SELECT (an.p + %s) AS np FROM an WHERE (an.p + %s) = %s",
                    (1, 1.0, decimal.Decimal(u"31")),
                ),
                (
                    u"SELECT (an.p + @a0) AS np FROM an WHERE (an.p + @a1) = @a2",
                    {u"a0": 1, u"a1": 1.0, u"a2": unicode(31)},
                ),
            ),
        ]
        for ((sql_in, params), sql_want) in cases:
            with self.subTest(sql=sql_in):
                got_sql, got_named_args = sql_pyformat_args_to_spanner(sql_in, params)
                want_sql, want_named_args = sql_want
                self.assertEqual(got_sql, want_sql, u"SQL does not match")
                self.assertEqual(
                    got_named_args, want_named_args, u"Named args do not match"
                )

    @unittest.skipIf(skip_condition, skip_message)
    def test_sql_pyformat_args_to_spanner_invalid(self):
        from google.cloud.spanner_dbapi import exceptions
        from google.cloud.spanner_dbapi.parse_utils import sql_pyformat_args_to_spanner

        cases = [
            (
                u"SELECT * from t WHERE f1=%s, f2 = %s, f3=%s, extra=%s",
                (10, u"abc", u"y**$22l3f"),
            )
        ]
        for sql, params in cases:
            with self.subTest(sql=sql):
                self.assertRaisesRegex(
                    exceptions.Error,
                    u"pyformat_args mismatch",
                    lambda: sql_pyformat_args_to_spanner(sql, params),
                )

    def test_cast_for_spanner(self):
        import decimal

        from google.cloud.spanner_dbapi.parse_utils import cast_for_spanner

        dec = 3
        value = decimal.Decimal(dec)
        self.assertEqual(cast_for_spanner(value), unicode(dec))
        self.assertEqual(cast_for_spanner(5), 5)
        self.assertEqual(cast_for_spanner(u"string"), u"string")

    @unittest.skipIf(skip_condition, skip_message)
    def test_get_param_types(self):
        import datetime

        from google.cloud.spanner_dbapi.parse_utils import DateStr
        from google.cloud.spanner_dbapi.parse_utils import TimestampStr
        from google.cloud.spanner_dbapi.parse_utils import get_param_types

        params = {
            u"a1": 10,
            u"b1": u"string",
            u"c1": 10.39,
            u"d1": TimestampStr(u"2005-08-30T01:01:01.000001Z"),
            u"e1": DateStr(u"2019-12-05"),
            u"f1": True,
            u"g1": datetime.datetime(2011, 9, 1, 13, 20, 30),
            u"h1": datetime.date(2011, 9, 1),
            u"i1": "bytes",
            u"j1": None,
        }
        want_types = {
            u"a1": param_types.INT64,
            u"b1": param_types.STRING,
            u"c1": param_types.FLOAT64,
            u"d1": param_types.TIMESTAMP,
            u"e1": param_types.DATE,
            u"f1": param_types.BOOL,
            u"g1": param_types.TIMESTAMP,
            u"h1": param_types.DATE,
            u"i1": param_types.BYTES,
        }
        got_types = get_param_types(params)
        self.assertEqual(got_types, want_types)

    def test_get_param_types_none(self):
        from google.cloud.spanner_dbapi.parse_utils import get_param_types

        self.assertEqual(get_param_types(None), None)

    @unittest.skipIf(skip_condition, skip_message)
    def test_ensure_where_clause(self):
        from google.cloud.spanner_dbapi.parse_utils import ensure_where_clause

        cases = [
            (
                u"UPDATE a SET a.b=10 FROM articles a JOIN d c ON a.ai = c.ai WHERE c.ci = 1",
                u"UPDATE a SET a.b=10 FROM articles a JOIN d c ON a.ai = c.ai WHERE c.ci = 1",
            ),
            (
                u"UPDATE (SELECT * FROM A JOIN c ON ai.id = c.id WHERE cl.ci = 1) SET d=5",
                u"UPDATE (SELECT * FROM A JOIN c ON ai.id = c.id WHERE cl.ci = 1) SET d=5 WHERE 1=1",
            ),
            (
                u"UPDATE T SET A = 1 WHERE C1 = 1 AND C2 = 2",
                u"UPDATE T SET A = 1 WHERE C1 = 1 AND C2 = 2",
            ),
            (
                u"UPDATE T SET r=r*0.9 WHERE id IN (SELECT id FROM items WHERE r / w >= 1.3 AND q > 100)",
                u"UPDATE T SET r=r*0.9 WHERE id IN (SELECT id FROM items WHERE r / w >= 1.3 AND q > 100)",
            ),
            (
                u"UPDATE T SET r=r*0.9 WHERE id IN (SELECT id FROM items WHERE r / w >= 1.3 AND q > 100)",
                u"UPDATE T SET r=r*0.9 WHERE id IN (SELECT id FROM items WHERE r / w >= 1.3 AND q > 100)",
            ),
            (u"DELETE * FROM TABLE", u"DELETE * FROM TABLE WHERE 1=1"),
        ]

        for sql, want in cases:
            with self.subTest(sql=sql):
                got = ensure_where_clause(sql)
                self.assertEqual(got, want)

    @unittest.skipIf(skip_condition, skip_message)
    def test_escape_name(self):
        from google.cloud.spanner_dbapi.parse_utils import escape_name

        cases = (
            (u"SELECT", u"`SELECT`"),
            (u"dashed-value", u"`dashed-value`"),
            (u"with space", u"`with space`"),
            (u"name", u"name"),
            (u"", u""),
        )
        for name, want in cases:
            with self.subTest(name=name):
                got = escape_name(name)
                self.assertEqual(got, want)
