#!/usr/bin/env python

# Copyright 2016 Google, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

u"""This application demonstrates how to do basic operations using Cloud
Spanner.

For more information, see the README.rst under /spanner.
"""

from __future__ import with_statement
from __future__ import absolute_import
import argparse
import base64
import datetime
import decimal

from google.cloud import spanner
from google.cloud.spanner_v1 import param_types


# [START spanner_create_instance]
def create_instance(instance_id):
    u"""Creates an instance."""
    spanner_client = spanner.Client()

    config_name = u"{}/instanceConfigs/regional-us-central1".format(
        spanner_client.project_name
    )

    instance = spanner_client.instance(
        instance_id,
        configuration_name=config_name,
        display_name=u"This is a display name.",
        node_count=1,
    )

    operation = instance.create()

    print u"Waiting for operation to complete..."
    operation.result(120)

    print u"Created instance {}".format(instance_id)


# [END spanner_create_instance]


# [START spanner_create_database]
def create_database(instance_id, database_id):
    u"""Creates a database and tables for sample data."""
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)

    database = instance.database(
        database_id,
        ddl_statements=[
            u"""CREATE TABLE Singers (
            SingerId     INT64 NOT NULL,
            FirstName    STRING(1024),
            LastName     STRING(1024),
            SingerInfo   BYTES(MAX)
        ) PRIMARY KEY (SingerId)""",
            u"""CREATE TABLE Albums (
            SingerId     INT64 NOT NULL,
            AlbumId      INT64 NOT NULL,
            AlbumTitle   STRING(MAX)
        ) PRIMARY KEY (SingerId, AlbumId),
        INTERLEAVE IN PARENT Singers ON DELETE CASCADE""",
        ],
    )

    operation = database.create()

    print u"Waiting for operation to complete..."
    operation.result(120)

    print u"Created database {} on instance {}".format(database_id, instance_id)


# [END spanner_create_database]


# [START spanner_insert_data]
def insert_data(instance_id, database_id):
    u"""Inserts sample data into the given database.

    The database and table must already exist and can be created using
    `create_database`.
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.batch() as batch:
        batch.insert(
            table=u"Singers",
            columns=(u"SingerId", u"FirstName", u"LastName"),
            values=[
                (1, u"Marc", u"Richards"),
                (2, u"Catalina", u"Smith"),
                (3, u"Alice", u"Trentor"),
                (4, u"Lea", u"Martin"),
                (5, u"David", u"Lomond"),
            ],
        )

        batch.insert(
            table=u"Albums",
            columns=(u"SingerId", u"AlbumId", u"AlbumTitle"),
            values=[
                (1, 1, u"Total Junk"),
                (1, 2, u"Go, Go, Go"),
                (2, 1, u"Green"),
                (2, 2, u"Forever Hold Your Peace"),
                (2, 3, u"Terrified"),
            ],
        )

    print u"Inserted data."


# [END spanner_insert_data]


# [START spanner_delete_data]
def delete_data(instance_id, database_id):
    u"""Deletes sample data from the given database.

    The database, table, and data must already exist and can be created using
    `create_database` and `insert_data`.
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    # Delete individual rows
    albums_to_delete = spanner.KeySet(keys=[[2, 1], [2, 3]])

    # Delete a range of rows where the column key is >=3 and <5
    singers_range = spanner.KeyRange(start_closed=[3], end_open=[5])
    singers_to_delete = spanner.KeySet(ranges=[singers_range])

    # Delete remaining Singers rows, which will also delete the remaining
    # Albums rows because Albums was defined with ON DELETE CASCADE
    remaining_singers = spanner.KeySet(all_=True)

    with database.batch() as batch:
        batch.delete(u"Albums", albums_to_delete)
        batch.delete(u"Singers", singers_to_delete)
        batch.delete(u"Singers", remaining_singers)

    print u"Deleted data."


# [END spanner_delete_data]


# [START spanner_query_data]
def query_data(instance_id, database_id):
    u"""Queries sample data from the database using SQL."""
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT SingerId, AlbumId, AlbumTitle FROM Albums"
        )

        for row in results:
            print u"SingerId: {}, AlbumId: {}, AlbumTitle: {}".format(*row)


# [END spanner_query_data]


# [START spanner_read_data]
def read_data(instance_id, database_id):
    u"""Reads sample data from the database."""
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        keyset = spanner.KeySet(all_=True)
        results = snapshot.read(
            table=u"Albums", columns=(u"SingerId", u"AlbumId", u"AlbumTitle"), keyset=keyset
        )

        for row in results:
            print u"SingerId: {}, AlbumId: {}, AlbumTitle: {}".format(*row)


# [END spanner_read_data]


# [START spanner_read_stale_data]
def read_stale_data(instance_id, database_id):
    u"""Reads sample data from the database. The data is exactly 15 seconds
    stale."""
    import datetime

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)
    staleness = datetime.timedelta(seconds=15)

    with database.snapshot(exact_staleness=staleness) as snapshot:
        keyset = spanner.KeySet(all_=True)
        results = snapshot.read(
            table=u"Albums",
            columns=(u"SingerId", u"AlbumId", u"MarketingBudget"),
            keyset=keyset,
        )

        for row in results:
            print u"SingerId: {}, AlbumId: {}, MarketingBudget: {}".format(*row)


# [END spanner_read_stale_data]


# [START spanner_query_data_with_new_column]
def query_data_with_new_column(instance_id, database_id):
    u"""Queries sample data from the database using SQL.

    This sample uses the `MarketingBudget` column. You can add the column
    by running the `add_column` sample or by running this DDL statement against
    your database:

        ALTER TABLE Albums ADD COLUMN MarketingBudget INT64
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT SingerId, AlbumId, MarketingBudget FROM Albums"
        )

        for row in results:
            print u"SingerId: {}, AlbumId: {}, MarketingBudget: {}".format(*row)


# [END spanner_query_data_with_new_column]


# [START spanner_create_index]
def add_index(instance_id, database_id):
    u"""Adds a simple index to the example database."""
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    operation = database.update_ddl(
        [u"CREATE INDEX AlbumsByAlbumTitle ON Albums(AlbumTitle)"]
    )

    print u"Waiting for operation to complete..."
    operation.result(120)

    print u"Added the AlbumsByAlbumTitle index."


# [END spanner_create_index]


# [START spanner_query_data_with_index]
def query_data_with_index(
    instance_id, database_id, start_title=u"Aardvark", end_title=u"Goo"
):
    u"""Queries sample data from the database using SQL and an index.

    The index must exist before running this sample. You can add the index
    by running the `add_index` sample or by running this DDL statement against
    your database:

        CREATE INDEX AlbumsByAlbumTitle ON Albums(AlbumTitle)

    This sample also uses the `MarketingBudget` column. You can add the column
    by running the `add_column` sample or by running this DDL statement against
    your database:

        ALTER TABLE Albums ADD COLUMN MarketingBudget INT64

    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    params = {u"start_title": start_title, u"end_title": end_title}
    param_types = {
        u"start_title": spanner.param_types.STRING,
        u"end_title": spanner.param_types.STRING,
    }

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT AlbumId, AlbumTitle, MarketingBudget "
            u"FROM Albums@{FORCE_INDEX=AlbumsByAlbumTitle} "
            u"WHERE AlbumTitle >= @start_title AND AlbumTitle < @end_title",
            params=params,
            param_types=param_types,
        )

        for row in results:
            print u"AlbumId: {}, AlbumTitle: {}, " u"MarketingBudget: {}".format(*row)


