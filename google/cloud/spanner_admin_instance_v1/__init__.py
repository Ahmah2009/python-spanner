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
from .services.instance_admin import InstanceAdminClient
from .types.spanner_instance_admin import CreateInstanceMetadata
from .types.spanner_instance_admin import CreateInstanceRequest
from .types.spanner_instance_admin import DeleteInstanceRequest
from .types.spanner_instance_admin import GetInstanceConfigRequest
from .types.spanner_instance_admin import GetInstanceRequest
from .types.spanner_instance_admin import Instance
from .types.spanner_instance_admin import InstanceConfig
from .types.spanner_instance_admin import ListInstanceConfigsRequest
from .types.spanner_instance_admin import ListInstanceConfigsResponse
from .types.spanner_instance_admin import ListInstancesRequest
from .types.spanner_instance_admin import ListInstancesResponse
from .types.spanner_instance_admin import ReplicaInfo
from .types.spanner_instance_admin import UpdateInstanceMetadata
from .types.spanner_instance_admin import UpdateInstanceRequest


__all__ = (
    "CreateInstanceMetadata",
    "CreateInstanceRequest",
    "DeleteInstanceRequest",
    "GetInstanceConfigRequest",
    "GetInstanceRequest",
    "Instance",
    "InstanceConfig",
    "ListInstanceConfigsRequest",
    "ListInstanceConfigsResponse",
    "ListInstancesRequest",
    "ListInstancesResponse",
    "ReplicaInfo",
    "UpdateInstanceMetadata",
    "UpdateInstanceRequest",
    "InstanceAdminClient",
)
