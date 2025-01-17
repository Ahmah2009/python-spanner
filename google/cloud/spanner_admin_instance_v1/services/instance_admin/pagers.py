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

from google.cloud.spanner_admin_instance_v1.types import spanner_instance_admin


class ListInstanceConfigsPager(object):
    """A pager for iterating through ``list_instance_configs`` requests.

    This class thinly wraps an initial
    :class:`~.spanner_instance_admin.ListInstanceConfigsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``instance_configs`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListInstanceConfigs`` requests and continue to iterate
    through the ``instance_configs`` field on the
    corresponding responses.

    All the usual :class:`~.spanner_instance_admin.ListInstanceConfigsResponse`
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
            request (:class:`~.spanner_instance_admin.ListInstanceConfigsRequest`):
                The initial request object.
            response (:class:`~.spanner_instance_admin.ListInstanceConfigsResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = spanner_instance_admin.ListInstanceConfigsRequest(request)
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
            yield from page.instance_configs

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListInstanceConfigsAsyncPager(object):
    """A pager for iterating through ``list_instance_configs`` requests.

    This class thinly wraps an initial
    :class:`~.spanner_instance_admin.ListInstanceConfigsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``instance_configs`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListInstanceConfigs`` requests and continue to iterate
    through the ``instance_configs`` field on the
    corresponding responses.

    All the usual :class:`~.spanner_instance_admin.ListInstanceConfigsResponse`
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
            request (:class:`~.spanner_instance_admin.ListInstanceConfigsRequest`):
                The initial request object.
            response (:class:`~.spanner_instance_admin.ListInstanceConfigsResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = spanner_instance_admin.ListInstanceConfigsRequest(request)
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
                for response in page.instance_configs:
                    yield response

        return async_generator()

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListInstancesPager(object):
    """A pager for iterating through ``list_instances`` requests.

    This class thinly wraps an initial
    :class:`~.spanner_instance_admin.ListInstancesResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``instances`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListInstances`` requests and continue to iterate
    through the ``instances`` field on the
    corresponding responses.

    All the usual :class:`~.spanner_instance_admin.ListInstancesResponse`
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
            request (:class:`~.spanner_instance_admin.ListInstancesRequest`):
                The initial request object.
            response (:class:`~.spanner_instance_admin.ListInstancesResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = spanner_instance_admin.ListInstancesRequest(request)
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
            yield from page.instances

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListInstancesAsyncPager(object):
    """A pager for iterating through ``list_instances`` requests.

    This class thinly wraps an initial
    :class:`~.spanner_instance_admin.ListInstancesResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``instances`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListInstances`` requests and continue to iterate
    through the ``instances`` field on the
    corresponding responses.

    All the usual :class:`~.spanner_instance_admin.ListInstancesResponse`
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
            request (:class:`~.spanner_instance_admin.ListInstancesRequest`):
                The initial request object.
            response (:class:`~.spanner_instance_admin.ListInstancesResponse`):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = spanner_instance_admin.ListInstancesRequest(request)
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
                for response in page.instances:
                    yield response

        return async_generator()

    def __repr__(self):
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)
