# Copyright 2016 Google LLC All rights reserved.
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
import collections
import datetime
import decimal
import math
import operator
import os
import struct
import threading
import time
import unittest
import uuid

import grpc
from google.rpc import code_pb2

from google.api_core import exceptions
from google.api_core.datetime_helpers import DatetimeWithNanoseconds

from google.cloud.spanner_v1 import param_types
from google.cloud.spanner_v1 import TypeCode
from google.cloud.spanner_v1 import Type

from google.cloud._helpers import UTC
from google.cloud.spanner_v1 import Client
from google.cloud.spanner_v1 import KeyRange
from google.cloud.spanner_v1 import KeySet
from google.cloud.spanner_v1 import BurstyPool
from google.cloud.spanner_v1 import COMMIT_TIMESTAMP

from test_utils.retry import RetryErrors
from test_utils.retry import RetryInstanceState
from test_utils.retry import RetryResult
from test_utils.system import unique_resource_id
from tests._fixtures import DDL_STATEMENTS
from tests._fixtures import EMULATOR_DDL_STATEMENTS
from tests._helpers import OpenTelemetryBase, HAS_OPENTELEMETRY_INSTALLED
from itertools import izip
from itertools import imap


CREATE_INSTANCE = os.getenv(u"GOOGLE_CLOUD_TESTS_CREATE_SPANNER_INSTANCE") is not None
USE_EMULATOR = os.getenv(u"SPANNER_EMULATOR_HOST") is not None
SKIP_BACKUP_TESTS = os.getenv(u"SKIP_BACKUP_TESTS") is not None

if CREATE_INSTANCE:
    INSTANCE_ID = u"google-cloud" + unique_resource_id(u"-")
else:
    INSTANCE_ID = os.environ.get(
        u"GOOGLE_CLOUD_TESTS_SPANNER_INSTANCE", u"google-cloud-python-systest"
    )
EXISTING_INSTANCES = []
COUNTERS_TABLE = u"counters"
COUNTERS_COLUMNS = (u"name", u"value")

BASE_ATTRIBUTES = {
    u"db.type": u"spanner",
    u"db.url": u"spanner.googleapis.com",
    u"net.host.name": u"spanner.googleapis.com",
}

_STATUS_CODE_TO_GRPC_STATUS_CODE = dict((
    member.value[0], member) for member in grpc.StatusCode)


class Config(object):
    u"""Run-time configuration to be modified at set-up.

    This is a mutable stand-in to allow test set-up to modify
    global state.
    """

    CLIENT = None
    INSTANCE_CONFIG = None
    INSTANCE = None


def _has_all_ddl(database):
    ddl_statements = EMULATOR_DDL_STATEMENTS if USE_EMULATOR else DDL_STATEMENTS
    return len(database.ddl_statements) == len(ddl_statements)


def _list_instances():
    return list(Config.CLIENT.list_instances())


def setUpModule():
    if USE_EMULATOR:
        from google.auth.credentials import AnonymousCredentials

        emulator_project = os.getenv(u"GCLOUD_PROJECT", u"emulator-test-project")
        Config.CLIENT = Client(
            project=emulator_project, credentials=AnonymousCredentials()
        )
    else:
        Config.CLIENT = Client()
    retry = RetryErrors(exceptions.ServiceUnavailable)

    configs = list(retry(Config.CLIENT.list_instance_configs)())

    instances = retry(_list_instances)()
    EXISTING_INSTANCES[:] = instances

    if CREATE_INSTANCE:
        if not USE_EMULATOR:
            # Defend against back-end returning configs for regions we aren't
            # actually allowed to use.
            configs = [config for config in configs if u"-us-" in config.name]

        if not configs:
            raise ValueError(u"List instance configs failed in module set up.")

        Config.INSTANCE_CONFIG = configs[0]
        config_name = configs[0].name

        Config.INSTANCE = Config.CLIENT.instance(INSTANCE_ID, config_name)
        created_op = Config.INSTANCE.create()
        created_op.result(30)  # block until completion

    else:
        Config.INSTANCE = Config.CLIENT.instance(INSTANCE_ID)
        Config.INSTANCE.reload()


def tearDownModule():
    if CREATE_INSTANCE:
        Config.INSTANCE.delete()


class TestInstanceAdminAPI(unittest.TestCase):
    def setUp(self):
        self.instances_to_delete = []

    def tearDown(self):
        for instance in self.instances_to_delete:
            instance.delete()

    @unittest.skipIf(
        CREATE_INSTANCE, u"This test fails when system tests are run in parallel."
    )
    def test_list_instances(self):
        instances = list(Config.CLIENT.list_instances())
        # We have added one new instance in `setUpModule`.
        if CREATE_INSTANCE:
            self.assertEqual(len(instances), len(EXISTING_INSTANCES) + 1)
        for instance in instances:
            instance_existence = (
                instance in EXISTING_INSTANCES or instance == Config.INSTANCE
            )
            self.assertTrue(instance_existence)

    def test_reload_instance(self):
        # Use same arguments as Config.INSTANCE (created in `setUpModule`)
        # so we can use reload() on a fresh instance.
        instance = Config.CLIENT.instance(INSTANCE_ID)
        # Make sure metadata unset before reloading.
        instance.display_name = None

        def _expected_display_name(instance):
            return instance.display_name == Config.INSTANCE.display_name

        retry = RetryInstanceState(_expected_display_name)

        retry(instance.reload)()

        self.assertEqual(instance.display_name, Config.INSTANCE.display_name)

    @unittest.skipUnless(CREATE_INSTANCE, u"Skipping instance creation")
    def test_create_instance(self):
        ALT_INSTANCE_ID = u"new" + unique_resource_id(u"-")
        instance = Config.CLIENT.instance(ALT_INSTANCE_ID, Config.INSTANCE_CONFIG.name)
        operation = instance.create()
        # Make sure this instance gets deleted after the test case.
        self.instances_to_delete.append(instance)

        # We want to make sure the operation completes.
        operation.result(30)  # raises on failure / timeout.

        # Create a new instance instance and make sure it is the same.
        instance_alt = Config.CLIENT.instance(
            ALT_INSTANCE_ID, Config.INSTANCE_CONFIG.name
        )
        instance_alt.reload()

        self.assertEqual(instance, instance_alt)
        self.assertEqual(instance.display_name, instance_alt.display_name)

    @unittest.skipIf(USE_EMULATOR, u"Skipping updating instance")
    def test_update_instance(self):
        OLD_DISPLAY_NAME = Config.INSTANCE.display_name
        NEW_DISPLAY_NAME = u"Foo Bar Baz"
        Config.INSTANCE.display_name = NEW_DISPLAY_NAME
        operation = Config.INSTANCE.update()

        # We want to make sure the operation completes.
        operation.result(30)  # raises on failure / timeout.

        # Create a new instance instance and reload it.
        instance_alt = Config.CLIENT.instance(INSTANCE_ID, None)
        self.assertNotEqual(instance_alt.display_name, NEW_DISPLAY_NAME)
        instance_alt.reload()
        self.assertEqual(instance_alt.display_name, NEW_DISPLAY_NAME)

        # Make sure to put the instance back the way it was for the
        # other test cases.
        Config.INSTANCE.display_name = OLD_DISPLAY_NAME
        Config.INSTANCE.update()


class _TestData(object):
    TABLE = u"contacts"
    COLUMNS = (u"contact_id", u"first_name", u"last_name", u"email")
    ROW_DATA = (
        (1, u"Phred", u"Phlyntstone", u"phred@example.com"),
        (2, u"Bharney", u"Rhubble", u"bharney@example.com"),
        (3, u"Wylma", u"Phlyntstone", u"wylma@example.com"),
    )
    ALL = KeySet(all_=True)
    SQL = u"SELECT * FROM contacts ORDER BY contact_id"

    _recurse_into_lists = True

    def _assert_timestamp(self, value, nano_value):
        self.assertIsInstance(value, datetime.datetime)
        self.assertIsNone(value.tzinfo)
        self.assertIs(nano_value.tzinfo, UTC)

        self.assertEqual(value.year, nano_value.year)
        self.assertEqual(value.month, nano_value.month)
        self.assertEqual(value.day, nano_value.day)
        self.assertEqual(value.hour, nano_value.hour)
        self.assertEqual(value.minute, nano_value.minute)
        self.assertEqual(value.second, nano_value.second)
        self.assertEqual(value.microsecond, nano_value.microsecond)
        if isinstance(value, DatetimeWithNanoseconds):
            self.assertEqual(value.nanosecond, nano_value.nanosecond)
        else:
            self.assertEqual(value.microsecond * 1000, nano_value.nanosecond)

    def _check_rows_data(self, rows_data, expected=None):
        if expected is None:
            expected = self.ROW_DATA

        self.assertEqual(len(rows_data), len(expected))
        for row, expected in izip(rows_data, expected):
            self._check_row_data(row, expected)

    def _check_row_data(self, row_data, expected):
        self.assertEqual(len(row_data), len(expected))
        for found_cell, expected_cell in izip(row_data, expected):
            self._check_cell_data(found_cell, expected_cell)

    def _check_cell_data(self, found_cell, expected_cell):
        if isinstance(found_cell, DatetimeWithNanoseconds):
            self._assert_timestamp(expected_cell, found_cell)
        elif isinstance(found_cell, float) and math.isnan(found_cell):
            self.assertTrue(math.isnan(expected_cell))
        elif isinstance(found_cell, list) and self._recurse_into_lists:
            self.assertEqual(len(found_cell), len(expected_cell))
            for found_item, expected_item in izip(found_cell, expected_cell):
                self._check_cell_data(found_item, expected_item)
        else:
            self.assertEqual(found_cell, expected_cell)