# [END spanner_query_data_with_index]


# [START spanner_read_data_with_index]
def read_data_with_index(instance_id, database_id):
    u"""Reads sample data from the database using an index.

    The index must exist before running this sample. You can add the index
    by running the `add_index` sample or by running this DDL statement against
    your database:

        CREATE INDEX AlbumsByAlbumTitle ON Albums(AlbumTitle)

    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        keyset = spanner.KeySet(all_=True)
        results = snapshot.read(
            table=u"Albums",
            columns=(u"AlbumId", u"AlbumTitle"),
            keyset=keyset,
            index=u"AlbumsByAlbumTitle",
        )

        for row in results:
            print u"AlbumId: {}, AlbumTitle: {}".format(*row)


# [END spanner_read_data_with_index]


# [START spanner_create_storing_index]
def add_storing_index(instance_id, database_id):
    u"""Adds an storing index to the example database."""
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    operation = database.update_ddl(
        [
            u"CREATE INDEX AlbumsByAlbumTitle2 ON Albums(AlbumTitle)"
            u"STORING (MarketingBudget)"
        ]
    )

    print u"Waiting for operation to complete..."
    operation.result(120)

    print u"Added the AlbumsByAlbumTitle2 index."


# [END spanner_create_storing_index]


# [START spanner_read_data_with_storing_index]
def read_data_with_storing_index(instance_id, database_id):
    u"""Reads sample data from the database using an index with a storing
    clause.

    The index must exist before running this sample. You can add the index
    by running the `add_soring_index` sample or by running this DDL statement
    against your database:

        CREATE INDEX AlbumsByAlbumTitle2 ON Albums(AlbumTitle)
        STORING (MarketingBudget)

    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        keyset = spanner.KeySet(all_=True)
        results = snapshot.read(
            table=u"Albums",
            columns=(u"AlbumId", u"AlbumTitle", u"MarketingBudget"),
            keyset=keyset,
            index=u"AlbumsByAlbumTitle2",
        )

        for row in results:
            print u"AlbumId: {}, AlbumTitle: {}, " u"MarketingBudget: {}".format(*row)


# [END spanner_read_data_with_storing_index]


# [START spanner_add_column]
def add_column(instance_id, database_id):
    u"""Adds a new column to the Albums table in the example database."""
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    operation = database.update_ddl(
        [u"ALTER TABLE Albums ADD COLUMN MarketingBudget INT64"]
    )

    print u"Waiting for operation to complete..."
    operation.result(120)

    print u"Added the MarketingBudget column."


# [END spanner_add_column]


# [START spanner_update_data]
def update_data(instance_id, database_id):
    u"""Updates sample data in the database.

    This updates the `MarketingBudget` column which must be created before
    running this sample. You can add the column by running the `add_column`
    sample or by running this DDL statement against your database:

        ALTER TABLE Albums ADD COLUMN MarketingBudget INT64

    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.batch() as batch:
        batch.update(
            table=u"Albums",
            columns=(u"SingerId", u"AlbumId", u"MarketingBudget"),
            values=[(1, 1, 100000), (2, 2, 500000)],
        )

    print u"Updated data."


# [END spanner_update_data]


# [START spanner_read_write_transaction]
def read_write_transaction(instance_id, database_id):
    u"""Performs a read-write transaction to update two sample records in the
    database.

    This will transfer 200,000 from the `MarketingBudget` field for the second
    Album to the first Album. If the `MarketingBudget` is too low, it will
    raise an exception.

    Before running this sample, you will need to run the `update_data` sample
    to populate the fields.
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    def update_albums(transaction):
        # Read the second album budget.
        second_album_keyset = spanner.KeySet(keys=[(2, 2)])
        second_album_result = transaction.read(
            table=u"Albums",
            columns=(u"MarketingBudget",),
            keyset=second_album_keyset,
            limit=1,
        )
        second_album_row = list(second_album_result)[0]
        second_album_budget = second_album_row[0]

        transfer_amount = 200000

        if second_album_budget < transfer_amount:
            # Raising an exception will automatically roll back the
            # transaction.
            raise ValueError(u"The second album doesn't have enough funds to transfer")

        # Read the first album's budget.
        first_album_keyset = spanner.KeySet(keys=[(1, 1)])
        first_album_result = transaction.read(
            table=u"Albums",
            columns=(u"MarketingBudget",),
            keyset=first_album_keyset,
            limit=1,
        )
        first_album_row = list(first_album_result)[0]
        first_album_budget = first_album_row[0]

        # Update the budgets.
        second_album_budget -= transfer_amount
        first_album_budget += transfer_amount
        print u"Setting first album's budget to {} and the second album's "
            u"budget to {}.".format(first_album_budget, second_album_budget)

        # Update the rows.
        transaction.update(
            table=u"Albums",
            columns=(u"SingerId", u"AlbumId", u"MarketingBudget"),
            values=[(1, 1, first_album_budget), (2, 2, second_album_budget)],
        )

    database.run_in_transaction(update_albums)

    print u"Transaction complete."


# [END spanner_read_write_transaction]


