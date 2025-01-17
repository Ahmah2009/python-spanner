from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import object
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

from typing import Any, AsyncIterable, Awaitable, Callable, Iterable, Sequence, Tuple

from google.cloud.spanner_admin_database_v1.types import backup
from google.cloud.spanner_admin_database_v1.types import spanner_database_admin
from google.longrunning import operations_pb2 as operations  # type: ignore


class ListDatabasesPager(object):
    """A pager for iterating through ``list_databases`` requests.

    This class thinly wraps an initial
    :class:`~.spanner_database_admin.ListDatabasesResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``databases`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListDatabases`` requests and continue to iterate
    through the ``databases`` field on the
    corresponding responses.

    All the usual :class:`~.spanner_database_admin.ListDatabasesResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method,
        request,
        response, **_3to2kwargs
    ):
        if 'metadata' in _3to2kwargs: metadata = _3to2kwargs['metadata']; del _3to2kwargs['metadata']
        else: metadata =  ()
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (:class:`~.spanner_database_admin.ListDatabasesRequest`):
                The initial request object.
            response (:class:`~.spanner_database_admin.ListDatabasesResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = spanner_database_admin.ListDatabasesRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    def pages(self):
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self):
        for page in self.pages:
            yield from page.databases

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListDatabasesAsyncPager(object):
    """A pager for iterating through ``list_databases`` requests.

    This class thinly wraps an initial
    :class:`~.spanner_database_admin.ListDatabasesResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``databases`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListDatabases`` requests and continue to iterate
    through the ``databases`` field on the
    corresponding responses.

    All the usual :class:`~.spanner_database_admin.ListDatabasesResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method,
        request,
        response, **_3to2kwargs
    ):
        if 'metadata' in _3to2kwargs: metadata = _3to2kwargs['metadata']; del _3to2kwargs['metadata']
        else: metadata =  ()
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (:class:`~.spanner_database_admin.ListDatabasesRequest`):
                The initial request object.
            response (:class:`~.spanner_database_admin.ListDatabasesResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = spanner_database_admin.ListDatabasesRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    async def pages(
        self,
    ):
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self):
        async def async_generator():
            async for page in self.pages:
                for response in page.databases:
                    yield response

        return async_generator()

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListBackupsPager(object):
    """A pager for iterating through ``list_backups`` requests.

    This class thinly wraps an initial
    :class:`~.backup.ListBackupsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``backups`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListBackups`` requests and continue to iterate
    through the ``backups`` field on the
    corresponding responses.

    All the usual :class:`~.backup.ListBackupsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method,
        request,
        response, **_3to2kwargs
    ):
        if 'metadata' in _3to2kwargs: metadata = _3to2kwargs['metadata']; del _3to2kwargs['metadata']
        else: metadata =  ()
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (:class:`~.backup.ListBackupsRequest`):
                The initial request object.
            response (:class:`~.backup.ListBackupsResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = backup.ListBackupsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    def pages(self):
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self):
        for page in self.pages:
            yield from page.backups

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListBackupsAsyncPager(object):
    """A pager for iterating through ``list_backups`` requests.

    This class thinly wraps an initial
    :class:`~.backup.ListBackupsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``backups`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListBackups`` requests and continue to iterate
    through the ``backups`` field on the
    corresponding responses.

    All the usual :class:`~.backup.ListBackupsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method,
        request,
        response, **_3to2kwargs
    ):
        if 'metadata' in _3to2kwargs: metadata = _3to2kwargs['metadata']; del _3to2kwargs['metadata']
        else: metadata =  ()
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (:class:`~.backup.ListBackupsRequest`):
                The initial request object.
            response (:class:`~.backup.ListBackupsResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = backup.ListBackupsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    async def pages(self):
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self):
        async def async_generator():
            async for page in self.pages:
                for response in page.backups:
                    yield response

        return async_generator()

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListDatabaseOperationsPager(object):
    """A pager for iterating through ``list_database_operations`` requests.

    This class thinly wraps an initial
    :class:`~.spanner_database_admin.ListDatabaseOperationsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``operations`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListDatabaseOperations`` requests and continue to iterate
    through the ``operations`` field on the
    corresponding responses.

    All the usual :class:`~.spanner_database_admin.ListDatabaseOperationsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method,
        request,
        response, **_3to2kwargs
    ):
        if 'metadata' in _3to2kwargs: metadata = _3to2kwargs['metadata']; del _3to2kwargs['metadata']
        else: metadata =  ()
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (:class:`~.spanner_database_admin.ListDatabaseOperationsRequest`):
                The initial request object.
            response (:class:`~.spanner_database_admin.ListDatabaseOperationsResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = spanner_database_admin.ListDatabaseOperationsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    def pages(self):
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self):
        for page in self.pages:
            yield from page.operations

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListDatabaseOperationsAsyncPager(object):
    """A pager for iterating through ``list_database_operations`` requests.

    This class thinly wraps an initial
    :class:`~.spanner_database_admin.ListDatabaseOperationsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``operations`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListDatabaseOperations`` requests and continue to iterate
    through the ``operations`` field on the
    corresponding responses.

    All the usual :class:`~.spanner_database_admin.ListDatabaseOperationsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method,
        request,
        response, **_3to2kwargs
    ):
        if 'metadata' in _3to2kwargs: metadata = _3to2kwargs['metadata']; del _3to2kwargs['metadata']
        else: metadata =  ()
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (:class:`~.spanner_database_admin.ListDatabaseOperationsRequest`):
                The initial request object.
            response (:class:`~.spanner_database_admin.ListDatabaseOperationsResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = spanner_database_admin.ListDatabaseOperationsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    async def pages(
        self,
    ):
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self):
        async def async_generator():
            async for page in self.pages:
                for response in page.operations:
                    yield response

        return async_generator()

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListBackupOperationsPager(object):
    """A pager for iterating through ``list_backup_operations`` requests.

    This class thinly wraps an initial
    :class:`~.backup.ListBackupOperationsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``operations`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListBackupOperations`` requests and continue to iterate
    through the ``operations`` field on the
    corresponding responses.

    All the usual :class:`~.backup.ListBackupOperationsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method,
        request,
        response, **_3to2kwargs
    ):
        if 'metadata' in _3to2kwargs: metadata = _3to2kwargs['metadata']; del _3to2kwargs['metadata']
        else: metadata =  ()
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (:class:`~.backup.ListBackupOperationsRequest`):
                The initial request object.
            response (:class:`~.backup.ListBackupOperationsResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = backup.ListBackupOperationsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    def pages(self):
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self):
        for page in self.pages:
            yield from page.operations

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListBackupOperationsAsyncPager(object):
    """A pager for iterating through ``list_backup_operations`` requests.

    This class thinly wraps an initial
    :class:`~.backup.ListBackupOperationsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``operations`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListBackupOperations`` requests and continue to iterate
    through the ``operations`` field on the
    corresponding responses.

    All the usual :class:`~.backup.ListBackupOperationsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method,
        request,
        response, **_3to2kwargs
    ):
        if 'metadata' in _3to2kwargs: metadata = _3to2kwargs['metadata']; del _3to2kwargs['metadata']
        else: metadata =  ()
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (:class:`~.backup.ListBackupOperationsRequest`):
                The initial request object.
            response (:class:`~.backup.ListBackupOperationsResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = backup.ListBackupOperationsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    async def pages(self):
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self):
        async def async_generator():
            async for page in self.pages:
                for response in page.operations:
                    yield response

        return async_generator()

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)
