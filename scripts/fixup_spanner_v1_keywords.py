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

from __future__ import with_statement
from __future__ import absolute_import
import argparse
import os
import libcst as cst
import pathlib
import sys
from typing import (Any, Callable, Dict, List, Sequence, Tuple)
from itertools import izip
from io import open


def partition(
    predicate,
    iterator
):
    u"""A stable, out-of-place partition."""
    results = ([], [])

    for i in iterator:
        results[int(predicate(i))].append(i)

    # Returns trueList, falseList
    return results[1], results[0]


class spannerCallTransformer(cst.CSTTransformer):
    CTRL_PARAMS: Tuple[unicode] = (u'retry', u'timeout', u'metadata')
    METHOD_TO_PARAMS: Dict[unicode, Tuple[unicode]] = {
    u'batch_create_sessions': (u'database', u'session_count', u'session_template', ),
    u'begin_transaction': (u'session', u'options', ),
    u'commit': (u'session', u'transaction_id', u'single_use_transaction', u'mutations', ),
    u'create_session': (u'database', u'session', ),
    u'delete_session': (u'name', ),
    u'execute_batch_dml': (u'session', u'transaction', u'statements', u'seqno', ),
    u'execute_sql': (u'session', u'sql', u'transaction', u'params', u'param_types', u'resume_token', u'query_mode', u'partition_token', u'seqno', u'query_options', ),
    u'execute_streaming_sql': (u'session', u'sql', u'transaction', u'params', u'param_types', u'resume_token', u'query_mode', u'partition_token', u'seqno', u'query_options', ),
    u'get_session': (u'name', ),
    u'list_sessions': (u'database', u'page_size', u'page_token', u'filter', ),
    u'partition_query': (u'session', u'sql', u'transaction', u'params', u'param_types', u'partition_options', ),
    u'partition_read': (u'session', u'table', u'key_set', u'transaction', u'index', u'columns', u'partition_options', ),
    u'read': (u'session', u'table', u'columns', u'key_set', u'transaction', u'index', u'limit', u'resume_token', u'partition_token', ),
    u'rollback': (u'session', u'transaction_id', ),
    u'streaming_read': (u'session', u'table', u'columns', u'key_set', u'transaction', u'index', u'limit', u'resume_token', u'partition_token', ),

    }

    def leave_Call(self, original, updated):
        try:
            key = original.func.attr.value
            kword_params = self.METHOD_TO_PARAMS[key]
        except (AttributeError, KeyError):
            # Either not a method from the API or too convoluted to be sure.
            return updated

        # If the existing code is valid, keyword args come after positional args.
        # Therefore, all positional args must map to the first parameters.
        args, kwargs = partition(lambda a: not bool(a.keyword), updated.args)
        if any(k.keyword.value == u"request" for k in kwargs):
            # We've already fixed this file, don't fix it again.
            return updated

        kwargs, ctrl_kwargs = partition(
            lambda a: not a.keyword.value in self.CTRL_PARAMS,
            kwargs
        )

        args, ctrl_args = args[:len(kword_params)], args[len(kword_params):]
        ctrl_kwargs.extend(cst.Arg(value=a.value, keyword=cst.Name(value=ctrl))
                           for a, ctrl in izip(ctrl_args, self.CTRL_PARAMS))

        request_arg = cst.Arg(
            value=cst.Dict([
                cst.DictElement(
                    cst.SimpleString(u"'{}'".format(name)),
                    cst.Element(value=arg.value)
                )
                # Note: the args + kwargs looks silly, but keep in mind that
                # the control parameters had to be stripped out, and that
                # those could have been passed positionally or by keyword.
                for name, arg in izip(kword_params, args + kwargs)]),
            keyword=cst.Name(u"request")
        )

        return updated.with_changes(
            args=[request_arg] + ctrl_kwargs
        )


def fix_files(
    in_dir,
    out_dir, **_3to2kwargs
):
    if 'transformer' in _3to2kwargs: transformer = _3to2kwargs['transformer']; del _3to2kwargs['transformer']
    else: transformer = spannerCallTransformer()
    u"""Duplicate the input dir to the output dir, fixing file method calls.

    Preconditions:
    * in_dir is a real directory
    * out_dir is a real, empty directory
    """
    pyfile_gen = (
        pathlib.Path(os.path.join(root, f))
        for root, _, files in os.walk(in_dir)
        for f in files if os.path.splitext(f)[1] == u".py"
    )

    for fpath in pyfile_gen:
        with open(fpath, u'r') as f:
            src = f.read()

        # Parse the code and insert method call fixes.
        tree = cst.parse_module(src)
        updated = tree.visit(transformer)

        # Create the path and directory structure for the new file.
        updated_path = out_dir.joinpath(fpath.relative_to(in_dir))
        updated_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate the updated source file at the corresponding path.
        with open(updated_path, u'w') as f:
            f.write(updated.code)


if __name__ == u'__main__':
    parser = argparse.ArgumentParser(
        description=u"""Fix up source that uses the spanner client library.

The existing sources are NOT overwritten but are copied to output_dir with changes made.

Note: This tool operates at a best-effort level at converting positional
      parameters in client method calls to keyword based parameters.
      Cases where it WILL FAIL include
      A) * or ** expansion in a method call.
      B) Calls via function or method alias (includes free function calls)
      C) Indirect or dispatched calls (e.g. the method is looked up dynamically)

      These all constitute false negatives. The tool will also detect false
      positives when an API method shares a name with another method.
""")
    parser.add_argument(
        u'-d',
        u'--input-directory',
        required=True,
        dest=u'input_dir',
        help=u'the input directory to walk for python files to fix up',
    )
    parser.add_argument(
        u'-o',
        u'--output-directory',
        required=True,
        dest=u'output_dir',
        help=u'the directory to output files fixed via un-flattening',
    )
    args = parser.parse_args()
    input_dir = pathlib.Path(args.input_dir)
    output_dir = pathlib.Path(args.output_dir)
    if not input_dir.is_dir():
        print >>sys.stderr, f"input directory '{input_dir}' does not exist or is not a directory"
        sys.exit(-1)

    if not output_dir.is_dir():
        print >>sys.stderr, f"output directory '{output_dir}' does not exist or is not a directory"
        sys.exit(-1)

    if os.listdir(output_dir):
        print >>sys.stderr, f"output directory '{output_dir}' is not empty"
        sys.exit(-1)

    fix_files(input_dir, output_dir)
