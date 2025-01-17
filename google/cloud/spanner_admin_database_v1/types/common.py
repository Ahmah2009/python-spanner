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


from google.protobuf import timestamp_pb2 as timestamp  # type: ignore


__protobuf__ = proto.module(
    package="google.spanner.admin.database.v1", manifest={"OperationProgress",},
)


class OperationProgress(proto.Message):
    r"""Encapsulates progress related information for a Cloud Spanner
    long running operation.

    Attributes:
        progress_percent (int):
            Percent completion of the operation.
            Values are between 0 and 100 inclusive.
        start_time (~.timestamp.Timestamp):
            Time the request was received.
        end_time (~.timestamp.Timestamp):
            If set, the time at which this operation
            failed or was completed successfully.
    """

    progress_percent = proto.Field(proto.INT32, number=1)

    start_time = proto.Field(proto.MESSAGE, number=2, message=timestamp.Timestamp,)

    end_time = proto.Field(proto.MESSAGE, number=3, message=timestamp.Timestamp,)


__all__ = tuple(sorted(__protobuf__.manifest))