class TestDatabaseAPI(unittest.TestCase, _TestData):
    DATABASE_NAME = u"test_database" + unique_resource_id(u"_")

    @classmethod
    def setUpClass(cls):
        pool = BurstyPool(labels={u"testcase": u"database_api"})
        ddl_statements = EMULATOR_DDL_STATEMENTS if USE_EMULATOR else DDL_STATEMENTS
        cls._db = Config.INSTANCE.database(
            cls.DATABASE_NAME, ddl_statements=ddl_statements, pool=pool
        )
        operation = cls._db.create()
        operation.result(30)  # raises on failure / timeout.

    @classmethod
    def tearDownClass(cls):
        cls._db.drop()

    def setUp(self):
        self.to_delete = []

    def tearDown(self):
        for doomed in self.to_delete:
            doomed.drop()

    def test_list_databases(self):
        # Since `Config.INSTANCE` is newly created in `setUpModule`, the
        # database created in `setUpClass` here will be the only one.
        database_names = [
            database.name for database in Config.INSTANCE.list_databases()
        ]
        self.assertTrue(self._db.name in database_names)

    def test_create_database(self):
        pool = BurstyPool(labels={u"testcase": u"create_database"})
        temp_db_id = u"temp_db" + unique_resource_id(u"_")
        temp_db = Config.INSTANCE.database(temp_db_id, pool=pool)
        operation = temp_db.create()
        self.to_delete.append(temp_db)

        # We want to make sure the operation completes.
        operation.result(30)  # raises on failure / timeout.

        database_ids = [database.name for database in Config.INSTANCE.list_databases()]
        self.assertIn(temp_db.name, database_ids)

    def test_table_not_found(self):
        temp_db_id = u"temp_db" + unique_resource_id(u"_")

        correct_table = u"MyTable"
        incorrect_table = u"NotMyTable"
        self.assertNotEqual(correct_table, incorrect_table)

        create_table = (
            u"CREATE TABLE {} (\n"
            u"    Id      STRING(36) NOT NULL,\n"
            u"    Field1  STRING(36) NOT NULL\n"
            u") PRIMARY KEY (Id)"
        ).format(correct_table)
        index = u"CREATE INDEX IDX ON {} (Field1)".format(incorrect_table)

        temp_db = Config.INSTANCE.database(
            temp_db_id, ddl_statements=[create_table, index]
        )
        self.to_delete.append(temp_db)
        with self.assertRaises(exceptions.NotFound):
            temp_db.create()

    @unittest.skip(
        (
            u"update_dataset_ddl() has a flaky timeout"
            u"https://github.com/GoogleCloudPlatform/google-cloud-python/issues/"
            u"5629"
        )
    )
    def test_update_database_ddl_with_operation_id(self):
        pool = BurstyPool(labels={u"testcase": u"update_database_ddl"})
        temp_db_id = u"temp_db" + unique_resource_id(u"_")
        temp_db = Config.INSTANCE.database(temp_db_id, pool=pool)
        create_op = temp_db.create()
        self.to_delete.append(temp_db)
        ddl_statements = EMULATOR_DDL_STATEMENTS if USE_EMULATOR else DDL_STATEMENTS

        # We want to make sure the operation completes.
        create_op.result(240)  # raises on failure / timeout.
        # random but shortish always start with letter
        operation_id = u"a" + unicode(uuid.uuid4())[:8]
        operation = temp_db.update_ddl(ddl_statements, operation_id=operation_id)

        self.assertEqual(operation_id, operation.operation.name.split(u"/")[-1])

        # We want to make sure the operation completes.
        operation.result(240)  # raises on failure / timeout.

        temp_db.reload()

        self.assertEqual(len(temp_db.ddl_statements), len(ddl_statements))

    def test_db_batch_insert_then_db_snapshot_read(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        with self._db.batch() as batch:
            batch.delete(self.TABLE, self.ALL)
            batch.insert(self.TABLE, self.COLUMNS, self.ROW_DATA)

        with self._db.snapshot(read_timestamp=batch.committed) as snapshot:
            from_snap = list(snapshot.read(self.TABLE, self.COLUMNS, self.ALL))

        self._check_rows_data(from_snap)

    def test_db_run_in_transaction_then_snapshot_execute_sql(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        with self._db.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        def _unit_of_work(transaction, test):
            rows = list(transaction.read(test.TABLE, test.COLUMNS, self.ALL))
            test.assertEqual(rows, [])

            transaction.insert_or_update(test.TABLE, test.COLUMNS, test.ROW_DATA)

        self._db.run_in_transaction(_unit_of_work, test=self)

        with self._db.snapshot() as after:
            rows = list(after.execute_sql(self.SQL))
        self._check_rows_data(rows)

    def test_db_run_in_transaction_twice(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        with self._db.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        def _unit_of_work(transaction, test):
            transaction.insert_or_update(test.TABLE, test.COLUMNS, test.ROW_DATA)

        self._db.run_in_transaction(_unit_of_work, test=self)
        self._db.run_in_transaction(_unit_of_work, test=self)

        with self._db.snapshot() as after:
            rows = list(after.execute_sql(self.SQL))
        self._check_rows_data(rows)

    def test_db_run_in_transaction_twice_4181(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        with self._db.batch() as batch:
            batch.delete(COUNTERS_TABLE, self.ALL)

        def _unit_of_work(transaction, name):
            transaction.insert(COUNTERS_TABLE, COUNTERS_COLUMNS, [[name, 0]])

        self._db.run_in_transaction(_unit_of_work, name=u"id_1")

        with self.assertRaises(exceptions.AlreadyExists):
            self._db.run_in_transaction(_unit_of_work, name=u"id_1")

        self._db.run_in_transaction(_unit_of_work, name=u"id_2")

        with self._db.snapshot() as after:
            rows = list(after.read(COUNTERS_TABLE, COUNTERS_COLUMNS, self.ALL))
        self.assertEqual(len(rows), 2)


class TestBackupAPI(unittest.TestCase, _TestData):
    DATABASE_NAME = u"test_database" + unique_resource_id(u"_")
    DATABASE_NAME_2 = u"test_database2" + unique_resource_id(u"_")

    @classmethod
    def setUpClass(cls):
        pool = BurstyPool(labels={u"testcase": u"database_api"})
        ddl_statements = EMULATOR_DDL_STATEMENTS if USE_EMULATOR else DDL_STATEMENTS
        db1 = Config.INSTANCE.database(
            cls.DATABASE_NAME, ddl_statements=ddl_statements, pool=pool
        )
        db2 = Config.INSTANCE.database(cls.DATABASE_NAME_2, pool=pool)
        cls._db = db1
        cls._dbs = [db1, db2]
        op1 = db1.create()
        op2 = db2.create()
        op1.result(30)  # raises on failure / timeout.
        op2.result(30)  # raises on failure / timeout.

        current_config = Config.INSTANCE.configuration_name
        same_config_instance_id = u"same-config" + unique_resource_id(u"-")
        cls._same_config_instance = Config.CLIENT.instance(
            same_config_instance_id, current_config
        )
        op = cls._same_config_instance.create()
        op.result(30)
        cls._instances = [cls._same_config_instance]

        retry = RetryErrors(exceptions.ServiceUnavailable)
        configs = list(retry(Config.CLIENT.list_instance_configs)())
        diff_configs = [
            config.name
            for config in configs
            if u"-us-" in config.name and config.name is not current_config
        ]
        cls._diff_config_instance = None
        if len(diff_configs) > 0:
            diff_config_instance_id = u"diff-config" + unique_resource_id(u"-")
            cls._diff_config_instance = Config.CLIENT.instance(
                diff_config_instance_id, diff_configs[0]
            )
            op = cls._diff_config_instance.create()
            op.result(30)
            cls._instances.append(cls._diff_config_instance)

    @classmethod
    def tearDownClass(cls):
        for db in cls._dbs:
            db.drop()
        for instance in cls._instances:
            instance.delete()

    def setUp(self):
        self.to_delete = []
        self.to_drop = []

    def tearDown(self):
        for doomed in self.to_delete:
            doomed.delete()
        for doomed in self.to_drop:
            doomed.drop()

    def test_create_invalid(self):
        from datetime import datetime
        from pytz import UTC

        backup_id = u"backup_id" + unique_resource_id(u"_")
        expire_time = datetime.utcnow()
        expire_time = expire_time.replace(tzinfo=UTC)

        backup = Config.INSTANCE.backup(
            backup_id, database=self._db, expire_time=expire_time
        )

        with self.assertRaises(exceptions.InvalidArgument):
            op = backup.create()
            op.result()

    def test_backup_workflow(self):
        from datetime import datetime
        from datetime import timedelta
        from pytz import UTC

        instance = Config.INSTANCE
        backup_id = u"backup_id" + unique_resource_id(u"_")
        expire_time = datetime.utcnow() + timedelta(days=3)
        expire_time = expire_time.replace(tzinfo=UTC)

        # Create backup.
        backup = instance.backup(backup_id, database=self._db, expire_time=expire_time)
        operation = backup.create()
        self.to_delete.append(backup)

        # Check metadata.
        metadata = operation.metadata
        self.assertEqual(backup.name, metadata.name)
        self.assertEqual(self._db.name, metadata.database)
        operation.result()

        # Check backup object.
        backup.reload()
        self.assertEqual(self._db.name, backup._database)
        self.assertEqual(expire_time, backup.expire_time)
        self.assertIsNotNone(backup.create_time)
        self.assertIsNotNone(backup.size_bytes)
        self.assertIsNotNone(backup.state)

        # Update with valid argument.
        valid_expire_time = datetime.utcnow() + timedelta(days=7)
        valid_expire_time = valid_expire_time.replace(tzinfo=UTC)
        backup.update_expire_time(valid_expire_time)
        self.assertEqual(valid_expire_time, backup.expire_time)

        # Restore database to same instance.
        restored_id = u"restored_db" + unique_resource_id(u"_")
        database = instance.database(restored_id)
        self.to_drop.append(database)
        operation = database.restore(source=backup)
        operation.result()

        database.drop()
        backup.delete()
        self.assertFalse(backup.exists())

    def test_restore_to_diff_instance(self):
        from datetime import datetime
        from datetime import timedelta
        from pytz import UTC

        backup_id = u"backup_id" + unique_resource_id(u"_")
        expire_time = datetime.utcnow() + timedelta(days=3)
        expire_time = expire_time.replace(tzinfo=UTC)

        # Create backup.
        backup = Config.INSTANCE.backup(
            backup_id, database=self._db, expire_time=expire_time
        )
        op = backup.create()
        self.to_delete.append(backup)
        op.result()

        # Restore database to different instance with same config.
        restored_id = u"restored_db" + unique_resource_id(u"_")
        database = self._same_config_instance.database(restored_id)
        self.to_drop.append(database)
        operation = database.restore(source=backup)
        operation.result()

        database.drop()
        backup.delete()
        self.assertFalse(backup.exists())

    def test_multi_create_cancel_update_error_restore_errors(self):
        from datetime import datetime
        from datetime import timedelta
        from pytz import UTC

        backup_id_1 = u"backup_id1" + unique_resource_id(u"_")
        backup_id_2 = u"backup_id2" + unique_resource_id(u"_")

        instance = Config.INSTANCE
        expire_time = datetime.utcnow() + timedelta(days=3)
        expire_time = expire_time.replace(tzinfo=UTC)

        backup1 = instance.backup(
            backup_id_1, database=self._dbs[0], expire_time=expire_time
        )
        backup2 = instance.backup(
            backup_id_2, database=self._dbs[1], expire_time=expire_time
        )

        # Create two backups.
        op1 = backup1.create()
        op2 = backup2.create()
        self.to_delete.extend([backup1, backup2])

        backup1.reload()
        self.assertFalse(backup1.is_ready())
        backup2.reload()
        self.assertFalse(backup2.is_ready())

        # Cancel a create operation.
        op2.cancel()
        self.assertTrue(op2.cancelled())

        op1.result()
        backup1.reload()
        self.assertTrue(backup1.is_ready())

        # Update expire time to invalid value.
        invalid_expire_time = datetime.now() + timedelta(days=366)
        invalid_expire_time = invalid_expire_time.replace(tzinfo=UTC)
        with self.assertRaises(exceptions.InvalidArgument):
            backup1.update_expire_time(invalid_expire_time)

        # Restore to existing database.
        with self.assertRaises(exceptions.AlreadyExists):
            self._db.restore(source=backup1)

        # Restore to instance with different config.
        if self._diff_config_instance is not None:
            return
        new_db = self._diff_config_instance.database(u"diff_config")
        op = new_db.create()
        op.result(30)
        self.to_drop.append(new_db)
        with self.assertRaises(exceptions.InvalidArgument):
            new_db.restore(source=backup1)

    def test_list_backups(self):
        from datetime import datetime
        from datetime import timedelta
        from pytz import UTC

        backup_id_1 = u"backup_id1" + unique_resource_id(u"_")
        backup_id_2 = u"backup_id2" + unique_resource_id(u"_")

        instance = Config.INSTANCE
        expire_time_1 = datetime.utcnow() + timedelta(days=21)
        expire_time_1 = expire_time_1.replace(tzinfo=UTC)

        backup1 = Config.INSTANCE.backup(
            backup_id_1, database=self._dbs[0], expire_time=expire_time_1
        )

        expire_time_2 = datetime.utcnow() + timedelta(days=1)
        expire_time_2 = expire_time_2.replace(tzinfo=UTC)
        backup2 = Config.INSTANCE.backup(
            backup_id_2, database=self._dbs[1], expire_time=expire_time_2
        )

        # Create two backups.
        op1 = backup1.create()
        op1.result()
        backup1.reload()
        create_time_compare = datetime.utcnow().replace(tzinfo=UTC)

        backup2.create()
        self.to_delete.extend([backup1, backup2])

        # List backups filtered by state.
        filter_ = u"state:CREATING"
        for backup in instance.list_backups(filter_=filter_):
            self.assertEqual(backup.name, backup2.name)

        # List backups filtered by backup name.
        filter_ = u"name:{0}".format(backup_id_1)
        for backup in instance.list_backups(filter_=filter_):
            self.assertEqual(backup.name, backup1.name)

        # List backups filtered by database name.
        filter_ = u"database:{0}".format(self._dbs[0].name)
        for backup in instance.list_backups(filter_=filter_):
            self.assertEqual(backup.name, backup1.name)

        # List backups filtered by create time.
        filter_ = u'create_time > "{0}"'.format(
            create_time_compare.strftime(u"%Y-%m-%dT%H:%M:%S.%fZ")
        )
        for backup in instance.list_backups(filter_=filter_):
            self.assertEqual(backup.name, backup2.name)

        # List backups filtered by expire time.
        filter_ = u'expire_time > "{0}"'.format(
            expire_time_1.strftime(u"%Y-%m-%dT%H:%M:%S.%fZ")
        )
        for backup in instance.list_backups(filter_=filter_):
            self.assertEqual(backup.name, backup1.name)

        # List backups filtered by size bytes.
        filter_ = u"size_bytes < {0}".format(backup1.size_bytes)
        for backup in instance.list_backups(filter_=filter_):
            self.assertEqual(backup.name, backup2.name)

        # List backups using pagination.
        count = 0
        for page in instance.list_backups(page_size=1):
            count += 1
        self.assertEqual(count, 2)


TestBackupAPI = unittest.skipIf(USE_EMULATOR, u"Skipping backup tests")(unittest.skipIf(SKIP_BACKUP_TESTS, u"Skipping backup tests")(TestBackupAPI))

SOME_DATE = datetime.date(2011, 1, 17)
SOME_TIME = datetime.datetime(1989, 1, 17, 17, 59, 12, 345612)
NANO_TIME = DatetimeWithNanoseconds(1995, 8, 31, nanosecond=987654321)
POS_INF = float(u"+inf")
NEG_INF = float(u"-inf")
(OTHER_NAN,) = struct.unpack(u"<d", "\x01\x00\x01\x00\x00\x00\xf8\xff")
BYTES_1 = "Ymlu"
BYTES_2 = "Ym9vdHM="
NUMERIC_1 = decimal.Decimal(u"0.123456789")
NUMERIC_2 = decimal.Decimal(u"1234567890")
ALL_TYPES_TABLE = u"all_types"
ALL_TYPES_COLUMNS = (
    u"pkey",
    u"int_value",
    u"int_array",
    u"bool_value",
    u"bool_array",
    u"bytes_value",
    u"bytes_array",
    u"date_value",
    u"date_array",
    u"float_value",
    u"float_array",
    u"string_value",
    u"string_array",
    u"timestamp_value",
    u"timestamp_array",
    u"numeric_value",
    u"numeric_array",
)
EMULATOR_ALL_TYPES_COLUMNS = ALL_TYPES_COLUMNS[:-2]
AllTypesRowData = collections.namedtuple(u"AllTypesRowData", ALL_TYPES_COLUMNS)
AllTypesRowData.__new__.func_defaults = tuple([None for colum in ALL_TYPES_COLUMNS])
EmulatorAllTypesRowData = collections.namedtuple(
    u"EmulatorAllTypesRowData", EMULATOR_ALL_TYPES_COLUMNS
)
EmulatorAllTypesRowData.__new__.func_defaults = tuple(
    [None for colum in EMULATOR_ALL_TYPES_COLUMNS]
)

ALL_TYPES_ROWDATA = (
    # all nulls
    AllTypesRowData(pkey=0),
    # Non-null values
    AllTypesRowData(pkey=101, int_value=123),
    AllTypesRowData(pkey=102, bool_value=False),
    AllTypesRowData(pkey=103, bytes_value=BYTES_1),
    AllTypesRowData(pkey=104, date_value=SOME_DATE),
    AllTypesRowData(pkey=105, float_value=1.4142136),
    AllTypesRowData(pkey=106, string_value=u"VALUE"),
    AllTypesRowData(pkey=107, timestamp_value=SOME_TIME),
    AllTypesRowData(pkey=108, timestamp_value=NANO_TIME),
    AllTypesRowData(pkey=109, numeric_value=NUMERIC_1),
    # empty array values
    AllTypesRowData(pkey=201, int_array=[]),
    AllTypesRowData(pkey=202, bool_array=[]),
    AllTypesRowData(pkey=203, bytes_array=[]),
    AllTypesRowData(pkey=204, date_array=[]),
    AllTypesRowData(pkey=205, float_array=[]),
    AllTypesRowData(pkey=206, string_array=[]),
    AllTypesRowData(pkey=207, timestamp_array=[]),
    AllTypesRowData(pkey=208, numeric_array=[]),
    # non-empty array values, including nulls
    AllTypesRowData(pkey=301, int_array=[123, 456, None]),
    AllTypesRowData(pkey=302, bool_array=[True, False, None]),
    AllTypesRowData(pkey=303, bytes_array=[BYTES_1, BYTES_2, None]),
    AllTypesRowData(pkey=304, date_array=[SOME_DATE, None]),
    AllTypesRowData(pkey=305, float_array=[3.1415926, 2.71828, None]),
    AllTypesRowData(pkey=306, string_array=[u"One", u"Two", None]),
    AllTypesRowData(pkey=307, timestamp_array=[SOME_TIME, NANO_TIME, None]),
    AllTypesRowData(pkey=308, numeric_array=[NUMERIC_1, NUMERIC_2, None]),
)
EMULATOR_ALL_TYPES_ROWDATA = (
    # all nulls
    EmulatorAllTypesRowData(pkey=0),
    # Non-null values
    EmulatorAllTypesRowData(pkey=101, int_value=123),
    EmulatorAllTypesRowData(pkey=102, bool_value=False),
    EmulatorAllTypesRowData(pkey=103, bytes_value=BYTES_1),
    EmulatorAllTypesRowData(pkey=104, date_value=SOME_DATE),
    EmulatorAllTypesRowData(pkey=105, float_value=1.4142136),
    EmulatorAllTypesRowData(pkey=106, string_value=u"VALUE"),
    EmulatorAllTypesRowData(pkey=107, timestamp_value=SOME_TIME),
    EmulatorAllTypesRowData(pkey=108, timestamp_value=NANO_TIME),
    # empty array values
    EmulatorAllTypesRowData(pkey=201, int_array=[]),
    EmulatorAllTypesRowData(pkey=202, bool_array=[]),
    EmulatorAllTypesRowData(pkey=203, bytes_array=[]),
    EmulatorAllTypesRowData(pkey=204, date_array=[]),
    EmulatorAllTypesRowData(pkey=205, float_array=[]),
    EmulatorAllTypesRowData(pkey=206, string_array=[]),
    EmulatorAllTypesRowData(pkey=207, timestamp_array=[]),
    # non-empty array values, including nulls
    EmulatorAllTypesRowData(pkey=301, int_array=[123, 456, None]),
    EmulatorAllTypesRowData(pkey=302, bool_array=[True, False, None]),
    EmulatorAllTypesRowData(pkey=303, bytes_array=[BYTES_1, BYTES_2, None]),
    EmulatorAllTypesRowData(pkey=304, date_array=[SOME_DATE, None]),
    EmulatorAllTypesRowData(pkey=305, float_array=[3.1415926, 2.71828, None]),
    EmulatorAllTypesRowData(pkey=306, string_array=[u"One", u"Two", None]),
    EmulatorAllTypesRowData(pkey=307, timestamp_array=[SOME_TIME, NANO_TIME, None]),
)


class TestSessionAPI(OpenTelemetryBase, _TestData):
    DATABASE_NAME = u"test_sessions" + unique_resource_id(u"_")

    @classmethod
    def setUpClass(cls):
        pool = BurstyPool(labels={u"testcase": u"session_api"})
        ddl_statements = EMULATOR_DDL_STATEMENTS if USE_EMULATOR else DDL_STATEMENTS
        cls._db = Config.INSTANCE.database(
            cls.DATABASE_NAME, ddl_statements=ddl_statements, pool=pool
        )
        operation = cls._db.create()
        operation.result(30)  # raises on failure / timeout.

    @classmethod
    def tearDownClass(cls):
        cls._db.drop()

    def setUp(self):
        super(TestSessionAPI, self).setUp()
        self.to_delete = []

    def tearDown(self):
        super(TestSessionAPI, self).tearDown()
        for doomed in self.to_delete:
            doomed.delete()

    def test_session_crud(self):
        retry_true = RetryResult(operator.truth)
        retry_false = RetryResult(operator.not_)
        session = self._db.session()
        self.assertFalse(session.exists())
        session.create()
        retry_true(session.exists)()
        session.delete()
        retry_false(session.exists)()

    def test_batch_insert_then_read(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        with self._db.batch() as batch:
            batch.delete(self.TABLE, self.ALL)
            batch.insert(self.TABLE, self.COLUMNS, self.ROW_DATA)

        with self._db.snapshot(read_timestamp=batch.committed) as snapshot:
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, self.ALL))
        self._check_rows_data(rows)

        if HAS_OPENTELEMETRY_INSTALLED:
            span_list = self.memory_exporter.get_finished_spans()
            self.assertEqual(len(span_list), 4)
            self.assertSpanAttributes(
                u"CloudSpanner.GetSession",
                attributes=dict(
                    BASE_ATTRIBUTES,
                    **{u"db.instance": self._db.name, u"session_found": True}
                ),
                span=span_list[0],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.Commit",
                attributes=dict(
                    BASE_ATTRIBUTES,
                    **{u"db.instance": self._db.name, u"num_mutations": 2}
                ),
                span=span_list[1],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.GetSession",
                attributes=dict(
                    BASE_ATTRIBUTES,
                    **{u"db.instance": self._db.name, u"session_found": True}
                ),
                span=span_list[2],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.ReadOnlyTransaction",
                attributes=dict(
                    BASE_ATTRIBUTES,
                    **{
                        u"db.instance": self._db.name,
                        u"columns": self.COLUMNS,
                        u"table_id": self.TABLE,
                    }
                ),
                span=span_list[3],
            )

    def test_batch_insert_then_read_string_array_of_string(self):
        TABLE = u"string_plus_array_of_string"
        COLUMNS = [u"id", u"name", u"tags"]
        ROWDATA = [
            (0, None, None),
            (1, u"phred", [u"yabba", u"dabba", u"do"]),
            (2, u"bharney", []),
            (3, u"wylma", [u"oh", None, u"phred"]),
        ]
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        with self._db.batch() as batch:
            batch.delete(TABLE, self.ALL)
            batch.insert(TABLE, COLUMNS, ROWDATA)

        with self._db.snapshot(read_timestamp=batch.committed) as snapshot:
            rows = list(snapshot.read(TABLE, COLUMNS, self.ALL))
        self._check_rows_data(rows, expected=ROWDATA)

    def test_batch_insert_then_read_all_datatypes(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        if USE_EMULATOR:
            all_types_columns = EMULATOR_ALL_TYPES_COLUMNS
            all_types_rowdata = EMULATOR_ALL_TYPES_ROWDATA
        else:
            all_types_columns = ALL_TYPES_COLUMNS
            all_types_rowdata = ALL_TYPES_ROWDATA
        with self._db.batch() as batch:
            batch.delete(ALL_TYPES_TABLE, self.ALL)
            batch.insert(ALL_TYPES_TABLE, all_types_columns, all_types_rowdata)

        with self._db.snapshot(read_timestamp=batch.committed) as snapshot:
            rows = list(snapshot.read(ALL_TYPES_TABLE, all_types_columns, self.ALL))
        self._check_rows_data(rows, expected=all_types_rowdata)

    def test_batch_insert_or_update_then_query(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        with self._db.batch() as batch:
            batch.insert_or_update(self.TABLE, self.COLUMNS, self.ROW_DATA)

        with self._db.snapshot(read_timestamp=batch.committed) as snapshot:
            rows = list(snapshot.execute_sql(self.SQL))
        self._check_rows_data(rows)

    def test_batch_insert_w_commit_timestamp(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        table = u"users_history"
        columns = [u"id", u"commit_ts", u"name", u"email", u"deleted"]
        user_id = 1234
        name = u"phred"
        email = u"phred@example.com"
        row_data = [[user_id, COMMIT_TIMESTAMP, name, email, False]]

        with self._db.batch() as batch:
            batch.delete(table, self.ALL)
            batch.insert(table, columns, row_data)

        with self._db.snapshot(read_timestamp=batch.committed) as snapshot:
            rows = list(snapshot.read(table, columns, self.ALL))

        self.assertEqual(len(rows), 1)
        r_id, commit_ts, r_name, r_email, deleted = rows[0]
        self.assertEqual(r_id, user_id)
        self.assertEqual(commit_ts, batch.committed)
        self.assertEqual(r_name, name)
        self.assertEqual(r_email, email)
        self.assertFalse(deleted)

    @RetryErrors(exception=exceptions.ServerError)
    @RetryErrors(exception=exceptions.Aborted)
    def test_transaction_read_and_insert_then_rollback(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with self._db.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        transaction = session.transaction()
        transaction.begin()

        rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
        self.assertEqual(rows, [])

        transaction.insert(self.TABLE, self.COLUMNS, self.ROW_DATA)

        # Inserted rows can't be read until after commit.
        rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
        self.assertEqual(rows, [])
        transaction.rollback()

        rows = list(session.read(self.TABLE, self.COLUMNS, self.ALL))
        self.assertEqual(rows, [])

        if HAS_OPENTELEMETRY_INSTALLED:
            span_list = self.memory_exporter.get_finished_spans()
            self.assertEqual(len(span_list), 8)
            self.assertSpanAttributes(
                u"CloudSpanner.CreateSession",
                attributes=dict(BASE_ATTRIBUTES, **{u"db.instance": self._db.name}),
                span=span_list[0],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.GetSession",
                attributes=dict(
                    BASE_ATTRIBUTES,
                    **{u"db.instance": self._db.name, u"session_found": True}
                ),
                span=span_list[1],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.Commit",
                attributes=dict(
                    BASE_ATTRIBUTES,
                    **{u"db.instance": self._db.name, u"num_mutations": 1}
                ),
                span=span_list[2],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.BeginTransaction",
                attributes=dict(BASE_ATTRIBUTES, **{u"db.instance": self._db.name}),
                span=span_list[3],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.ReadOnlyTransaction",
                attributes=dict(
                    BASE_ATTRIBUTES,
                    **{
                        u"db.instance": self._db.name,
                        u"table_id": self.TABLE,
                        u"columns": self.COLUMNS,
                    }
                ),
                span=span_list[4],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.ReadOnlyTransaction",
                attributes=dict(
                    BASE_ATTRIBUTES,
                    **{
                        u"db.instance": self._db.name,
                        u"table_id": self.TABLE,
                        u"columns": self.COLUMNS,
                    }
                ),
                span=span_list[5],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.Rollback",
                attributes=dict(BASE_ATTRIBUTES, **{u"db.instance": self._db.name}),
                span=span_list[6],
            )
            self.assertSpanAttributes(
                u"CloudSpanner.ReadOnlyTransaction",
                attributes=dict(
                    BASE_ATTRIBUTES,
                    **{
                        u"db.instance": self._db.name,
                        u"table_id": self.TABLE,
                        u"columns": self.COLUMNS,
                    }
                ),
                span=span_list[7],
            )

    def _transaction_read_then_raise(self, transaction):
        rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
        self.assertEqual(len(rows), 0)
        transaction.insert(self.TABLE, self.COLUMNS, self.ROW_DATA)
        raise CustomException()

    @RetryErrors(exception=exceptions.ServerError)
    @RetryErrors(exception=exceptions.Conflict)
    def test_transaction_read_and_insert_then_exception(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        with self._db.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        with self.assertRaises(CustomException):
            self._db.run_in_transaction(self._transaction_read_then_raise)

        # Transaction was rolled back.
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, self.ALL))
        self.assertEqual(rows, [])

    @RetryErrors(exception=exceptions.ServerError)
    @RetryErrors(exception=exceptions.Conflict)
    def test_transaction_read_and_insert_or_update_then_commit(self):
        # [START spanner_test_dml_read_your_writes]
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with session.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        with session.transaction() as transaction:
            rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
            self.assertEqual(rows, [])

            transaction.insert_or_update(self.TABLE, self.COLUMNS, self.ROW_DATA)

            # Inserted rows can't be read until after commit.
            rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
            self.assertEqual(rows, [])

        rows = list(session.read(self.TABLE, self.COLUMNS, self.ALL))
        self._check_rows_data(rows)
        # [END spanner_test_dml_read_your_writes]

    def _generate_insert_statements(self):
        insert_template = u"INSERT INTO {table} ({column_list}) " u"VALUES ({row_data})"
        for row in self.ROW_DATA:
            yield insert_template.format(
                table=self.TABLE,
                column_list=u", ".join(self.COLUMNS),
                row_data=u'{}, "{}", "{}", "{}"'.format(*row),
            )

    @RetryErrors(exception=exceptions.ServerError)
    @RetryErrors(exception=exceptions.Conflict)
    def test_transaction_execute_sql_w_dml_read_rollback(self):
        # [START spanner_test_dml_rollback_txn_not_committed]
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with session.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        transaction = session.transaction()
        transaction.begin()

        rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
        self.assertEqual(rows, [])

        for insert_statement in self._generate_insert_statements():
            result = transaction.execute_sql(insert_statement)
            list(result)  # iterate to get stats
            self.assertEqual(result.stats.row_count_exact, 1)

        # Rows inserted via DML *can* be read before commit.
        during_rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
        self._check_rows_data(during_rows)

        transaction.rollback()

        rows = list(session.read(self.TABLE, self.COLUMNS, self.ALL))
        self._check_rows_data(rows, [])
        # [END spanner_test_dml_rollback_txn_not_committed]

    @RetryErrors(exception=exceptions.ServerError)
    @RetryErrors(exception=exceptions.Conflict)
    def test_transaction_execute_update_read_commit(self):
        # [START spanner_test_dml_read_your_writes]
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with session.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        with session.transaction() as transaction:
            rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
            self.assertEqual(rows, [])

            for insert_statement in self._generate_insert_statements():
                row_count = transaction.execute_update(insert_statement)
                self.assertEqual(row_count, 1)

            # Rows inserted via DML *can* be read before commit.
            during_rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_rows_data(during_rows)

        rows = list(session.read(self.TABLE, self.COLUMNS, self.ALL))
        self._check_rows_data(rows)
        # [END spanner_test_dml_read_your_writes]

    @RetryErrors(exception=exceptions.ServerError)
    @RetryErrors(exception=exceptions.Conflict)
    def test_transaction_execute_update_then_insert_commit(self):
        # [START spanner_test_dml_with_mutation]
        # [START spanner_test_dml_update]
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with session.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        insert_statement = list(self._generate_insert_statements())[0]

        with session.transaction() as transaction:
            rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
            self.assertEqual(rows, [])

            row_count = transaction.execute_update(insert_statement)
            self.assertEqual(row_count, 1)

            transaction.insert(self.TABLE, self.COLUMNS, self.ROW_DATA[1:])

        rows = list(session.read(self.TABLE, self.COLUMNS, self.ALL))
        self._check_rows_data(rows)
        # [END spanner_test_dml_update]
        # [END spanner_test_dml_with_mutation]

    @staticmethod
    def _check_batch_status(status_code, expected=code_pb2.OK):
        if status_code != expected:
            grpc_status_code = _STATUS_CODE_TO_GRPC_STATUS_CODE[status_code]
            call = FauxCall(status_code)
            raise exceptions.from_grpc_status(
                grpc_status_code, u"batch_update failed", errors=[call]
            )

    def test_transaction_batch_update_success(self):
        # [START spanner_test_dml_with_mutation]
        # [START spanner_test_dml_update]
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with session.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        insert_statement = list(self._generate_insert_statements())[0]
        update_statement = (
            u"UPDATE contacts SET email = @email " u"WHERE contact_id = @contact_id;",
            {u"contact_id": 1, u"email": u"phreddy@example.com"},
            {u"contact_id": param_types.INT64, u"email": param_types.STRING},
        )
        delete_statement = (
            u"DELETE contacts WHERE contact_id = @contact_id;",
            {u"contact_id": 1},
            {u"contact_id": param_types.INT64},
        )

        def unit_of_work(transaction, self):
            rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
            self.assertEqual(rows, [])

            status, row_counts = transaction.batch_update(
                [insert_statement, update_statement, delete_statement]
            )
            self._check_batch_status(status.code)
            self.assertEqual(len(row_counts), 3)
            for row_count in row_counts:
                self.assertEqual(row_count, 1)

        session.run_in_transaction(unit_of_work, self)

        rows = list(session.read(self.TABLE, self.COLUMNS, self.ALL))
        self._check_rows_data(rows, [])
        # [END spanner_test_dml_with_mutation]
        # [END spanner_test_dml_update]

    def test_transaction_batch_update_and_execute_dml(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with session.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        insert_statements = list(self._generate_insert_statements())
        update_statements = [
            (
                u"UPDATE contacts SET email = @email " u"WHERE contact_id = @contact_id;",
                {u"contact_id": 1, u"email": u"phreddy@example.com"},
                {u"contact_id": param_types.INT64, u"email": param_types.STRING},
            )
        ]

        delete_statement = u"DELETE contacts WHERE TRUE;"

        def unit_of_work(transaction, self):
            rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
            self.assertEqual(rows, [])

            status, row_counts = transaction.batch_update(
                insert_statements + update_statements
            )
            self._check_batch_status(status.code)
            self.assertEqual(len(row_counts), len(insert_statements) + 1)
            for row_count in row_counts:
                self.assertEqual(row_count, 1)

            row_count = transaction.execute_update(delete_statement)

            self.assertEqual(row_count, len(insert_statements))

        session.run_in_transaction(unit_of_work, self)

        rows = list(session.read(self.TABLE, self.COLUMNS, self.ALL))
        self._check_rows_data(rows, [])

    def test_transaction_batch_update_w_syntax_error(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with session.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        insert_statement = list(self._generate_insert_statements())[0]
        update_statement = (
            u"UPDTAE contacts SET email = @email " u"WHERE contact_id = @contact_id;",
            {u"contact_id": 1, u"email": u"phreddy@example.com"},
            {u"contact_id": param_types.INT64, u"email": param_types.STRING},
        )
        delete_statement = (
            u"DELETE contacts WHERE contact_id = @contact_id;",
            {u"contact_id": 1},
            {u"contact_id": param_types.INT64},
        )

        def unit_of_work(transaction):
            rows = list(transaction.read(self.TABLE, self.COLUMNS, self.ALL))
            self.assertEqual(rows, [])

            status, row_counts = transaction.batch_update(
                [insert_statement, update_statement, delete_statement]
            )
            self._check_batch_status(status.code, code_pb2.INVALID_ARGUMENT)
            self.assertEqual(len(row_counts), 1)
            self.assertEqual(row_counts[0], 1)

        session.run_in_transaction(unit_of_work)

    def test_transaction_batch_update_wo_statements(self):
        from google.api_core.exceptions import InvalidArgument

        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with session.transaction() as transaction:
            with self.assertRaises(InvalidArgument):
                transaction.batch_update([])

    def test_transaction_batch_update_w_parent_span(self):
        try:
            from opentelemetry import trace
        except ImportError:
            return

        tracer = trace.get_tracer(__name__)

        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        session = self._db.session()
        session.create()
        self.to_delete.append(session)

        with session.batch() as batch:
            batch.delete(self.TABLE, self.ALL)

        insert_statement = list(self._generate_insert_statements())[0]
        update_statement = (
            u"UPDATE contacts SET email = @email " u"WHERE contact_id = @contact_id;",
            {u"contact_id": 1, u"email": u"phreddy@example.com"},
            {u"contact_id": param_types.INT64, u"email": param_types.STRING},
        )
        delete_statement = (
            u"DELETE contacts WHERE contact_id = @contact_id;",
            {u"contact_id": 1},
            {u"contact_id": param_types.INT64},
        )

        def unit_of_work(transaction, self):

            status, row_counts = transaction.batch_update(
                [insert_statement, update_statement, delete_statement]
            )
            self._check_batch_status(status.code)
            self.assertEqual(len(row_counts), 3)
            for row_count in row_counts:
                self.assertEqual(row_count, 1)

        with tracer.start_as_current_span(u"Test Span"):
            session.run_in_transaction(unit_of_work, self)

        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 6)
        self.assertEqual(
            list(imap(lambda span: span.name, span_list)),
            [
                u"CloudSpanner.CreateSession",
                u"CloudSpanner.Commit",
                u"CloudSpanner.BeginTransaction",
                u"CloudSpanner.DMLTransaction",
                u"CloudSpanner.Commit",
                u"Test Span",
            ],
        )
        for span in span_list[2:-1]:
            self.assertEqual(span.context.trace_id, span_list[-1].context.trace_id)
            self.assertEqual(span.parent.span_id, span_list[-1].context.span_id)

    def test_execute_partitioned_dml(self):
        # [START spanner_test_dml_partioned_dml_update]
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        delete_statement = u"DELETE FROM {} WHERE true".format(self.TABLE)

        def _setup_table(txn):
            txn.execute_update(delete_statement)
            for insert_statement in self._generate_insert_statements():
                txn.execute_update(insert_statement)

        committed = self._db.run_in_transaction(_setup_table)

        with self._db.snapshot(read_timestamp=committed) as snapshot:
            before_pdml = list(snapshot.read(self.TABLE, self.COLUMNS, self.ALL))

        self._check_rows_data(before_pdml)

        nonesuch = u"nonesuch@example.com"
        target = u"phred@example.com"
        update_statement = (
            u"UPDATE {table} SET {table}.email = @email " u"WHERE {table}.email = @target"
        ).format(table=self.TABLE)

        row_count = self._db.execute_partitioned_dml(
            update_statement,
            params={u"email": nonesuch, u"target": target},
            param_types={u"email": param_types.STRING, u"target": param_types.STRING},
        )
        self.assertEqual(row_count, 1)

        row = self.ROW_DATA[0]
        updated = [row[:3] + (nonesuch,)] + list(self.ROW_DATA[1:])

        with self._db.snapshot(read_timestamp=committed) as snapshot:
            after_update = list(snapshot.read(self.TABLE, self.COLUMNS, self.ALL))
        self._check_rows_data(after_update, updated)

        row_count = self._db.execute_partitioned_dml(delete_statement)
        self.assertEqual(row_count, len(self.ROW_DATA))

        with self._db.snapshot(read_timestamp=committed) as snapshot:
            after_delete = list(snapshot.read(self.TABLE, self.COLUMNS, self.ALL))

        self._check_rows_data(after_delete, [])
        # [END spanner_test_dml_partioned_dml_update]

    def _transaction_concurrency_helper(self, unit_of_work, pkey):
        INITIAL_VALUE = 123
        NUM_THREADS = 3  # conforms to equivalent Java systest.

        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        with self._db.batch() as batch:
            batch.insert_or_update(
                COUNTERS_TABLE, COUNTERS_COLUMNS, [[pkey, INITIAL_VALUE]]
            )

        # We don't want to run the threads' transactions in the current
        # session, which would fail.
        txn_sessions = []

        for _ in xrange(NUM_THREADS):
            txn_sessions.append(self._db)

        threads = [
            threading.Thread(
                target=txn_session.run_in_transaction, args=(unit_of_work, pkey)
            )
            for txn_session in txn_sessions
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        with self._db.snapshot() as snapshot:
            keyset = KeySet(keys=[(pkey,)])
            rows = list(snapshot.read(COUNTERS_TABLE, COUNTERS_COLUMNS, keyset))
            self.assertEqual(len(rows), 1)
            _, value = rows[0]
            self.assertEqual(value, INITIAL_VALUE + len(threads))

    def _read_w_concurrent_update(self, transaction, pkey):
        keyset = KeySet(keys=[(pkey,)])
        rows = list(transaction.read(COUNTERS_TABLE, COUNTERS_COLUMNS, keyset))
        self.assertEqual(len(rows), 1)
        pkey, value = rows[0]
        transaction.update(COUNTERS_TABLE, COUNTERS_COLUMNS, [[pkey, value + 1]])

    def test_transaction_read_w_concurrent_updates(self):
        PKEY = u"read_w_concurrent_updates"
        self._transaction_concurrency_helper(self._read_w_concurrent_update, PKEY)

    def _query_w_concurrent_update(self, transaction, pkey):
        SQL = u"SELECT * FROM counters WHERE name = @name"
        rows = list(
            transaction.execute_sql(
                SQL, params={u"name": pkey}, param_types={u"name": param_types.STRING}
            )
        )
        self.assertEqual(len(rows), 1)
        pkey, value = rows[0]
        transaction.update(COUNTERS_TABLE, COUNTERS_COLUMNS, [[pkey, value + 1]])

    def test_transaction_query_w_concurrent_updates(self):
        PKEY = u"query_w_concurrent_updates"
        self._transaction_concurrency_helper(self._query_w_concurrent_update, PKEY)

    @unittest.skipIf(USE_EMULATOR, u"Skipping concurrent transactions")
    def test_transaction_read_w_abort(self):
        retry = RetryInstanceState(_has_all_ddl)
        retry(self._db.reload)()

        trigger = _ReadAbortTrigger()

        with self._db.batch() as batch:
            batch.delete(COUNTERS_TABLE, self.ALL)
            batch.insert(
                COUNTERS_TABLE, COUNTERS_COLUMNS, [[trigger.KEY1, 0], [trigger.KEY2, 0]]
            )

        provoker = threading.Thread(target=trigger.provoke_abort, args=(self._db,))
        handler = threading.Thread(target=trigger.handle_abort, args=(self._db,))

        provoker.start()
        trigger.provoker_started.wait()

        handler.start()
        trigger.handler_done.wait()

        provoker.join()
        handler.join()
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(COUNTERS_TABLE, COUNTERS_COLUMNS, self.ALL))
            self._check_row_data(rows, expected=[[trigger.KEY1, 1], [trigger.KEY2, 1]])

    @staticmethod
    def _row_data(max_index):
        for index in xrange(max_index):
            yield (
                index,
                u"First%09d" % (index,),
                u"Last%09d" % (max_index - index),
                u"test-%09d@example.com" % (index,),
            )

    def _set_up_table(self, row_count, database=None):
        if database is None:
            database = self._db
            retry = RetryInstanceState(_has_all_ddl)
            retry(database.reload)()

        def _unit_of_work(transaction, test):
            transaction.delete(test.TABLE, test.ALL)
            transaction.insert(test.TABLE, test.COLUMNS, test._row_data(row_count))

        committed = database.run_in_transaction(_unit_of_work, test=self)

        return committed

    def test_read_with_single_keys_index(self):
        # [START spanner_test_single_key_index_read]
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        self._set_up_table(row_count)

        expected = [[row[1], row[2]] for row in self._row_data(row_count)]
        row = 5
        keyset = [[expected[row][0], expected[row][1]]]
        with self._db.snapshot() as snapshot:
            results_iter = snapshot.read(
                self.TABLE, columns, KeySet(keys=keyset), index=u"name"
            )
            rows = list(results_iter)
            self.assertEqual(rows, [expected[row]])
        # [END spanner_test_single_key_index_read]

    def test_empty_read_with_single_keys_index(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        self._set_up_table(row_count)
        keyset = [[u"Non", u"Existent"]]
        with self._db.snapshot() as snapshot:
            results_iter = snapshot.read(
                self.TABLE, columns, KeySet(keys=keyset), index=u"name"
            )
            rows = list(results_iter)
            self.assertEqual(rows, [])

    def test_read_with_multiple_keys_index(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        self._set_up_table(row_count)
        expected = [[row[1], row[2]] for row in self._row_data(row_count)]
        with self._db.snapshot() as snapshot:
            rows = list(
                snapshot.read(self.TABLE, columns, KeySet(keys=expected), index=u"name")
            )
            self.assertEqual(rows, expected)

    def test_snapshot_read_w_various_staleness(self):
        from datetime import datetime
        from google.cloud._helpers import UTC

        ROW_COUNT = 400
        committed = self._set_up_table(ROW_COUNT)
        all_data_rows = list(self._row_data(ROW_COUNT))

        before_reads = datetime.utcnow().replace(tzinfo=UTC)

        # Test w/ read timestamp
        with self._db.snapshot(read_timestamp=committed) as read_tx:
            rows = list(read_tx.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(rows, all_data_rows)

        # Test w/ min read timestamp
        with self._db.snapshot(min_read_timestamp=committed) as min_read_ts:
            rows = list(min_read_ts.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(rows, all_data_rows)

        staleness = datetime.utcnow().replace(tzinfo=UTC) - before_reads

        # Test w/ max staleness
        with self._db.snapshot(max_staleness=staleness) as max_staleness:
            rows = list(max_staleness.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(rows, all_data_rows)

        # Test w/ exact staleness
        with self._db.snapshot(exact_staleness=staleness) as exact_staleness:
            rows = list(exact_staleness.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(rows, all_data_rows)

        # Test w/ strong
        with self._db.snapshot() as strong:
            rows = list(strong.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(rows, all_data_rows)

    def test_multiuse_snapshot_read_isolation_strong(self):
        ROW_COUNT = 40
        self._set_up_table(ROW_COUNT)
        all_data_rows = list(self._row_data(ROW_COUNT))
        with self._db.snapshot(multi_use=True) as strong:
            before = list(strong.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(before, all_data_rows)

            with self._db.batch() as batch:
                batch.delete(self.TABLE, self.ALL)

            after = list(strong.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(after, all_data_rows)

    def test_multiuse_snapshot_read_isolation_read_timestamp(self):
        ROW_COUNT = 40
        committed = self._set_up_table(ROW_COUNT)
        all_data_rows = list(self._row_data(ROW_COUNT))

        with self._db.snapshot(read_timestamp=committed, multi_use=True) as read_ts:

            before = list(read_ts.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(before, all_data_rows)

            with self._db.batch() as batch:
                batch.delete(self.TABLE, self.ALL)

            after = list(read_ts.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(after, all_data_rows)

    def test_multiuse_snapshot_read_isolation_exact_staleness(self):
        ROW_COUNT = 40

        self._set_up_table(ROW_COUNT)
        all_data_rows = list(self._row_data(ROW_COUNT))

        time.sleep(1)
        delta = datetime.timedelta(microseconds=1000)

        with self._db.snapshot(exact_staleness=delta, multi_use=True) as exact:

            before = list(exact.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(before, all_data_rows)

            with self._db.batch() as batch:
                batch.delete(self.TABLE, self.ALL)

            after = list(exact.read(self.TABLE, self.COLUMNS, self.ALL))
            self._check_row_data(after, all_data_rows)

    def test_read_w_index(self):
        ROW_COUNT = 2000
        # Indexed reads cannot return non-indexed columns
        MY_COLUMNS = self.COLUMNS[0], self.COLUMNS[2]
        EXTRA_DDL = [u"CREATE INDEX contacts_by_last_name ON contacts(last_name)"]
        pool = BurstyPool(labels={u"testcase": u"read_w_index"})
        ddl_statements = EMULATOR_DDL_STATEMENTS if USE_EMULATOR else DDL_STATEMENTS
        temp_db = Config.INSTANCE.database(
            u"test_read" + unique_resource_id(u"_"),
            ddl_statements=ddl_statements + EXTRA_DDL,
            pool=pool,
        )
        operation = temp_db.create()
        self.to_delete.append(_DatabaseDropper(temp_db))

        # We want to make sure the operation completes.
        operation.result(30)  # raises on failure / timeout.
        committed = self._set_up_table(ROW_COUNT, database=temp_db)

        with temp_db.snapshot(read_timestamp=committed) as snapshot:
            rows = list(
                snapshot.read(
                    self.TABLE, MY_COLUMNS, self.ALL, index=u"contacts_by_last_name"
                )
            )

        expected = list(
            reversed([(row[0], row[2]) for row in self._row_data(ROW_COUNT)])
        )
        self._check_rows_data(rows, expected)

    def test_read_w_single_key(self):
        # [START spanner_test_single_key_read]
        ROW_COUNT = 40
        committed = self._set_up_table(ROW_COUNT)

        with self._db.snapshot(read_timestamp=committed) as snapshot:
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, KeySet(keys=[(0,)])))

        all_data_rows = list(self._row_data(ROW_COUNT))
        expected = [all_data_rows[0]]
        self._check_row_data(rows, expected)
        # [END spanner_test_single_key_read]

    def test_empty_read(self):
        # [START spanner_test_empty_read]
        ROW_COUNT = 40
        self._set_up_table(ROW_COUNT)
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, KeySet(keys=[(40,)])))
        self._check_row_data(rows, [])
        # [END spanner_test_empty_read]

    def test_read_w_multiple_keys(self):
        ROW_COUNT = 40
        indices = [0, 5, 17]
        committed = self._set_up_table(ROW_COUNT)

        with self._db.snapshot(read_timestamp=committed) as snapshot:
            rows = list(
                snapshot.read(
                    self.TABLE,
                    self.COLUMNS,
                    KeySet(keys=[(index,) for index in indices]),
                )
            )

        all_data_rows = list(self._row_data(ROW_COUNT))
        expected = [row for row in all_data_rows if row[0] in indices]
        self._check_row_data(rows, expected)

    def test_read_w_limit(self):
        ROW_COUNT = 3000
        LIMIT = 100
        committed = self._set_up_table(ROW_COUNT)

        with self._db.snapshot(read_timestamp=committed) as snapshot:
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, self.ALL, limit=LIMIT))

        all_data_rows = list(self._row_data(ROW_COUNT))
        expected = all_data_rows[:LIMIT]
        self._check_row_data(rows, expected)

    def test_read_w_ranges(self):
        ROW_COUNT = 3000
        START = 1000
        END = 2000
        committed = self._set_up_table(ROW_COUNT)
        with self._db.snapshot(read_timestamp=committed, multi_use=True) as snapshot:
            all_data_rows = list(self._row_data(ROW_COUNT))

            single_key = KeyRange(start_closed=[START], end_open=[START + 1])
            keyset = KeySet(ranges=(single_key,))
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, keyset))
            expected = all_data_rows[START : START + 1]
            self._check_rows_data(rows, expected)

            closed_closed = KeyRange(start_closed=[START], end_closed=[END])
            keyset = KeySet(ranges=(closed_closed,))
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, keyset))
            expected = all_data_rows[START : END + 1]
            self._check_row_data(rows, expected)

            closed_open = KeyRange(start_closed=[START], end_open=[END])
            keyset = KeySet(ranges=(closed_open,))
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, keyset))
            expected = all_data_rows[START:END]
            self._check_row_data(rows, expected)

            open_open = KeyRange(start_open=[START], end_open=[END])
            keyset = KeySet(ranges=(open_open,))
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, keyset))
            expected = all_data_rows[START + 1 : END]
            self._check_row_data(rows, expected)

            open_closed = KeyRange(start_open=[START], end_closed=[END])
            keyset = KeySet(ranges=(open_closed,))
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, keyset))
            expected = all_data_rows[START + 1 : END + 1]
            self._check_row_data(rows, expected)

    def test_read_partial_range_until_end(self):
        row_count = 3000
        start = 1000
        committed = self._set_up_table(row_count)
        with self._db.snapshot(read_timestamp=committed, multi_use=True) as snapshot:
            all_data_rows = list(self._row_data(row_count))

            expected_map = {
                (u"start_closed", u"end_closed"): all_data_rows[start:],
                (u"start_closed", u"end_open"): [],
                (u"start_open", u"end_closed"): all_data_rows[start + 1 :],
                (u"start_open", u"end_open"): [],
            }
            for start_arg in (u"start_closed", u"start_open"):
                for end_arg in (u"end_closed", u"end_open"):
                    range_kwargs = {start_arg: [start], end_arg: []}
                    keyset = KeySet(ranges=(KeyRange(**range_kwargs),))

                    rows = list(snapshot.read(self.TABLE, self.COLUMNS, keyset))
                    expected = expected_map[(start_arg, end_arg)]
                    self._check_row_data(rows, expected)

    def test_read_partial_range_from_beginning(self):
        row_count = 3000
        end = 2000
        committed = self._set_up_table(row_count)

        all_data_rows = list(self._row_data(row_count))

        expected_map = {
            (u"start_closed", u"end_closed"): all_data_rows[: end + 1],
            (u"start_closed", u"end_open"): all_data_rows[:end],
            (u"start_open", u"end_closed"): [],
            (u"start_open", u"end_open"): [],
        }
        for start_arg in (u"start_closed", u"start_open"):
            for end_arg in (u"end_closed", u"end_open"):
                range_kwargs = {start_arg: [], end_arg: [end]}
                keyset = KeySet(ranges=(KeyRange(**range_kwargs),))
        with self._db.snapshot(read_timestamp=committed, multi_use=True) as snapshot:
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, keyset))
            expected = expected_map[(start_arg, end_arg)]
            self._check_row_data(rows, expected)

    def test_read_with_range_keys_index_single_key(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        self._set_up_table(row_count)
        start = 3
        krange = KeyRange(start_closed=data[start], end_open=data[start + 1])
        keyset = KeySet(ranges=(krange,))
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, columns, keyset, index=u"name"))
            self.assertEqual(rows, data[start : start + 1])

    def test_read_with_range_keys_index_closed_closed(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        self._set_up_table(row_count)
        start, end = 3, 7
        krange = KeyRange(start_closed=data[start], end_closed=data[end])
        keyset = KeySet(ranges=(krange,))
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, columns, keyset, index=u"name"))
            self.assertEqual(rows, data[start : end + 1])

    def test_read_with_range_keys_index_closed_open(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        self._set_up_table(row_count)
        start, end = 3, 7
        krange = KeyRange(start_closed=data[start], end_open=data[end])
        keyset = KeySet(ranges=(krange,))
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, columns, keyset, index=u"name"))
            self.assertEqual(rows, data[start:end])

    def test_read_with_range_keys_index_open_closed(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        self._set_up_table(row_count)
        start, end = 3, 7
        krange = KeyRange(start_open=data[start], end_closed=data[end])
        keyset = KeySet(ranges=(krange,))
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, columns, keyset, index=u"name"))
            self.assertEqual(rows, data[start + 1 : end + 1])

    def test_read_with_range_keys_index_open_open(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        self._set_up_table(row_count)
        start, end = 3, 7
        krange = KeyRange(start_open=data[start], end_open=data[end])
        keyset = KeySet(ranges=(krange,))
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, columns, keyset, index=u"name"))
            self.assertEqual(rows, data[start + 1 : end])

    def test_read_with_range_keys_index_limit_closed_closed(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        self._set_up_table(row_count)
        start, end, limit = 3, 7, 2
        krange = KeyRange(start_closed=data[start], end_closed=data[end])
        keyset = KeySet(ranges=(krange,))
        with self._db.snapshot() as snapshot:
            rows = list(
                snapshot.read(self.TABLE, columns, keyset, index=u"name", limit=limit)
            )
            expected = data[start : end + 1]
            self.assertEqual(rows, expected[:limit])

    def test_read_with_range_keys_index_limit_closed_open(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        self._set_up_table(row_count)
        start, end, limit = 3, 7, 2
        krange = KeyRange(start_closed=data[start], end_open=data[end])
        keyset = KeySet(ranges=(krange,))
        with self._db.snapshot() as snapshot:
            rows = list(
                snapshot.read(self.TABLE, columns, keyset, index=u"name", limit=limit)
            )
            expected = data[start:end]
            self.assertEqual(rows, expected[:limit])

    def test_read_with_range_keys_index_limit_open_closed(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        self._set_up_table(row_count)
        start, end, limit = 3, 7, 2
        krange = KeyRange(start_open=data[start], end_closed=data[end])
        keyset = KeySet(ranges=(krange,))
        with self._db.snapshot() as snapshot:
            rows = list(
                snapshot.read(self.TABLE, columns, keyset, index=u"name", limit=limit)
            )
            expected = data[start + 1 : end + 1]
            self.assertEqual(rows, expected[:limit])

    def test_read_with_range_keys_index_limit_open_open(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        self._set_up_table(row_count)
        start, end, limit = 3, 7, 2
        krange = KeyRange(start_open=data[start], end_open=data[end])
        keyset = KeySet(ranges=(krange,))
        with self._db.snapshot() as snapshot:
            rows = list(
                snapshot.read(self.TABLE, columns, keyset, index=u"name", limit=limit)
            )
            expected = data[start + 1 : end]
            self.assertEqual(rows, expected[:limit])

    def test_read_with_range_keys_and_index_closed_closed(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]

        self._set_up_table(row_count)
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        keyrow, start, end = 1, 3, 7
        closed_closed = KeyRange(start_closed=data[start], end_closed=data[end])
        keys = [data[keyrow]]
        keyset = KeySet(keys=keys, ranges=(closed_closed,))
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, columns, keyset, index=u"name"))
            expected = [data[keyrow]] + data[start : end + 1]
            self.assertEqual(rows, expected)

    def test_read_with_range_keys_and_index_closed_open(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        self._set_up_table(row_count)
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        keyrow, start, end = 1, 3, 7
        closed_open = KeyRange(start_closed=data[start], end_open=data[end])
        keys = [data[keyrow]]
        keyset = KeySet(keys=keys, ranges=(closed_open,))
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, columns, keyset, index=u"name"))
            expected = [data[keyrow]] + data[start:end]
            self.assertEqual(rows, expected)

    def test_read_with_range_keys_and_index_open_closed(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        self._set_up_table(row_count)
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        keyrow, start, end = 1, 3, 7
        open_closed = KeyRange(start_open=data[start], end_closed=data[end])
        keys = [data[keyrow]]
        keyset = KeySet(keys=keys, ranges=(open_closed,))
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, columns, keyset, index=u"name"))
            expected = [data[keyrow]] + data[start + 1 : end + 1]
            self.assertEqual(rows, expected)

    def test_read_with_range_keys_and_index_open_open(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        self._set_up_table(row_count)
        data = [[row[1], row[2]] for row in self._row_data(row_count)]
        keyrow, start, end = 1, 3, 7
        open_open = KeyRange(start_open=data[start], end_open=data[end])
        keys = [data[keyrow]]
        keyset = KeySet(keys=keys, ranges=(open_open,))
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.read(self.TABLE, columns, keyset, index=u"name"))
            expected = [data[keyrow]] + data[start + 1 : end]
            self.assertEqual(rows, expected)

    def test_partition_read_w_index(self):
        row_count = 10
        columns = self.COLUMNS[1], self.COLUMNS[2]
        committed = self._set_up_table(row_count)

        expected = [[row[1], row[2]] for row in self._row_data(row_count)]
        union = []

        batch_txn = self._db.batch_snapshot(read_timestamp=committed)
        batches = batch_txn.generate_read_batches(
            self.TABLE, columns, KeySet(all_=True), index=u"name"
        )
        for batch in batches:
            p_results_iter = batch_txn.process(batch)
            union.extend(list(p_results_iter))

        self.assertEqual(union, expected)
        batch_txn.close()

    def test_execute_sql_w_manual_consume(self):
        ROW_COUNT = 3000
        committed = self._set_up_table(ROW_COUNT)

        with self._db.snapshot(read_timestamp=committed) as snapshot:
            streamed = snapshot.execute_sql(self.SQL)

        keyset = KeySet(all_=True)
        with self._db.snapshot(read_timestamp=committed) as snapshot:
            rows = list(snapshot.read(self.TABLE, self.COLUMNS, keyset))
        self.assertEqual(list(streamed), rows)
        self.assertEqual(streamed._current_row, [])
        self.assertEqual(streamed._pending_chunk, None)

    def _check_sql_results(
        self, database, sql, params, param_types, expected, order=True
    ):
        if order and u"ORDER" not in sql:
            sql += u" ORDER BY pkey"
        with database.snapshot() as snapshot:
            rows = list(
                snapshot.execute_sql(sql, params=params, param_types=param_types)
            )
        self._check_rows_data(rows, expected=expected)

    def test_multiuse_snapshot_execute_sql_isolation_strong(self):
        ROW_COUNT = 40
        self._set_up_table(ROW_COUNT)
        all_data_rows = list(self._row_data(ROW_COUNT))
        with self._db.snapshot(multi_use=True) as strong:

            before = list(strong.execute_sql(self.SQL))
            self._check_row_data(before, all_data_rows)

            with self._db.batch() as batch:
                batch.delete(self.TABLE, self.ALL)

            after = list(strong.execute_sql(self.SQL))
            self._check_row_data(after, all_data_rows)

    def test_execute_sql_returning_array_of_struct(self):
        SQL = (
            u"SELECT ARRAY(SELECT AS STRUCT C1, C2 "
            u"FROM (SELECT 'a' AS C1, 1 AS C2 "
            u"UNION ALL SELECT 'b' AS C1, 2 AS C2) "
            u"ORDER BY C1 ASC)"
        )
        self._check_sql_results(
            self._db,
            sql=SQL,
            params=None,
            param_types=None,
            expected=[[[[u"a", 1], [u"b", 2]]]],
        )

    def test_execute_sql_returning_empty_array_of_struct(self):
        SQL = (
            u"SELECT ARRAY(SELECT AS STRUCT C1, C2 "
            u"FROM (SELECT 2 AS C1) X "
            u"JOIN (SELECT 1 AS C2) Y "
            u"ON X.C1 = Y.C2 "
            u"ORDER BY C1 ASC)"
        )
        self._db.snapshot(multi_use=True)

        self._check_sql_results(
            self._db, sql=SQL, params=None, param_types=None, expected=[[[]]]
        )

    def test_invalid_type(self):
        table = u"counters"
        columns = (u"name", u"value")

        valid_input = ((u"", 0),)
        with self._db.batch() as batch:
            batch.delete(table, self.ALL)
            batch.insert(table, columns, valid_input)

        invalid_input = ((0, u""),)
        with self.assertRaises(exceptions.FailedPrecondition):
            with self._db.batch() as batch:
                batch.delete(table, self.ALL)
                batch.insert(table, columns, invalid_input)

    def test_execute_sql_select_1(self):

        self._db.snapshot(multi_use=True)

        # Hello, world query
        self._check_sql_results(
            self._db,
            sql=u"SELECT 1",
            params=None,
            param_types=None,
            expected=[(1,)],
            order=False,
        )

    def _bind_test_helper(
        self, type_name, single_value, array_value, expected_array_value=None
    ):

        self._db.snapshot(multi_use=True)

        # Bind a non-null <type_name>
        self._check_sql_results(
            self._db,
            sql=u"SELECT @v",
            params={u"v": single_value},
            param_types={u"v": Type(code=type_name)},
            expected=[(single_value,)],
            order=False,
        )

        # Bind a null <type_name>
        self._check_sql_results(
            self._db,
            sql=u"SELECT @v",
            params={u"v": None},
            param_types={u"v": Type(code=type_name)},
            expected=[(None,)],
            order=False,
        )

        # Bind an array of <type_name>
        array_type = Type(code=TypeCode.ARRAY, array_element_type=Type(code=type_name))

        if expected_array_value is None:
            expected_array_value = array_value

        self._check_sql_results(
            self._db,
            sql=u"SELECT @v",
            params={u"v": array_value},
            param_types={u"v": array_type},
            expected=[(expected_array_value,)],
            order=False,
        )

        # Bind an empty array of <type_name>
        self._check_sql_results(
            self._db,
            sql=u"SELECT @v",
            params={u"v": []},
            param_types={u"v": array_type},
            expected=[([],)],
            order=False,
        )

        # Bind a null array of <type_name>
        self._check_sql_results(
            self._db,
            sql=u"SELECT @v",
            params={u"v": None},
            param_types={u"v": array_type},
            expected=[(None,)],
            order=False,
        )

    def test_execute_sql_w_string_bindings(self):
        self._bind_test_helper(TypeCode.STRING, u"Phred", [u"Phred", u"Bharney"])

    def test_execute_sql_w_bool_bindings(self):
        self._bind_test_helper(TypeCode.BOOL, True, [True, False, True])

    def test_execute_sql_w_int64_bindings(self):
        self._bind_test_helper(TypeCode.INT64, 42, [123, 456, 789])

    def test_execute_sql_w_float64_bindings(self):
        self._bind_test_helper(TypeCode.FLOAT64, 42.3, [12.3, 456.0, 7.89])

    def test_execute_sql_w_float_bindings_transfinite(self):

        # Find -inf
        self._check_sql_results(
            self._db,
            sql=u"SELECT @neg_inf",
            params={u"neg_inf": NEG_INF},
            param_types={u"neg_inf": param_types.FLOAT64},
            expected=[(NEG_INF,)],
            order=False,
        )

        # Find +inf
        self._check_sql_results(
            self._db,
            sql=u"SELECT @pos_inf",
            params={u"pos_inf": POS_INF},
            param_types={u"pos_inf": param_types.FLOAT64},
            expected=[(POS_INF,)],
            order=False,
        )

    def test_execute_sql_w_bytes_bindings(self):
        self._bind_test_helper(TypeCode.BYTES, "DEADBEEF", ["FACEDACE", "DEADBEEF"])

    def test_execute_sql_w_timestamp_bindings(self):
        import pytz
        from google.api_core.datetime_helpers import DatetimeWithNanoseconds

        timestamp_1 = DatetimeWithNanoseconds(
            1989, 1, 17, 17, 59, 12, nanosecond=345612789
        )

        timestamp_2 = DatetimeWithNanoseconds(
            1989, 1, 17, 17, 59, 13, nanosecond=456127893
        )

        timestamps = [timestamp_1, timestamp_2]

        # In round-trip, timestamps acquire a timezone value.
        expected_timestamps = [
            timestamp.replace(tzinfo=pytz.UTC) for timestamp in timestamps
        ]

        self._recurse_into_lists = False
        self._bind_test_helper(
            TypeCode.TIMESTAMP, timestamp_1, timestamps, expected_timestamps
        )

    def test_execute_sql_w_date_bindings(self):
        import datetime

        dates = [SOME_DATE, SOME_DATE + datetime.timedelta(days=1)]
        self._bind_test_helper(TypeCode.DATE, SOME_DATE, dates)

    @unittest.skipIf(USE_EMULATOR, u"Skipping NUMERIC")
    def test_execute_sql_w_numeric_bindings(self):
        self._bind_test_helper(TypeCode.NUMERIC, NUMERIC_1, [NUMERIC_1, NUMERIC_2])

    def test_execute_sql_w_query_param_struct(self):
        NAME = u"Phred"
        COUNT = 123
        SIZE = 23.456
        HEIGHT = 188.0
        WEIGHT = 97.6

        record_type = param_types.Struct(
            [
                param_types.StructField(u"name", param_types.STRING),
                param_types.StructField(u"count", param_types.INT64),
                param_types.StructField(u"size", param_types.FLOAT64),
                param_types.StructField(
                    u"nested",
                    param_types.Struct(
                        [
                            param_types.StructField(u"height", param_types.FLOAT64),
                            param_types.StructField(u"weight", param_types.FLOAT64),
                        ]
                    ),
                ),
            ]
        )

        # Query with null struct, explicit type
        self._check_sql_results(
            self._db,
            sql=u"SELECT @r.name, @r.count, @r.size, @r.nested.weight",
            params={u"r": None},
            param_types={u"r": record_type},
            expected=[(None, None, None, None)],
            order=False,
        )

        # Query with non-null struct, explicit type, NULL values
        self._check_sql_results(
            self._db,
            sql=u"SELECT @r.name, @r.count, @r.size, @r.nested.weight",
            params={u"r": (None, None, None, None)},
            param_types={u"r": record_type},
            expected=[(None, None, None, None)],
            order=False,
        )

        # Query with non-null struct, explicit type, nested NULL values
        self._check_sql_results(
            self._db,
            sql=u"SELECT @r.nested.weight",
            params={u"r": (None, None, None, (None, None))},
            param_types={u"r": record_type},
            expected=[(None,)],
            order=False,
        )

        # Query with non-null struct, explicit type
        self._check_sql_results(
            self._db,
            sql=u"SELECT @r.name, @r.count, @r.size, @r.nested.weight",
            params={u"r": (NAME, COUNT, SIZE, (HEIGHT, WEIGHT))},
            param_types={u"r": record_type},
            expected=[(NAME, COUNT, SIZE, WEIGHT)],
            order=False,
        )

        # Query with empty struct, explicitly empty type
        empty_type = param_types.Struct([])
        self._check_sql_results(
            self._db,
            sql=u"SELECT @r IS NULL",
            params={u"r": ()},
            param_types={u"r": empty_type},
            expected=[(False,)],
            order=False,
        )

        # Query with null struct, explicitly empty type
        self._check_sql_results(
            self._db,
            sql=u"SELECT @r IS NULL",
            params={u"r": None},
            param_types={u"r": empty_type},
            expected=[(True,)],
            order=False,
        )

        # Query with equality check for struct value
        struct_equality_query = (
            u"SELECT " u'@struct_param=STRUCT<threadf INT64, userf STRING>(1,"bob")'
        )
        struct_type = param_types.Struct(
            [
                param_types.StructField(u"threadf", param_types.INT64),
                param_types.StructField(u"userf", param_types.STRING),
            ]
        )
        self._check_sql_results(
            self._db,
            sql=struct_equality_query,
            params={u"struct_param": (1, u"bob")},
            param_types={u"struct_param": struct_type},
            expected=[(True,)],
            order=False,
        )

        # Query with nullness test for struct
        self._check_sql_results(
            self._db,
            sql=u"SELECT @struct_param IS NULL",
            params={u"struct_param": None},
            param_types={u"struct_param": struct_type},
            expected=[(True,)],
            order=False,
        )

        # Query with null array-of-struct
        array_elem_type = param_types.Struct(
            [param_types.StructField(u"threadid", param_types.INT64)]
        )
        array_type = param_types.Array(array_elem_type)
        self._check_sql_results(
            self._db,
            sql=u"SELECT a.threadid FROM UNNEST(@struct_arr_param) a",
            params={u"struct_arr_param": None},
            param_types={u"struct_arr_param": array_type},
            expected=[],
            order=False,
        )

        # Query with non-null array-of-struct
        self._check_sql_results(
            self._db,
            sql=u"SELECT a.threadid FROM UNNEST(@struct_arr_param) a",
            params={u"struct_arr_param": [(123,), (456,)]},
            param_types={u"struct_arr_param": array_type},
            expected=[(123,), (456,)],
            order=False,
        )

        # Query with null array-of-struct field
        struct_type_with_array_field = param_types.Struct(
            [
                param_types.StructField(u"intf", param_types.INT64),
                param_types.StructField(u"arraysf", array_type),
            ]
        )
        self._check_sql_results(
            self._db,
            sql=u"SELECT a.threadid FROM UNNEST(@struct_param.arraysf) a",
            params={u"struct_param": (123, None)},
            param_types={u"struct_param": struct_type_with_array_field},
            expected=[],
            order=False,
        )

        # Query with non-null array-of-struct field
        self._check_sql_results(
            self._db,
            sql=u"SELECT a.threadid FROM UNNEST(@struct_param.arraysf) a",
            params={u"struct_param": (123, ((456,), (789,)))},
            param_types={u"struct_param": struct_type_with_array_field},
            expected=[(456,), (789,)],
            order=False,
        )

        # Query with anonymous / repeated-name fields
        anon_repeated_array_elem_type = param_types.Struct(
            [
                param_types.StructField(u"", param_types.INT64),
                param_types.StructField(u"", param_types.STRING),
            ]
        )
        anon_repeated_array_type = param_types.Array(anon_repeated_array_elem_type)
        self._check_sql_results(
            self._db,
            sql=u"SELECT CAST(t as STRUCT<threadid INT64, userid STRING>).* "
            u"FROM UNNEST(@struct_param) t",
            params={u"struct_param": [(123, u"abcdef")]},
            param_types={u"struct_param": anon_repeated_array_type},
            expected=[(123, u"abcdef")],
            order=False,
        )

        # Query and return a struct parameter
        value_type = param_types.Struct(
            [
                param_types.StructField(u"message", param_types.STRING),
                param_types.StructField(u"repeat", param_types.INT64),
            ]
        )
        value_query = (
            u"SELECT ARRAY(SELECT AS STRUCT message, repeat "
            u"FROM (SELECT @value.message AS message, "
            u"@value.repeat AS repeat)) AS value"
        )
        self._check_sql_results(
            self._db,
            sql=value_query,
            params={u"value": (u"hello", 1)},
            param_types={u"value": value_type},
            expected=[([[u"hello", 1]],)],
            order=False,
        )

    def test_execute_sql_returning_transfinite_floats(self):

        with self._db.snapshot(multi_use=True) as snapshot:
            # Query returning -inf, +inf, NaN as column values
            rows = list(
                snapshot.execute_sql(
                    u"SELECT "
                    u'CAST("-inf" AS FLOAT64), '
                    u'CAST("+inf" AS FLOAT64), '
                    u'CAST("NaN" AS FLOAT64)'
                )
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], float(u"-inf"))
            self.assertEqual(rows[0][1], float(u"+inf"))
            # NaNs cannot be compared by equality.
            self.assertTrue(math.isnan(rows[0][2]))

            # Query returning array of -inf, +inf, NaN as one column
            rows = list(
                snapshot.execute_sql(
                    u"SELECT"
                    u' [CAST("-inf" AS FLOAT64),'
                    u' CAST("+inf" AS FLOAT64),'
                    u' CAST("NaN" AS FLOAT64)]'
                )
            )
            self.assertEqual(len(rows), 1)
            float_array = rows[0][0]
            self.assertEqual(float_array[0], float(u"-inf"))
            self.assertEqual(float_array[1], float(u"+inf"))
            # NaNs cannot be searched for by equality.
            self.assertTrue(math.isnan(float_array[2]))

    def test_partition_query(self):
        row_count = 40
        sql = u"SELECT * FROM {}".format(self.TABLE)
        committed = self._set_up_table(row_count)

        # Paritioned query does not support ORDER BY
        all_data_rows = set(self._row_data(row_count))
        union = set()
        batch_txn = self._db.batch_snapshot(read_timestamp=committed)
        for batch in batch_txn.generate_query_batches(sql):
            p_results_iter = batch_txn.process(batch)
            # Lists aren't hashable so the results need to be converted
            rows = [tuple(result) for result in p_results_iter]
            union.update(set(rows))

        self.assertEqual(union, all_data_rows)
        batch_txn.close()