# [START spanner_read_only_transaction]
def read_only_transaction(instance_id, database_id):
    u"""Reads data inside of a read-only transaction.

    Within the read-only transaction, or "snapshot", the application sees
    consistent view of the database at a particular timestamp.
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot(multi_use=True) as snapshot:
        # Read using SQL.
        results = snapshot.execute_sql(
            u"SELECT SingerId, AlbumId, AlbumTitle FROM Albums"
        )

        print u"Results from first read:"
        for row in results:
            print u"SingerId: {}, AlbumId: {}, AlbumTitle: {}".format(*row)

        # Perform another read using the `read` method. Even if the data
        # is updated in-between the reads, the snapshot ensures that both
        # return the same data.
        keyset = spanner.KeySet(all_=True)
        results = snapshot.read(
            table=u"Albums", columns=(u"SingerId", u"AlbumId", u"AlbumTitle"), keyset=keyset
        )

        print u"Results from second read:"
        for row in results:
            print u"SingerId: {}, AlbumId: {}, AlbumTitle: {}".format(*row)


# [END spanner_read_only_transaction]


# [START spanner_create_table_with_timestamp_column]
def create_table_with_timestamp(instance_id, database_id):
    u"""Creates a table with a COMMIT_TIMESTAMP column."""

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    operation = database.update_ddl(
        [
            u"""CREATE TABLE Performances (
            SingerId     INT64 NOT NULL,
            VenueId      INT64 NOT NULL,
            EventDate    Date,
            Revenue      INT64,
            LastUpdateTime TIMESTAMP NOT NULL
            OPTIONS(allow_commit_timestamp=true)
        ) PRIMARY KEY (SingerId, VenueId, EventDate),
          INTERLEAVE IN PARENT Singers ON DELETE CASCADE"""
        ]
    )

    print u"Waiting for operation to complete..."
    operation.result(120)

    print u"Created Performances table on database {} on instance {}".format(
            database_id, instance_id
        )


# [END spanner_create_table_with_timestamp_column]


# [START spanner_insert_data_with_timestamp_column]
def insert_data_with_timestamp(instance_id, database_id):
    u"""Inserts data with a COMMIT_TIMESTAMP field into a table. """

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)

    database = instance.database(database_id)

    with database.batch() as batch:
        batch.insert(
            table=u"Performances",
            columns=(u"SingerId", u"VenueId", u"EventDate", u"Revenue", u"LastUpdateTime"),
            values=[
                (1, 4, u"2017-10-05", 11000, spanner.COMMIT_TIMESTAMP),
                (1, 19, u"2017-11-02", 15000, spanner.COMMIT_TIMESTAMP),
                (2, 42, u"2017-12-23", 7000, spanner.COMMIT_TIMESTAMP),
            ],
        )

    print u"Inserted data."


# [END spanner_insert_data_with_timestamp_column]


# [START spanner_add_timestamp_column]
def add_timestamp_column(instance_id, database_id):
    u""" Adds a new TIMESTAMP column to the Albums table in the example database.
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)

    database = instance.database(database_id)

    operation = database.update_ddl(
        [
            u"ALTER TABLE Albums ADD COLUMN LastUpdateTime TIMESTAMP "
            u"OPTIONS(allow_commit_timestamp=true)"
        ]
    )

    print u"Waiting for operation to complete..."
    operation.result(120)

    print u'Altered table "Albums" on database {} on instance {}.'.format(
            database_id, instance_id
        )


# [END spanner_add_timestamp_column]


# [START spanner_update_data_with_timestamp_column]
def update_data_with_timestamp(instance_id, database_id):
    u"""Updates Performances tables in the database with the COMMIT_TIMESTAMP
    column.

    This updates the `MarketingBudget` column which must be created before
    running this sample. You can add the column by running the `add_column`
    sample or by running this DDL statement against your database:

        ALTER TABLE Albums ADD COLUMN MarketingBudget INT64

    In addition this update expects the LastUpdateTime column added by
    applying this DDL statement against your database:

        ALTER TABLE Albums ADD COLUMN LastUpdateTime TIMESTAMP
        OPTIONS(allow_commit_timestamp=true)
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)

    database = instance.database(database_id)

    with database.batch() as batch:
        batch.update(
            table=u"Albums",
            columns=(u"SingerId", u"AlbumId", u"MarketingBudget", u"LastUpdateTime"),
            values=[
                (1, 1, 1000000, spanner.COMMIT_TIMESTAMP),
                (2, 2, 750000, spanner.COMMIT_TIMESTAMP),
            ],
        )

    print u"Updated data."


# [END spanner_update_data_with_timestamp_column]


# [START spanner_query_data_with_timestamp_column]
def query_data_with_timestamp(instance_id, database_id):
    u"""Queries sample data from the database using SQL.

    This updates the `LastUpdateTime` column which must be created before
    running this sample. You can add the column by running the
    `add_timestamp_column` sample or by running this DDL statement
    against your database:

        ALTER TABLE Performances ADD COLUMN LastUpdateTime TIMESTAMP
        OPTIONS (allow_commit_timestamp=true)

    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)

    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT SingerId, AlbumId, MarketingBudget FROM Albums "
            u"ORDER BY LastUpdateTime DESC"
        )

    for row in results:
        print u"SingerId: {}, AlbumId: {}, MarketingBudget: {}".format(*row)


# [END spanner_query_data_with_timestamp_column]


# [START spanner_add_numeric_column]
def add_numeric_column(instance_id, database_id):
    u""" Adds a new NUMERIC column to the Venues table in the example database.
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)

    database = instance.database(database_id)

    operation = database.update_ddl([u"ALTER TABLE Venues ADD COLUMN Revenue NUMERIC"])

    print u"Waiting for operation to complete..."
    operation.result(120)

    print u'Altered table "Venues" on database {} on instance {}.'.format(
            database_id, instance_id
        )


# [END spanner_add_numeric_column]


# [START spanner_update_data_with_numeric_column]
def update_data_with_numeric(instance_id, database_id):
    u"""Updates Venues tables in the database with the NUMERIC
    column.

    This updates the `Revenue` column which must be created before
    running this sample. You can add the column by running the
    `add_numeric_column` sample or by running this DDL statement
     against your database:

        ALTER TABLE Venues ADD COLUMN Revenue NUMERIC
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)

    database = instance.database(database_id)

    with database.batch() as batch:
        batch.update(
            table=u"Venues",
            columns=(u"VenueId", u"Revenue"),
            values=[
                (4, decimal.Decimal(u"35000")),
                (19, decimal.Decimal(u"104500")),
                (42, decimal.Decimal(u"99999999999999999999999999999.99")),
            ],
        )

    print u"Updated data."


