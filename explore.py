import os
import sys
import re

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import rawparse
import rawid

#rawdir = os.path.join(libdir, '../../vanilla/raw/objects/')
rawdir = os.path.join(libdir, '../../dorfraw/raw/objects/')
ridx = rawid.Rindex(rawroot=rawdir, verbosity=0, strict=True)

# useful things

def find_tag(tag, search_args=False, p=True, r=False):
    if r:
        results = []
    for ns in ridx.namespaces:
        for ro in ns:
            if search_args:
                if any(tag in tags for tags in ro):
                    if p:
                        print(ns.name, ro.ident)
                    if r:
                        results.append(ro)
            else:
                if tag in ro:
                    if p:
                        print(ns.name, ro.ident)
                    if r:
                        results.append(ro)
    if r:
        return results

def get_tag(tag, search_args=False):
    return find_tag(tag, search_args=search_args, p=False, r=True)

def filter_tag(ros, tag, search_args=False):
    new_ros = []
    for ro in ros:
        if search_args:
            if any(tag in tags for tags in ro):
                new_ros.append(ro)
        else:
            if tag in ro:
                new_ros.append(ro)
    return new_ros

def print_ros(ros):
    for ro in ros:
        print(ro.namespace.name, ro.ident)

# repair passes

nonident_re = re.compile(r'[^A-Z0-9_-]')

def fix_ident(ident):
    if ', ' in ident:
        if ident.startswith('BAMBOO'):
            fixed = ident.replace(', ', '_')
        else:
            halves = ident.split(', ')
            assert len(halves) == 2
            fixed = halves[1] + '_' + halves[0]
    else:
        fixed = ident
    fixed = fixed.replace(' ', '_')
    fixed = fixed.replace("'", '')
    return fixed

def fix_spaces_in_ids(ridx):
    xlat = {}

    for ro in ridx.objects:
        if nonident_re.search(ro.ident):
            xlat[ro.ident] = fix_ident(ro.ident)
        for tags in ro:
            if nonident_re.search(tags[0]):
                xlat[tags[0]] = fix_ident(tags[0])

    # for k in xlat:
    #     print('{:30s} -> {:30s}'.format(k, xlat[k]))
    
    print('mapping has {:d} entries'.format(len(xlat)))

    replacements = 0
    for ro in ridx.objects:
        if ro.ident in xlat:
            ro.ident = xlat[ro.ident]
            replacements += 1
        for tags in ro:
            for i in range(len(tags)):
                if tags[i] in xlat:
                    tags[i] = xlat[tags[i]]
                    replacements += 1

    print('replaced {:d} tags'.format(replacements))
