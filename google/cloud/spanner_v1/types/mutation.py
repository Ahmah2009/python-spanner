# -*- coding: utf-8 -*-

# Copyright 2020 Google LLC
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
#

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
import proto  # type: ignore


from google.cloud.spanner_v1.types import keys
from google.protobuf import struct_pb2 as struct  # type: ignore


__protobuf__ = proto.module(package="google.spanner.v1", manifest={"Mutation",},)


class Mutation(proto.Message):
    r"""A modification to one or more Cloud Spanner rows. Mutations can be
    applied to a Cloud Spanner database by sending them in a
    [Commit][google.spanner.v1.Spanner.Commit] call.

    Attributes:
        insert (~.mutation.Mutation.Write):
            Insert new rows in a table. If any of the rows already
            exist, the write or transaction fails with error
            ``ALREADY_EXISTS``.
        update (~.mutation.Mutation.Write):
            Update existing rows in a table. If any of the rows does not
            already exist, the transaction fails with error
            ``NOT_FOUND``.
        insert_or_update (~.mutation.Mutation.Write):
            Like [insert][google.spanner.v1.Mutation.insert], except
            that if the row already exists, then its column values are
            overwritten with the ones provided. Any column values not
            explicitly written are preserved.

            When using
            [insert_or_update][google.spanner.v1.Mutation.insert_or_update],
            just as when using
            [insert][google.spanner.v1.Mutation.insert], all
            ``NOT NULL`` columns in the table must be given a value.
            This holds true even when the row already exists and will
            therefore actually be updated.
        replace (~.mutation.Mutation.Write):
            Like [insert][google.spanner.v1.Mutation.insert], except
            that if the row already exists, it is deleted, and the
            column values provided are inserted instead. Unlike
            [insert_or_update][google.spanner.v1.Mutation.insert_or_update],
            this means any values not explicitly written become
            ``NULL``.

            In an interleaved table, if you create the child table with
            the ``ON DELETE CASCADE`` annotation, then replacing a
            parent row also deletes the child rows. Otherwise, you must
            delete the child rows before you replace the parent row.
        delete (~.mutation.Mutation.Delete):
            Delete rows from a table. Succeeds whether or
            not the named rows were present.
    """

    class Write(proto.Message):
        r"""Arguments to [insert][google.spanner.v1.Mutation.insert],
        [update][google.spanner.v1.Mutation.update],
        [insert_or_update][google.spanner.v1.Mutation.insert_or_update], and
        [replace][google.spanner.v1.Mutation.replace] operations.

        Attributes:
            table (str):
                Required. The table whose rows will be
                written.
            columns (Sequence[str]):
                The names of the columns in
                [table][google.spanner.v1.Mutation.Write.table] to be
                written.

                The list of columns must contain enough columns to allow
                Cloud Spanner to derive values for all primary key columns
                in the row(s) to be modified.
            values (Sequence[~.struct.ListValue]):
                The values to be written. ``values`` can contain more than
                one list of values. If it does, then multiple rows are
                written, one for each entry in ``values``. Each list in
                ``values`` must have exactly as many entries as there are
                entries in
                [columns][google.spanner.v1.Mutation.Write.columns] above.
                Sending multiple lists is equivalent to sending multiple
                ``Mutation``\ s, each containing one ``values`` entry and
                repeating [table][google.spanner.v1.Mutation.Write.table]
                and [columns][google.spanner.v1.Mutation.Write.columns].
                Individual values in each list are encoded as described
                [here][google.spanner.v1.TypeCode].
        """

        table = proto.Field(proto.STRING, number=1)

        columns = proto.RepeatedField(proto.STRING, number=2)

        values = proto.RepeatedField(proto.MESSAGE, number=3, message=struct.ListValue,)

    class Delete(proto.Message):
        r"""Arguments to [delete][google.spanner.v1.Mutation.delete] operations.

        Attributes:
            table (str):
                Required. The table whose rows will be
                deleted.
            key_set (~.keys.KeySet):
                Required. The primary keys of the rows within
                [table][google.spanner.v1.Mutation.Delete.table] to delete.
                The primary keys must be specified in the order in which
                they appear in the ``PRIMARY KEY()`` clause of the table's
                equivalent DDL statement (the DDL statement used to create
                the table). Delete is idempotent. The transaction will
                succeed even if some or all rows do not exist.
        """

        table = proto.Field(proto.STRING, number=1)

        key_set = proto.Field(proto.MESSAGE, number=2, message=keys.KeySet,)

    insert = proto.Field(proto.MESSAGE, number=1, oneof="operation", message=Write,)

    update = proto.Field(proto.MESSAGE, number=2, oneof="operation", message=Write,)

    insert_or_update = proto.Field(
        proto.MESSAGE, number=3, oneof="operation", message=Write,
    )

    replace = proto.Field(proto.MESSAGE, number=4, oneof="operation", message=Write,)

    delete = proto.Field(proto.MESSAGE, number=5, oneof="operation", message=Delete,)


__all__ = tuple(sorted(__protobuf__.manifest))