# [END spanner_update_data_with_numeric_column]


# [START spanner_write_data_for_struct_queries]
def write_struct_data(instance_id, database_id):
    u"""Inserts sample data that can be used to test STRUCT parameters
    in queries.
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.batch() as batch:
        batch.insert(
            table=u"Singers",
            columns=(u"SingerId", u"FirstName", u"LastName"),
            values=[
                (6, u"Elena", u"Campbell"),
                (7, u"Gabriel", u"Wright"),
                (8, u"Benjamin", u"Martinez"),
                (9, u"Hannah", u"Harris"),
            ],
        )

    print u"Inserted sample data for STRUCT queries"


# [END spanner_write_data_for_struct_queries]


def query_with_struct(instance_id, database_id):
    u"""Query a table using STRUCT parameters. """
    # [START spanner_create_struct_with_data]
    record_type = param_types.Struct(
        [
            param_types.StructField(u"FirstName", param_types.STRING),
            param_types.StructField(u"LastName", param_types.STRING),
        ]
    )
    record_value = (u"Elena", u"Campbell")
    # [END spanner_create_struct_with_data]

    # [START spanner_query_data_with_struct]
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)

    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT SingerId FROM Singers WHERE " u"(FirstName, LastName) = @name",
            params={u"name": record_value},
            param_types={u"name": record_type},
        )

    for row in results:
        print u"SingerId: {}".format(*row)
    # [END spanner_query_data_with_struct]


def query_with_array_of_struct(instance_id, database_id):
    u"""Query a table using an array of STRUCT parameters. """
    # [START spanner_create_user_defined_struct]
    name_type = param_types.Struct(
        [
            param_types.StructField(u"FirstName", param_types.STRING),
            param_types.StructField(u"LastName", param_types.STRING),
        ]
    )
    # [END spanner_create_user_defined_struct]

    # [START spanner_create_array_of_struct_with_data]
    band_members = [
        (u"Elena", u"Campbell"),
        (u"Gabriel", u"Wright"),
        (u"Benjamin", u"Martinez"),
    ]
    # [END spanner_create_array_of_struct_with_data]

    # [START spanner_query_data_with_array_of_struct]
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT SingerId FROM Singers WHERE "
            u"STRUCT<FirstName STRING, LastName STRING>"
            u"(FirstName, LastName) IN UNNEST(@names)",
            params={u"names": band_members},
            param_types={u"names": param_types.Array(name_type)},
        )

    for row in results:
        print u"SingerId: {}".format(*row)
    # [END spanner_query_data_with_array_of_struct]


# [START spanner_field_access_on_struct_parameters]
def query_struct_field(instance_id, database_id):
    u"""Query a table using field access on a STRUCT parameter. """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    name_type = param_types.Struct(
        [
            param_types.StructField(u"FirstName", param_types.STRING),
            param_types.StructField(u"LastName", param_types.STRING),
        ]
    )

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT SingerId FROM Singers " u"WHERE FirstName = @name.FirstName",
            params={u"name": (u"Elena", u"Campbell")},
            param_types={u"name": name_type},
        )

    for row in results:
        print u"SingerId: {}".format(*row)


# [END spanner_field_access_on_struct_parameters]


# [START spanner_field_access_on_nested_struct_parameters]
def query_nested_struct_field(instance_id, database_id):
    u"""Query a table using nested field access on a STRUCT parameter. """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    song_info_type = param_types.Struct(
        [
            param_types.StructField(u"SongName", param_types.STRING),
            param_types.StructField(
                u"ArtistNames",
                param_types.Array(
                    param_types.Struct(
                        [
                            param_types.StructField(u"FirstName", param_types.STRING),
                            param_types.StructField(u"LastName", param_types.STRING),
                        ]
                    )
                ),
            ),
        ]
    )

    song_info = (u"Imagination", [(u"Elena", u"Campbell"), (u"Hannah", u"Harris")])

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT SingerId, @song_info.SongName "
            u"FROM Singers WHERE "
            u"STRUCT<FirstName STRING, LastName STRING>"
            u"(FirstName, LastName) "
            u"IN UNNEST(@song_info.ArtistNames)",
            params={u"song_info": song_info},
            param_types={u"song_info": song_info_type},
        )

    for row in results:
        print u"SingerId: {} SongName: {}".format(*row)


# [END spanner_field_access_on_nested_struct_parameters]


def insert_data_with_dml(instance_id, database_id):
    u"""Inserts sample data into the given database using a DML statement. """
    # [START spanner_dml_standard_insert]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    def insert_singers(transaction):
        row_ct = transaction.execute_update(
            u"INSERT Singers (SingerId, FirstName, LastName) "
            u" VALUES (10, 'Virginia', 'Watson')"
        )

        print u"{} record(s) inserted.".format(row_ct)

    database.run_in_transaction(insert_singers)
    # [END spanner_dml_standard_insert]


def update_data_with_dml(instance_id, database_id):
    u"""Updates sample data from the database using a DML statement. """
    # [START spanner_dml_standard_update]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    def update_albums(transaction):
        row_ct = transaction.execute_update(
            u"UPDATE Albums "
            u"SET MarketingBudget = MarketingBudget * 2 "
            u"WHERE SingerId = 1 and AlbumId = 1"
        )

        print u"{} record(s) updated.".format(row_ct)

    database.run_in_transaction(update_albums)
    # [END spanner_dml_standard_update]


def delete_data_with_dml(instance_id, database_id):
    u"""Deletes sample data from the database using a DML statement. """
    # [START spanner_dml_standard_delete]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    def delete_singers(transaction):
        row_ct = transaction.execute_update(
            u"DELETE FROM Singers WHERE FirstName = 'Alice'"
        )

        print u"{} record(s) deleted.".format(row_ct)

    database.run_in_transaction(delete_singers)
    # [END spanner_dml_standard_delete]


def update_data_with_dml_timestamp(instance_id, database_id):
    u"""Updates data with Timestamp from the database using a DML statement. """
    # [START spanner_dml_standard_update_with_timestamp]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    def update_albums(transaction):
        row_ct = transaction.execute_update(
            u"UPDATE Albums "
            u"SET LastUpdateTime = PENDING_COMMIT_TIMESTAMP() "
            u"WHERE SingerId = 1"
        )

        print u"{} record(s) updated.".format(row_ct)

    database.run_in_transaction(update_albums)
    # [END spanner_dml_standard_update_with_timestamp]


def dml_write_read_transaction(instance_id, database_id):
    u"""First inserts data then reads it from within a transaction using DML."""
    # [START spanner_dml_write_then_read]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    def write_then_read(transaction):
        # Insert record.
        row_ct = transaction.execute_update(
            u"INSERT Singers (SingerId, FirstName, LastName) "
            u" VALUES (11, 'Timothy', 'Campbell')"
        )
        print u"{} record(s) inserted.".format(row_ct)

        # Read newly inserted record.
        results = transaction.execute_sql(
            u"SELECT FirstName, LastName FROM Singers WHERE SingerId = 11"
        )
        for result in results:
            print u"FirstName: {}, LastName: {}".format(*result)

    database.run_in_transaction(write_then_read)
    # [END spanner_dml_write_then_read]


def update_data_with_dml_struct(instance_id, database_id):
    u"""Updates data with a DML statement and STRUCT parameters. """
    # [START spanner_dml_structs]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    record_type = param_types.Struct(
        [
            param_types.StructField(u"FirstName", param_types.STRING),
            param_types.StructField(u"LastName", param_types.STRING),
        ]
    )
    record_value = (u"Timothy", u"Campbell")

    def write_with_struct(transaction):
        row_ct = transaction.execute_update(
            u"UPDATE Singers SET LastName = 'Grant' "
            u"WHERE STRUCT<FirstName STRING, LastName STRING>"
            u"(FirstName, LastName) = @name",
            params={u"name": record_value},
            param_types={u"name": record_type},
        )
        print u"{} record(s) updated.".format(row_ct)

    database.run_in_transaction(write_with_struct)
    # [END spanner_dml_structs]


def insert_with_dml(instance_id, database_id):
    u"""Inserts data with a DML statement into the database. """
    # [START spanner_dml_getting_started_insert]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    def insert_singers(transaction):
        row_ct = transaction.execute_update(
            u"INSERT Singers (SingerId, FirstName, LastName) VALUES "
            u"(12, 'Melissa', 'Garcia'), "
            u"(13, 'Russell', 'Morales'), "
            u"(14, 'Jacqueline', 'Long'), "
            u"(15, 'Dylan', 'Shaw')"
        )
        print u"{} record(s) inserted.".format(row_ct)

    database.run_in_transaction(insert_singers)
    # [END spanner_dml_getting_started_insert]


def query_data_with_parameter(instance_id, database_id):
    u"""Queries sample data from the database using SQL with a parameter."""
    # [START spanner_query_with_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT SingerId, FirstName, LastName FROM Singers "
            u"WHERE LastName = @lastName",
            params={u"lastName": u"Garcia"},
            param_types={u"lastName": spanner.param_types.STRING},
        )

        for row in results:
            print u"SingerId: {}, FirstName: {}, LastName: {}".format(*row)
    # [END spanner_query_with_parameter]


def write_with_dml_transaction(instance_id, database_id):
    u""" Transfers part of a marketing budget from one album to another. """
    # [START spanner_dml_getting_started_update]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    def transfer_budget(transaction):
        # Transfer marketing budget from one album to another. Performed in a
        # single transaction to ensure that the transfer is atomic.
        second_album_result = transaction.execute_sql(
            u"SELECT MarketingBudget from Albums " u"WHERE SingerId = 2 and AlbumId = 2"
        )
        second_album_row = list(second_album_result)[0]
        second_album_budget = second_album_row[0]

        transfer_amount = 200000

        # Transaction will only be committed if this condition still holds at
        # the time of commit. Otherwise it will be aborted and the callable
        # will be rerun by the client library
        if second_album_budget >= transfer_amount:
            first_album_result = transaction.execute_sql(
                u"SELECT MarketingBudget from Albums "
                u"WHERE SingerId = 1 and AlbumId = 1"
            )
            first_album_row = list(first_album_result)[0]
            first_album_budget = first_album_row[0]

            second_album_budget -= transfer_amount
            first_album_budget += transfer_amount

            # Update first album
            transaction.execute_update(
                u"UPDATE Albums "
                u"SET MarketingBudget = @AlbumBudget "
                u"WHERE SingerId = 1 and AlbumId = 1",
                params={u"AlbumBudget": first_album_budget},
                param_types={u"AlbumBudget": spanner.param_types.INT64},
            )

            # Update second album
            transaction.execute_update(
                u"UPDATE Albums "
                u"SET MarketingBudget = @AlbumBudget "
                u"WHERE SingerId = 2 and AlbumId = 2",
                params={u"AlbumBudget": second_album_budget},
                param_types={u"AlbumBudget": spanner.param_types.INT64},
            )

            print u"Transferred {} from Album2's budget to Album1's".format(
                    transfer_amount
                )

    database.run_in_transaction(transfer_budget)
    # [END spanner_dml_getting_started_update]


def update_data_with_partitioned_dml(instance_id, database_id):
    u""" Update sample data with a partitioned DML statement. """
    # [START spanner_dml_partitioned_update]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    row_ct = database.execute_partitioned_dml(
        u"UPDATE Albums SET MarketingBudget = 100000 WHERE SingerId > 1"
    )

    print u"{} records updated.".format(row_ct)
    # [END spanner_dml_partitioned_update]


def delete_data_with_partitioned_dml(instance_id, database_id):
    u""" Delete sample data with a partitioned DML statement. """
    # [START spanner_dml_partitioned_delete]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    row_ct = database.execute_partitioned_dml(u"DELETE FROM Singers WHERE SingerId > 10")

    print u"{} record(s) deleted.".format(row_ct)
    # [END spanner_dml_partitioned_delete]


def update_with_batch_dml(instance_id, database_id):
    u"""Updates sample data in the database using Batch DML. """
    # [START spanner_dml_batch_update]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"

    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    insert_statement = (
        u"INSERT INTO Albums "
        u"(SingerId, AlbumId, AlbumTitle, MarketingBudget) "
        u"VALUES (1, 3, 'Test Album Title', 10000)"
    )

    update_statement = (
        u"UPDATE Albums "
        u"SET MarketingBudget = MarketingBudget * 2 "
        u"WHERE SingerId = 1 and AlbumId = 3"
    )

    def update_albums(transaction):
        row_cts = transaction.batch_update([insert_statement, update_statement])

        print u"Executed {} SQL statements using Batch DML.".format(len(row_cts))

    database.run_in_transaction(update_albums)
    # [END spanner_dml_batch_update]


def create_table_with_datatypes(instance_id, database_id):
    u"""Creates a table with supported dataypes. """
    # [START spanner_create_table_with_datatypes]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    operation = database.update_ddl(
        [
            u"""CREATE TABLE Venues (
            VenueId         INT64 NOT NULL,
            VenueName       STRING(100),
            VenueInfo       BYTES(MAX),
            Capacity        INT64,
            AvailableDates  ARRAY<DATE>,
            LastContactDate DATE,
            OutdoorVenue    BOOL,
            PopularityScore FLOAT64,
            LastUpdateTime  TIMESTAMP NOT NULL
            OPTIONS(allow_commit_timestamp=true)
        ) PRIMARY KEY (VenueId)"""
        ]
    )

    print u"Waiting for operation to complete..."
    operation.result(120)

    print u"Created Venues table on database {} on instance {}".format(
            database_id, instance_id
        )
    # [END spanner_create_table_with_datatypes]


def insert_datatypes_data(instance_id, database_id):
    u"""Inserts data with supported datatypes into a table. """
    # [START spanner_insert_datatypes_data]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    exampleBytes1 = base64.b64encode(u"Hello World 1".encode())
    exampleBytes2 = base64.b64encode(u"Hello World 2".encode())
    exampleBytes3 = base64.b64encode(u"Hello World 3".encode())
    available_dates1 = [u"2020-12-01", u"2020-12-02", u"2020-12-03"]
    available_dates2 = [u"2020-11-01", u"2020-11-05", u"2020-11-15"]
    available_dates3 = [u"2020-10-01", u"2020-10-07"]
    with database.batch() as batch:
        batch.insert(
            table=u"Venues",
            columns=(
                u"VenueId",
                u"VenueName",
                u"VenueInfo",
                u"Capacity",
                u"AvailableDates",
                u"LastContactDate",
                u"OutdoorVenue",
                u"PopularityScore",
                u"LastUpdateTime",
            ),
            values=[
                (
                    4,
                    u"Venue 4",
                    exampleBytes1,
                    1800,
                    available_dates1,
                    u"2018-09-02",
                    False,
                    0.85543,
                    spanner.COMMIT_TIMESTAMP,
                ),
                (
                    19,
                    u"Venue 19",
                    exampleBytes2,
                    6300,
                    available_dates2,
                    u"2019-01-15",
                    True,
                    0.98716,
                    spanner.COMMIT_TIMESTAMP,
                ),
                (
                    42,
                    u"Venue 42",
                    exampleBytes3,
                    3000,
                    available_dates3,
                    u"2018-10-01",
                    False,
                    0.72598,
                    spanner.COMMIT_TIMESTAMP,
                ),
            ],
        )

    print u"Inserted data."
    # [END spanner_insert_datatypes_data]


def query_data_with_array(instance_id, database_id):
    u"""Queries sample data using SQL with an ARRAY parameter. """
    # [START spanner_query_with_array_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    exampleArray = [u"2020-10-01", u"2020-11-01"]
    param = {u"available_dates": exampleArray}
    param_type = {u"available_dates": param_types.Array(param_types.DATE)}

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName, AvailableDate FROM Venues v,"
            u"UNNEST(v.AvailableDates) as AvailableDate "
            u"WHERE AvailableDate in UNNEST(@available_dates)",
            params=param,
            param_types=param_type,
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}, AvailableDate: {}".format(*row)
    # [END spanner_query_with_array_parameter]


def query_data_with_bool(instance_id, database_id):
    u"""Queries sample data using SQL with a BOOL parameter. """
    # [START spanner_query_with_bool_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    exampleBool = True
    param = {u"outdoor_venue": exampleBool}
    param_type = {u"outdoor_venue": param_types.BOOL}

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName, OutdoorVenue FROM Venues "
            u"WHERE OutdoorVenue = @outdoor_venue",
            params=param,
            param_types=param_type,
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}, OutdoorVenue: {}".format(*row)
    # [END spanner_query_with_bool_parameter]


def query_data_with_bytes(instance_id, database_id):
    u"""Queries sample data using SQL with a BYTES parameter. """
    # [START spanner_query_with_bytes_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    exampleBytes = base64.b64encode(u"Hello World 1".encode())
    param = {u"venue_info": exampleBytes}
    param_type = {u"venue_info": param_types.BYTES}

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName FROM Venues " u"WHERE VenueInfo = @venue_info",
            params=param,
            param_types=param_type,
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}".format(*row)
    # [END spanner_query_with_bytes_parameter]


def query_data_with_date(instance_id, database_id):
    u"""Queries sample data using SQL with a DATE parameter. """
    # [START spanner_query_with_date_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    exampleDate = u"2019-01-01"
    param = {u"last_contact_date": exampleDate}
    param_type = {u"last_contact_date": param_types.DATE}

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName, LastContactDate FROM Venues "
            u"WHERE LastContactDate < @last_contact_date",
            params=param,
            param_types=param_type,
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}, LastContactDate: {}".format(*row)
    # [END spanner_query_with_date_parameter]


def query_data_with_float(instance_id, database_id):
    u"""Queries sample data using SQL with a FLOAT64 parameter. """
    # [START spanner_query_with_float_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    exampleFloat = 0.8
    param = {u"popularity_score": exampleFloat}
    param_type = {u"popularity_score": param_types.FLOAT64}

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName, PopularityScore FROM Venues "
            u"WHERE PopularityScore > @popularity_score",
            params=param,
            param_types=param_type,
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}, PopularityScore: {}".format(*row)
    # [END spanner_query_with_float_parameter]


def query_data_with_int(instance_id, database_id):
    u"""Queries sample data using SQL with a INT64 parameter. """
    # [START spanner_query_with_int_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    exampleInt = 3000
    param = {u"capacity": exampleInt}
    param_type = {u"capacity": param_types.INT64}

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName, Capacity FROM Venues "
            u"WHERE Capacity >= @capacity",
            params=param,
            param_types=param_type,
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}, Capacity: {}".format(*row)
    # [END spanner_query_with_int_parameter]


def query_data_with_string(instance_id, database_id):
    u"""Queries sample data using SQL with a STRING parameter. """
    # [START spanner_query_with_string_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    exampleString = u"Venue 42"
    param = {u"venue_name": exampleString}
    param_type = {u"venue_name": param_types.STRING}

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName FROM Venues " u"WHERE VenueName = @venue_name",
            params=param,
            param_types=param_type,
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}".format(*row)
    # [END spanner_query_with_string_parameter]


def query_data_with_numeric_parameter(instance_id, database_id):
    u"""Queries sample data using SQL with a NUMERIC parameter. """
    # [START spanner_query_with_numeric_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    example_numeric = decimal.Decimal(u"100000")
    param = {u"revenue": example_numeric}
    param_type = {u"revenue": param_types.NUMERIC}

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, Revenue FROM Venues " u"WHERE Revenue < @revenue",
            params=param,
            param_types=param_type,
        )

        for row in results:
            print u"VenueId: {}, Revenue: {}".format(*row)
    # [END spanner_query_with_numeric_parameter]


def query_data_with_timestamp_parameter(instance_id, database_id):
    u"""Queries sample data using SQL with a TIMESTAMP parameter. """
    # [START spanner_query_with_timestamp_parameter]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    example_timestamp = datetime.datetime.utcnow().isoformat() + u"Z"
    # [END spanner_query_with_timestamp_parameter]
    # Avoid time drift on the local machine.
    # https://github.com/GoogleCloudPlatform/python-docs-samples/issues/4197.
    example_timestamp = (
        datetime.datetime.utcnow() + datetime.timedelta(days=1)
    ).isoformat() + u"Z"
    # [START spanner_query_with_timestamp_parameter]
    param = {u"last_update_time": example_timestamp}
    param_type = {u"last_update_time": param_types.TIMESTAMP}

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName, LastUpdateTime FROM Venues "
            u"WHERE LastUpdateTime < @last_update_time",
            params=param,
            param_types=param_type,
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}, LastUpdateTime: {}".format(*row)
    # [END spanner_query_with_timestamp_parameter]


def query_data_with_query_options(instance_id, database_id):
    u"""Queries sample data using SQL with query options."""
    # [START spanner_query_with_query_options]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName, LastUpdateTime FROM Venues",
            query_options={u"optimizer_version": u"1"},
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}, LastUpdateTime: {}".format(*row)
    # [END spanner_query_with_query_options]


def create_client_with_query_options(instance_id, database_id):
    u"""Create a client with query options."""
    # [START spanner_create_client_with_query_options]
    # instance_id = "your-spanner-instance"
    # database_id = "your-spanner-db-id"
    spanner_client = spanner.Client(query_options={u"optimizer_version": u"1"})
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            u"SELECT VenueId, VenueName, LastUpdateTime FROM Venues"
        )

        for row in results:
            print u"VenueId: {}, VenueName: {}, LastUpdateTime: {}".format(*row)
    # [END spanner_create_client_with_query_options]


if __name__ == u"__main__":  # noqa: C901
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(u"instance_id", help=u"Your Cloud Spanner instance ID.")
    parser.add_argument(
        u"--database-id", help=u"Your Cloud Spanner database ID.", default=u"example_db"
    )

    subparsers = parser.add_subparsers(dest=u"command")
    subparsers.add_parser(u"create_instance", help=create_instance.__doc__)
    subparsers.add_parser(u"create_database", help=create_database.__doc__)
    subparsers.add_parser(u"insert_data", help=insert_data.__doc__)
    subparsers.add_parser(u"delete_data", help=delete_data.__doc__)
    subparsers.add_parser(u"query_data", help=query_data.__doc__)
    subparsers.add_parser(u"read_data", help=read_data.__doc__)
    subparsers.add_parser(u"read_stale_data", help=read_stale_data.__doc__)
    subparsers.add_parser(u"add_column", help=add_column.__doc__)
    subparsers.add_parser(u"update_data", help=update_data.__doc__)
    subparsers.add_parser(
        u"query_data_with_new_column", help=query_data_with_new_column.__doc__
    )
    subparsers.add_parser(u"read_write_transaction", help=read_write_transaction.__doc__)
    subparsers.add_parser(u"read_only_transaction", help=read_only_transaction.__doc__)
    subparsers.add_parser(u"add_index", help=add_index.__doc__)
    query_data_with_index_parser = subparsers.add_parser(
        u"query_data_with_index", help=query_data_with_index.__doc__
    )
    query_data_with_index_parser.add_argument(u"--start_title", default=u"Aardvark")
    query_data_with_index_parser.add_argument(u"--end_title", default=u"Goo")
    subparsers.add_parser(u"read_data_with_index", help=insert_data.__doc__)
    subparsers.add_parser(u"add_storing_index", help=add_storing_index.__doc__)
    subparsers.add_parser(u"read_data_with_storing_index", help=insert_data.__doc__)
    subparsers.add_parser(
        u"create_table_with_timestamp", help=create_table_with_timestamp.__doc__
    )
    subparsers.add_parser(
        u"insert_data_with_timestamp", help=insert_data_with_timestamp.__doc__
    )
    subparsers.add_parser(u"add_timestamp_column", help=add_timestamp_column.__doc__)
    subparsers.add_parser(
        u"update_data_with_timestamp", help=update_data_with_timestamp.__doc__
    )
    subparsers.add_parser(
        u"query_data_with_timestamp", help=query_data_with_timestamp.__doc__
    )
    subparsers.add_parser(u"write_struct_data", help=write_struct_data.__doc__)
    subparsers.add_parser(u"query_with_struct", help=query_with_struct.__doc__)
    subparsers.add_parser(
        u"query_with_array_of_struct", help=query_with_array_of_struct.__doc__
    )
    subparsers.add_parser(u"query_struct_field", help=query_struct_field.__doc__)
    subparsers.add_parser(
        u"query_nested_struct_field", help=query_nested_struct_field.__doc__
    )
    subparsers.add_parser(u"insert_data_with_dml", help=insert_data_with_dml.__doc__)
    subparsers.add_parser(u"update_data_with_dml", help=update_data_with_dml.__doc__)
    subparsers.add_parser(u"delete_data_with_dml", help=delete_data_with_dml.__doc__)
    subparsers.add_parser(
        u"update_data_with_dml_timestamp", help=update_data_with_dml_timestamp.__doc__
    )
    subparsers.add_parser(
        u"dml_write_read_transaction", help=dml_write_read_transaction.__doc__
    )
    subparsers.add_parser(
        u"update_data_with_dml_struct", help=update_data_with_dml_struct.__doc__
    )
    subparsers.add_parser(u"insert_with_dml", help=insert_with_dml.__doc__)
    subparsers.add_parser(
        u"query_data_with_parameter", help=query_data_with_parameter.__doc__
    )
    subparsers.add_parser(
        u"write_with_dml_transaction", help=write_with_dml_transaction.__doc__
    )
    subparsers.add_parser(
        u"update_data_with_partitioned_dml",
        help=update_data_with_partitioned_dml.__doc__,
    )
    subparsers.add_parser(
        u"delete_data_with_partitioned_dml",
        help=delete_data_with_partitioned_dml.__doc__,
    )
    subparsers.add_parser(u"update_with_batch_dml", help=update_with_batch_dml.__doc__)
    subparsers.add_parser(
        u"create_table_with_datatypes", help=create_table_with_datatypes.__doc__
    )
    subparsers.add_parser(u"insert_datatypes_data", help=insert_datatypes_data.__doc__)
    subparsers.add_parser(u"query_data_with_array", help=query_data_with_array.__doc__)
    subparsers.add_parser(u"query_data_with_bool", help=query_data_with_bool.__doc__)
    subparsers.add_parser(u"query_data_with_bytes", help=query_data_with_bytes.__doc__)
    subparsers.add_parser(u"query_data_with_date", help=query_data_with_date.__doc__)
    subparsers.add_parser(u"query_data_with_float", help=query_data_with_float.__doc__)
    subparsers.add_parser(u"query_data_with_int", help=query_data_with_int.__doc__)
    subparsers.add_parser(u"query_data_with_string", help=query_data_with_string.__doc__)
    subparsers.add_parser(
        u"query_data_with_timestamp_parameter",
        help=query_data_with_timestamp_parameter.__doc__,
    )
    subparsers.add_parser(
        u"query_data_with_query_options", help=query_data_with_query_options.__doc__
    )
    subparsers.add_parser(
        u"create_client_with_query_options",
        help=create_client_with_query_options.__doc__,
    )

    args = parser.parse_args()

    if args.command == u"create_instance":
        create_instance(args.instance_id)
    elif args.command == u"create_database":
        create_database(args.instance_id, args.database_id)
    elif args.command == u"insert_data":
        insert_data(args.instance_id, args.database_id)
    elif args.command == u"delete_data":
        delete_data(args.instance_id, args.database_id)
    elif args.command == u"query_data":
        query_data(args.instance_id, args.database_id)
    elif args.command == u"read_data":
        read_data(args.instance_id, args.database_id)
    elif args.command == u"read_stale_data":
        read_stale_data(args.instance_id, args.database_id)
    elif args.command == u"add_column":
        add_column(args.instance_id, args.database_id)
    elif args.command == u"update_data":
        update_data(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_new_column":
        query_data_with_new_column(args.instance_id, args.database_id)
    elif args.command == u"read_write_transaction":
        read_write_transaction(args.instance_id, args.database_id)
    elif args.command == u"read_only_transaction":
        read_only_transaction(args.instance_id, args.database_id)
    elif args.command == u"add_index":
        add_index(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_index":
        query_data_with_index(
            args.instance_id, args.database_id, args.start_title, args.end_title
        )
    elif args.command == u"read_data_with_index":
        read_data_with_index(args.instance_id, args.database_id)
    elif args.command == u"add_storing_index":
        add_storing_index(args.instance_id, args.database_id)
    elif args.command == u"read_data_with_storing_index":
        read_data_with_storing_index(args.instance_id, args.database_id)
    elif args.command == u"create_table_with_timestamp":
        create_table_with_timestamp(args.instance_id, args.database_id)
    elif args.command == u"insert_data_with_timestamp":
        insert_data_with_timestamp(args.instance_id, args.database_id)
    elif args.command == u"add_timestamp_column":
        add_timestamp_column(args.instance_id, args.database_id)
    elif args.command == u"update_data_with_timestamp":
        update_data_with_timestamp(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_timestamp":
        query_data_with_timestamp(args.instance_id, args.database_id)
    elif args.command == u"write_struct_data":
        write_struct_data(args.instance_id, args.database_id)
    elif args.command == u"query_with_struct":
        query_with_struct(args.instance_id, args.database_id)
    elif args.command == u"query_with_array_of_struct":
        query_with_array_of_struct(args.instance_id, args.database_id)
    elif args.command == u"query_struct_field":
        query_struct_field(args.instance_id, args.database_id)
    elif args.command == u"query_nested_struct_field":
        query_nested_struct_field(args.instance_id, args.database_id)
    elif args.command == u"insert_data_with_dml":
        insert_data_with_dml(args.instance_id, args.database_id)
    elif args.command == u"update_data_with_dml":
        update_data_with_dml(args.instance_id, args.database_id)
    elif args.command == u"delete_data_with_dml":
        delete_data_with_dml(args.instance_id, args.database_id)
    elif args.command == u"update_data_with_dml_timestamp":
        update_data_with_dml_timestamp(args.instance_id, args.database_id)
    elif args.command == u"dml_write_read_transaction":
        dml_write_read_transaction(args.instance_id, args.database_id)
    elif args.command == u"update_data_with_dml_struct":
        update_data_with_dml_struct(args.instance_id, args.database_id)
    elif args.command == u"insert_with_dml":
        insert_with_dml(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_parameter":
        query_data_with_parameter(args.instance_id, args.database_id)
    elif args.command == u"write_with_dml_transaction":
        write_with_dml_transaction(args.instance_id, args.database_id)
    elif args.command == u"update_data_with_partitioned_dml":
        update_data_with_partitioned_dml(args.instance_id, args.database_id)
    elif args.command == u"delete_data_with_partitioned_dml":
        delete_data_with_partitioned_dml(args.instance_id, args.database_id)
    elif args.command == u"update_with_batch_dml":
        update_with_batch_dml(args.instance_id, args.database_id)
    elif args.command == u"create_table_with_datatypes":
        create_table_with_datatypes(args.instance_id, args.database_id)
    elif args.command == u"insert_datatypes_data":
        insert_datatypes_data(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_array":
        query_data_with_array(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_bool":
        query_data_with_bool(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_bytes":
        query_data_with_bytes(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_date":
        query_data_with_date(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_float":
        query_data_with_float(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_int":
        query_data_with_int(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_string":
        query_data_with_string(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_timestamp_parameter":
        query_data_with_timestamp_parameter(args.instance_id, args.database_id)
    elif args.command == u"query_data_with_query_options":
        query_data_with_query_options(args.instance_id, args.database_id)
    elif args.command == u"create_client_with_query_options":
        create_client_with_query_options(args.instance_id, args.database_id)
