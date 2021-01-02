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
from __future__ import absolute_import

import pkg_resources

__version__ = pkg_resources.get_distribution(u"google-cloud-spanner").version

from .services.spanner import SpannerClient
from .types.keys import KeyRange as KeyRangePB
from .types.keys import KeySet as KeySetPB
from .types.mutation import Mutation
from .types.query_plan import PlanNode
from .types.query_plan import QueryPlan
from .types.result_set import PartialResultSet
from .types.result_set import ResultSet
from .types.result_set import ResultSetMetadata
from .types.result_set import ResultSetStats
from .types.spanner import BatchCreateSessionsRequest
from .types.spanner import BatchCreateSessionsResponse
from .types.spanner import BeginTransactionRequest
from .types.spanner import CommitRequest
from .types.spanner import CommitResponse
from .types.spanner import CreateSessionRequest
from .types.spanner import DeleteSessionRequest
from .types.spanner import ExecuteBatchDmlRequest
from .types.spanner import ExecuteBatchDmlResponse
from .types.spanner import ExecuteSqlRequest
from .types.spanner import GetSessionRequest
from .types.spanner import ListSessionsRequest
from .types.spanner import ListSessionsResponse
from .types.spanner import Partition
from .types.spanner import PartitionOptions
from .types.spanner import PartitionQueryRequest
from .types.spanner import PartitionReadRequest
from .types.spanner import PartitionResponse
from .types.spanner import ReadRequest
from .types.spanner import RollbackRequest
from .types.spanner import Session
from .types.transaction import Transaction
from .types.transaction import TransactionOptions
from .types.transaction import TransactionSelector
from .types.type import StructType
from .types.type import Type
from .types.type import TypeCode

from google.cloud.spanner_v1 import param_types
from google.cloud.spanner_v1.client import Client
from google.cloud.spanner_v1.keyset import KeyRange
from google.cloud.spanner_v1.keyset import KeySet
from google.cloud.spanner_v1.pool import AbstractSessionPool
from google.cloud.spanner_v1.pool import BurstyPool
from google.cloud.spanner_v1.pool import FixedSizePool
from google.cloud.spanner_v1.pool import PingingPool
from google.cloud.spanner_v1.pool import TransactionPingingPool


COMMIT_TIMESTAMP = u"spanner.commit_timestamp()"
u"""Placeholder be used to store commit timestamp of a transaction in a column.
This value can only be used for timestamp columns that have set the option
``(allow_commit_timestamp=true)`` in the schema.
"""


__all__ = (
    # google.cloud.spanner_v1
    u"__version__",
    u"param_types",
    # google.cloud.spanner_v1.client
    u"Client",
    # google.cloud.spanner_v1.keyset
    u"KeyRange",
    u"KeySet",
    # google.cloud.spanner_v1.pool
    u"AbstractSessionPool",
    u"BurstyPool",
    u"FixedSizePool",
    u"PingingPool",
    u"TransactionPingingPool",
    # local
    u"COMMIT_TIMESTAMP",
    # google.cloud.spanner_v1.types
    u"BatchCreateSessionsRequest",
    u"BatchCreateSessionsResponse",
    u"BeginTransactionRequest",
    u"CommitRequest",
    u"CommitResponse",
    u"CreateSessionRequest",
    u"DeleteSessionRequest",
    u"ExecuteBatchDmlRequest",
    u"ExecuteBatchDmlResponse",
    u"ExecuteSqlRequest",
    u"GetSessionRequest",
    u"KeyRangePB",
    u"KeySetPB",
    u"ListSessionsRequest",
    u"ListSessionsResponse",
    u"Mutation",
    u"PartialResultSet",
    u"Partition",
    u"PartitionOptions",
    u"PartitionQueryRequest",
    u"PartitionReadRequest",
    u"PartitionResponse",
    u"PlanNode",
    u"QueryPlan",
    u"ReadRequest",
    u"ResultSet",
    u"ResultSetMetadata",
    u"ResultSetStats",
    u"RollbackRequest",
    u"Session",
    u"StructType",
    u"Transaction",
    u"TransactionOptions",
    u"TransactionSelector",
    u"Type",
    u"TypeCode",
    # google.cloud.spanner_v1.services
    u"SpannerClient",
)
