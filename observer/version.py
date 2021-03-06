#!/usr/bin/env python3
# coding=utf-8
# by nearg1e (nearg1e.com@gmail[dot]com)
"""
about version.

"""

import sys
from functools import cmp_to_key
from distutils.version import LooseVersion

from utils.common import remove_blank
from utils.common import IS_PY3
from utils.log import LOGGER as logger
from ext.terminaltables import AsciiTable

from .calls import show_output

# reverse: operator
OPERATOR_MAP = {
    True: "<=",
    False: ">="
}


def str2version(version):
    """to version"""
    if IS_PY3:
        str_types = str
    else:
        str_types = (unicode, str, basestring)
    
    if isinstance(version, str_types):
        return LooseVersion(remove_blank(version))

    return version


def match(static_map, fingerprint):
    """return if fingerprint match or not."""
    def _gen_match():
        for path, filehash in fingerprint.items():
            real_hash = static_map.get(path)
            # LICENSE or file change will make real_hash different
            if filehash and real_hash:
                yield real_hash == filehash
    all_match = [mat for mat in _gen_match()]
    return all_match and all(all_match)


def make_version(static_map, fingerprint_map, reverse=True):
    """
    return version expression. compare to each version fingerprint.
    make compare expressions. like [(">=", 'v2.3.3.3')]
    """
    version_compare_set = set()
    key_lst = fingerprint_map.keys()
    version_lst = sorted([str2version(ver_) for ver_ in key_lst], reverse=reverse)

    # head version in reverse version list is different
    head_version_str = version_lst[0].vstring
    fingerprint = head_fingerprint = fingerprint_map.get(head_version_str)
    match_head = match(static_map, head_fingerprint)
    if match_head and reverse:
        version_compare_set.add(('>', version_lst[1].vstring))
    elif match_head and not reverse:
        version_compare_set.add(('>=', head_version_str))

    for version in version_lst[1:]:
        logger.debug('create operator in version: %s', version.vstring)
        fingerprint.update(fingerprint_map.get(version.vstring))
        if match(static_map, fingerprint):
            operator = OPERATOR_MAP.get(reverse)
            version_compare_set.add((operator, version.vstring))
            logger.verbose(
                'create version opreator: %s %s',
                operator, version.vstring
            )
    logger.debug("operator: %s", version_compare_set)
    return version_compare_set


def make_all(static_map, fingerprint):
    """call the make_version"""
    version_compare_set = set()
    version_compare_set.update(
        make_version(static_map, fingerprint.get('fingerprint'))
    )
    version_compare_set.update(
        make_version(static_map, fingerprint.get('reverse_fingerprint'), False)
    )
    return version_compare_set


def version_compare_sort(prev_, next_):
    """
    version compare sort cmp function.
    compare version first and operate next.
    """
    def _cmp(pre, nex):
        return (pre > nex) - (pre < nex)

    if prev_[1] != next_[1]:
        return _cmp(str2version(prev_[1]), str2version(next_[1]))
    if prev_[0].strip('=') == '>':
        return -1
    return 1


def calc(version_compare_set):
    """calcute version compare list."""

    def _check(version_compare_lst):
        compare_lst = ['>']
        # avoid [>= 1.1, <= 1.0]
        for compare, _ in version_compare_lst:
            compare = compare.strip('=')
            if compare != compare_lst[-1]:
                compare_lst.append(compare)
        length = len(compare_lst)
        if version_compare_lst and 0 < length < 3:
            return True
        logger.warning('maybe framework or cms had be change by developer')
        if len(version_compare_lst) < 1:
            logger.warning('Reducing depth(--depth), set smaller number maybe useful')
            logger.error('unable to judge version')
            sys.exit()
        elif length > 2:
            logger.warning('Enlarge depth(--depth), set larger number or max(0) maybe useful')
            lst = [('version cond',)]
            for comb, ver in version_compare_lst:
                lst.append(('{} {}'.format(comb, ver),))
            show_output(AsciiTable(lst).table)
            sys.exit()

    lst = list(version_compare_set)
    lst.sort(key=cmp_to_key(version_compare_sort))
    logger.verbose('compare list after sort: %s', lst)
    if _check(lst):
        if len(lst) == 1:
            show_output(' '.join(lst[0]))
            return lst
        for prev_, next_ in zip(lst[:-1], lst[1:]):
            if prev_[0].strip('=') == '>' \
                and next_[0].strip('=') == '<':
                lst = [
                    ('version cond',),
                    ('{} {}'.format(*prev_),),
                    ('{} {}'.format(*next_),)
                ]
                show_output(AsciiTable(lst).table)
                return [prev_, next_]
        if lst[0][0].strip('=') == ">":
            res = lst[-1]
        else:
            res = lst[0]
        show_output(' '.join(res))
        return (res, )
    sys.exit()
