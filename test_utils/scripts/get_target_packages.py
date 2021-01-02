# Copyright 2017 Google LLC
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

u"""Print a list of packages which require testing."""

from __future__ import absolute_import
import os
import re
import subprocess
import warnings


CURRENT_DIR = os.path.realpath(os.path.dirname(__file__))
BASE_DIR = os.path.realpath(os.path.join(CURRENT_DIR, u'..', u'..'))
GITHUB_REPO = os.environ.get(u'GITHUB_REPO', u'google-cloud-python')
CI = os.environ.get(u'CI', u'')
CI_BRANCH = os.environ.get(u'CIRCLE_BRANCH')
CI_PR = os.environ.get(u'CIRCLE_PR_NUMBER')
CIRCLE_TAG = os.environ.get(u'CIRCLE_TAG')
head_hash, head_name = subprocess.check_output([u'git', u'show-ref', u'HEAD']
).strip().decode(u'ascii').split()
rev_parse = subprocess.check_output(
    [u'git', u'rev-parse', u'--abbrev-ref', u'HEAD']
).strip().decode(u'ascii')
MAJOR_DIV = u'#' * 78
MINOR_DIV = u'#' + u'-' * 77

# NOTE: This reg-ex is copied from ``get_tagged_packages``.
TAG_RE = re.compile(ur"""
    ^
    (?P<pkg>
        (([a-z]+)-)*)            # pkg-name-with-hyphens- (empty allowed)
    ([0-9]+)\.([0-9]+)\.([0-9]+)  # Version x.y.z (x, y, z all ints)
    $
""", re.VERBOSE)

# This is the current set of dependencies by package.
# As of this writing, the only "real" dependency is that of error_reporting
# (on logging), the rest are just system test dependencies.
PKG_DEPENDENCIES = {
    u'logging': set([u'pubsub']),
}


def get_baseline():
    u"""Return the baseline commit.

    On a pull request, or on a branch, return the common parent revision
    with the master branch.

    Locally, return a value pulled from environment variables, or None if
    the environment variables are not set.

    On a push to master, return None. This will effectively cause everything
    to be considered to be affected.
    """

    # If this is a pull request or branch, return the tip for master.
    # We will test only packages which have changed since that point.
    ci_non_master = (CI == u'true') and any([CI_BRANCH != u'master', CI_PR])

    if ci_non_master:

        repo_url = u'git@github.com:GoogleCloudPlatform/{}'.format(GITHUB_REPO)
        subprocess.run([u'git', u'remote', u'add', u'baseline', repo_url],
                        stderr=subprocess.DEVNULL)
        subprocess.run([u'git', u'pull', u'baseline'], stderr=subprocess.DEVNULL)

        if CI_PR is None and CI_BRANCH is not None:
            output = subprocess.check_output([
                u'git', u'merge-base', u'--fork-point',
                u'baseline/master', CI_BRANCH])
            return output.strip().decode(u'ascii')

        return u'baseline/master'

    # If environment variables are set identifying what the master tip is,
    # use that.
    if os.environ.get(u'GOOGLE_CLOUD_TESTING_REMOTE', u''):
        remote = os.environ[u'GOOGLE_CLOUD_TESTING_REMOTE']
        branch = os.environ.get(u'GOOGLE_CLOUD_TESTING_BRANCH', u'master')
        return u'%s/%s' % (remote, branch)

    # If we are not in CI and we got this far, issue a warning.
    if not CI:
        warnings.warn(u'No baseline could be determined; this means tests '
                      u'will run for every package. If this is local '
                      u'development, set the $GOOGLE_CLOUD_TESTING_REMOTE '
                      u'environment variable.')

    # That is all we can do; return None.
    return None


def get_changed_files():
    u"""Return a list of files that have been changed since the baseline.

    If there is no base, return None.
    """
    # Get the baseline, and fail quickly if there is no baseline.
    baseline = get_baseline()
    print u'# Baseline commit: {}'.format(baseline)
    if not baseline:
        return None

    # Return a list of altered files.
    try:
        return subprocess.check_output([
            u'git', u'diff', u'--name-only', u'{}..HEAD'.format(baseline),
        ], stderr=subprocess.DEVNULL).decode(u'utf8').strip().split(u'\n')
    except subprocess.CalledProcessError:
        warnings.warn(u'Unable to perform git diff; falling back to assuming '
                      u'all packages have changed.')
        return None