class TestStreamingChunking(unittest.TestCase, _TestData):
    @classmethod
    def setUpClass(cls):
        from tests.system.utils.streaming_utils import INSTANCE_NAME
        from tests.system.utils.streaming_utils import DATABASE_NAME

        instance = Config.CLIENT.instance(INSTANCE_NAME)
        if not instance.exists():
            raise unittest.SkipTest(
                u"Run 'tests/system/utils/populate_streaming.py' to enable."
            )

        database = instance.database(DATABASE_NAME)
        if not instance.exists():
            raise unittest.SkipTest(
                u"Run 'tests/system/utils/populate_streaming.py' to enable."
            )

        cls._db = database

    def _verify_one_column(self, table_desc):
        sql = u"SELECT chunk_me FROM {}".format(table_desc.table)
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.execute_sql(sql))
        self.assertEqual(len(rows), table_desc.row_count)
        expected = table_desc.value()
        for row in rows:
            self.assertEqual(row[0], expected)

    def _verify_two_columns(self, table_desc):
        sql = u"SELECT chunk_me, chunk_me_2 FROM {}".format(table_desc.table)
        with self._db.snapshot() as snapshot:
            rows = list(snapshot.execute_sql(sql))
        self.assertEqual(len(rows), table_desc.row_count)
        expected = table_desc.value()
        for row in rows:
            self.assertEqual(row[0], expected)
            self.assertEqual(row[1], expected)

    def test_four_kay(self):
        from tests.system.utils.streaming_utils import FOUR_KAY

        self._verify_one_column(FOUR_KAY)

    def test_forty_kay(self):
        from tests.system.utils.streaming_utils import FORTY_KAY

        self._verify_one_column(FORTY_KAY)

    def test_four_hundred_kay(self):
        from tests.system.utils.streaming_utils import FOUR_HUNDRED_KAY

        self._verify_one_column(FOUR_HUNDRED_KAY)

    def test_four_meg(self):
        from tests.system.utils.streaming_utils import FOUR_MEG

        self._verify_two_columns(FOUR_MEG)


