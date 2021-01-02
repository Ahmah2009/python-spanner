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

u"""Spanner DB API exceptions."""


class Warning(Exception):
    u"""Important DB API warning."""

    pass


class Error(Exception):
    u"""The base class for all the DB API exceptions.

    Does not include :class:`Warning`.
    """

    pass


class InterfaceError(Error):
    u"""
    Error related to the database interface
    rather than the database itself.
    """

    pass


class DatabaseError(Error):
    u"""Error related to the database."""

    pass


class DataError(DatabaseError):
    u"""
    Error due to problems with the processed data like
    division by zero, numeric value out of range, etc.
    """

    pass


class OperationalError(DatabaseError):
    u"""
    Error related to the database's operation, e.g. an
    unexpected disconnect, the data source name is not
    found, a transaction could not be processed, a
    memory allocation error, etc.
    """

    pass


class IntegrityError(DatabaseError):
    u"""
    Error for cases of relational integrity of the database
    is affected, e.g. a foreign key check fails.
    """

    pass


class InternalError(DatabaseError):
    u"""
    Internal database error, e.g. the cursor is not valid
    anymore, the transaction is out of sync, etc.
    """

    pass


class ProgrammingError(DatabaseError):
    u"""
    Programming error, e.g. table not found or already
    exists, syntax error in the SQL statement, wrong
    number of parameters specified, etc.
    """

    pass


class NotSupportedError(DatabaseError):
    u"""
    Error for case of a method or database API not
    supported by the database was used.
    """

    pass