def reverse_map(dict_of_sets):
    u"""Reverse a map of one-to-many.

    So the map::

      {
        'A': {'B', 'C'},
        'B': {'C'},
      }

    becomes

      {
        'B': {'A'},
        'C': {'A', 'B'},
      }

    Args:
        dict_of_sets (dict[set]): A dictionary of sets, mapping
            one value to many.

    Returns:
        dict[set]: The reversed map.
    """
    result = {}
    for key, values in dict_of_sets.items():
        for value in values:
            result.setdefault(value, set()).add(key)

    return result

def get_changed_packages(file_list):
    u"""Return a list of changed packages based on the provided file list.

    If the file list is None, then all packages should be considered to be
    altered.
    """
    # Determine a complete list of packages.
    all_packages = set()
    for file_ in os.listdir(BASE_DIR):
        abs_file = os.path.realpath(os.path.join(BASE_DIR, file_))
        nox_file = os.path.join(abs_file, u'nox.py')
        if os.path.isdir(abs_file) and os.path.isfile(nox_file):
            all_packages.add(file_)

    # If ther is no file list, send down the full package set.
    if file_list is None:
        return all_packages

    # Create a set based on the list of changed files.
    answer = set()
    reverse_deps = reverse_map(PKG_DEPENDENCIES)
    for file_ in file_list:
        # Ignore root directory changes (setup.py, .gitignore, etc.).
        if os.path.sep not in file_:
            continue

        # Ignore changes that are not in a package (usually this will be docs).
        package = file_.split(os.path.sep, 1)[0]
        if package not in all_packages:
            continue

        # If there is a change in core, short-circuit now and return
        # everything.
        if package in (u'core',):
            return all_packages

        # Add the package, as well as any dependencies this package has.
        # NOTE: For now, dependencies only go down one level.
        answer.add(package)
        answer = answer.union(reverse_deps.get(package, set()))

    # We got this far without being short-circuited; return the final answer.
    return answer


def get_tagged_package():
    u"""Return the package corresponding to the current tag.

    If there is not tag, will return :data:`None`.
    """
    if CIRCLE_TAG is None:
        return

    match = TAG_RE.match(CIRCLE_TAG)
    if match is None:
        return

    pkg_name = match.group(u'pkg')
    if pkg_name == u'':
        # NOTE: This corresponds to the "umbrella" tag.
        return

    return pkg_name.rstrip(u'-').replace(u'-', u'_')


def get_target_packages():
    u"""Return a list of target packages to be run in the current build.

    If in a tag build, will run only the package(s) that are tagged, otherwise
    will run the packages that have file changes in them (or packages that
    depend on those).
    """
    tagged_package = get_tagged_package()
    if tagged_package is None:
        file_list = get_changed_files()
        print MAJOR_DIV
        print u'# Changed files:'
        print MINOR_DIV
        for file_ in file_list or ():
            print u'#  {}'.format(file_)
        for package in sorted(get_changed_packages(file_list)):
            yield package
    else:
        yield tagged_package


def main():
    print MAJOR_DIV
    print u'# Environment'
    print MINOR_DIV
    print u'# CircleCI:        {}'.format(CI)
    print u'# CircleCI branch: {}'.format(CI_BRANCH)
    print u'# CircleCI pr:     {}'.format(CI_PR)
    print u'# CircleCI tag:    {}'.format(CIRCLE_TAG)
    print u'# HEAD ref:        {}'.format(head_hash)
    print u'#                  {}'.format(head_name)
    print u'# Git branch:      {}'.format(rev_parse)
    print MAJOR_DIV

    packages = list(get_target_packages())

    print MAJOR_DIV
    print u'# Target packages:'
    print MINOR_DIV
    for package in packages:
       print package
    print MAJOR_DIV


if __name__ == u'__main__':
    main()