class CustomException(Exception):
    u"""Placeholder for any user-defined exception."""


class _DatabaseDropper(object):
    u"""Helper for cleaning up databases created on-the-fly."""

    def __init__(self, db):
        self._db = db

    def delete(self):
        self._db.drop()


class _ReadAbortTrigger(object):
    u"""Helper for tests provoking abort-during-read."""

    KEY1 = u"key1"
    KEY2 = u"key2"

    def __init__(self):
        self.provoker_started = threading.Event()
        self.provoker_done = threading.Event()
        self.handler_running = threading.Event()
        self.handler_done = threading.Event()

    def _provoke_abort_unit_of_work(self, transaction):
        keyset = KeySet(keys=[(self.KEY1,)])
        rows = list(transaction.read(COUNTERS_TABLE, COUNTERS_COLUMNS, keyset))

        assert len(rows) == 1
        row = rows[0]
        value = row[1]

        self.provoker_started.set()

        self.handler_running.wait()

        transaction.update(COUNTERS_TABLE, COUNTERS_COLUMNS, [[self.KEY1, value + 1]])

    def provoke_abort(self, database):
        database.run_in_transaction(self._provoke_abort_unit_of_work)
        self.provoker_done.set()

    def _handle_abort_unit_of_work(self, transaction):
        keyset_1 = KeySet(keys=[(self.KEY1,)])
        rows_1 = list(transaction.read(COUNTERS_TABLE, COUNTERS_COLUMNS, keyset_1))

        assert len(rows_1) == 1
        row_1 = rows_1[0]
        value_1 = row_1[1]

        self.handler_running.set()

        self.provoker_done.wait()

        keyset_2 = KeySet(keys=[(self.KEY2,)])
        rows_2 = list(transaction.read(COUNTERS_TABLE, COUNTERS_COLUMNS, keyset_2))

        assert len(rows_2) == 1
        row_2 = rows_2[0]
        value_2 = row_2[1]

        transaction.update(
            COUNTERS_TABLE, COUNTERS_COLUMNS, [[self.KEY2, value_1 + value_2]]
        )

    def handle_abort(self, database):
        database.run_in_transaction(self._handle_abort_unit_of_work)
        self.handler_done.set()


class FauxCall(object):
    def __init__(self, code, details=u"FauxCall"):
        self._code = code
        self._details = details

    def initial_metadata(self):
        return {}

    def trailing_metadata(self):
        return {}

    def code(self):
        return self._code

    def details(self):
        return self._details
