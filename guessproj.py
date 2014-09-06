#!python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import division
from __future__ import print_function

__author__ = 'Alexei Ardyakov'
__version__ = '0.01'
__license__ = 'MIT'

import codecs
import os
import re
import sys
from functools import partial
from pyproj import Proj, transform
from scipy.optimize import leastsq

try:
    from osgeo import osr # GDAL is needed for WKT output
except:
    osr = False

PY3 = sys.version_info[0] >= 3


def to_str(s):
    """Converts byte or unicode string to str type, assuming UTF-8 encoding"""
    if s is None:
        return None
    if isinstance(s, str):
        return s
    if PY3 and isinstance(s, bytes):
        return s.decode('utf-8')
    elif not PY3 and isinstance(s, unicode):
        return s.encode('utf-8')
    raise ValueError('Cannot convert {0} to str'.format(s))


def target_func_template(points, src_proj, tgt_template, params):
    """Target function template (the real target function is a result
    of partial application of the template with first 3 arguments known)
    """
    tgt_proj = tgt_template.format(*params)
    p1 = Proj(to_str(src_proj))
    p2 = Proj(to_str(tgt_proj))
    result = []
    for pt in points:
        if len(pt[0]) == 2:
            tpt = transform(p1, p2, pt[0][0], pt[0][1])
        elif len(pt[0]) == 3:
            tpt = transform(p1, p2, pt[0][0], pt[0][1], pt[0][2])
        else:
            raise ValueError('Two or three coordinates expected')
        result.append(pt[1][0] - tpt[0])
        result.append(pt[1][1] - tpt[1])
        if len(pt[0]) == 3 and len(pt[1]) == 3:
            result.append(pt[0][2] - tpt[2])
    return result
    

def find_params(src_proj, tgt_known, tgt_unknown, points):
    """Finds unknown params of target projection
    using least squares method
    """
    # Sorting params (some of them can have dot separated index)
    param_list = []
    for param_dict, is_known in ((tgt_known, True), (tgt_unknown, False)):
        for k in param_dict.keys():
            if '.' in k:
                k1, k2 = k.split('.')
                k2 = int(k2)
            else:
                k1, k2 = k, 0
            param_list.append((k1, k2, param_dict[k], is_known))
    param_list.sort()
    # Constructing target projection template
    start_values, var_names = [], []
    tgt_template = ''
    var_index = 0
    for p in param_list:
        if p[1] == 0:
            tgt_template += ' +{0}'.format(p[0])
        else:
            tgt_template += ','
        if p[3]: # Known value
            if p[2] is not None:
                if p[1] == 0:
                    tgt_template += '={0}'.format(p[2])
                else:
                    tgt_template += '{0}'.format(p[2])
        else: # Unknown value
            start_values.append(p[2])
            if p[1] == 0:
                var_names.append(p[0])
                tgt_template += '='
            else:
                var_names.append('{0}.{1}'.format(p[0], p[1]))
            tgt_template += '{' + str(var_index) + '}'
            var_index += 1
    tgt_template = tgt_template.strip()
    # Creating target function
    tgt_func = partial(target_func_template,
                       points, src_proj, tgt_template)
    # Solving the problem
    x, cov_x, infodict, mesg, ier = leastsq(
        tgt_func, start_values, ftol=1e-12, full_output=True)
    # Formatting outputs
    if ier not in (1, 2, 3, 4):
        return None, None, None
    result_projstring = tgt_template.format(*x)
    result_dict = dict(zip(var_names, x))
    fvec = infodict['fvec']
    residuals = []
    i = 0
    for pt in points:
        if len(pt[0]) == 3 and len(pt[1]) == 3:
            residuals.append(tuple(fvec[i:i + 3]))
            i += 3
        else:
            residuals.append(tuple(fvec[i:i + 2]))
            i += 2
    return result_projstring, result_dict, residuals


def parse_arguments(argv):
    """Parses command line arguments of the program"""
    src_params = []
    known, unknown, options = {}, {}, {}
    filename = None
    parsing_target = False
    for arg in argv[1:]:
        if arg.startswith('-'):
            splitarg = arg.split('=', 1)
            if len(splitarg) == 2:
                options[splitarg[0]] = splitarg[1]
            else:
                options[arg] = True
        elif parsing_target:
            if arg.startswith('+'):
                param_re = re.compile(r'^\+([0-9a-zA-Z_]+)([=~].*)?$')
                m = param_re.match(arg)
                if not m:
                    raise ValueError('Invalid parameter: {0}'.format(arg))
                pname, pvalue = m.groups()
                if not pvalue:
                    known[pname] = None
                else:
                    subvalues = pvalue.split(',')
                    for i, sv in enumerate(subvalues):
                        extpname = pname + ('.' + str(i) if i else '')
                        if sv.startswith('~'):
                            unknown[extpname] = float(sv[1:])
                        elif sv.startswith('=~'):
                            unknown[extpname] = float(sv[2:])
                        elif sv.startswith('='):
                            known[extpname] = sv[1:]
                        else:
                            known[extpname] = sv
            else:
                if filename:
                    raise ValueError('Multiple input files are not supported')
                filename = arg
        else:
            if arg == '+to':
                parsing_target = True
            elif arg.startswith('+'):
                src_params.append(arg)
            else:
                raise ValueError('Unexpected token: {0}'.format(arg))
    if src_params:
        src_proj = ' '.join(src_params)
    else:
        src_proj = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
    return (src_proj, known, unknown, options, filename)


def parse_coord(s):
    """Parses a value of coordinate"""
    # TODO: Implement DMS format
    return float(to_str(s).replace(',', '.'))


def read_points(filename, encoding='utf-8'):
    """Reads points from file"""
    points = []
    with codecs.open(filename, 'r', encoding) as fp:
        for line in fp:
            tokens = line.strip().split()
            if not tokens[0] or tokens[0].startswith('#'):
                continue
            number_count = len(tokens)
            for i, t in enumerate(tokens):
                try:
                    d = parse_coord(t)
                except:
                    number_count = i
                    break
            number_count = min((number_count, 6))
            if number_count == 5:
                number_count = 4
            if number_count < 4:
                raise ValueError('')
            tokens = line.strip().split(None, number_count)
            if number_count == 4:
                points.append((
                    tuple(map(parse_coord, tokens[0:2])),
                    tuple(map(parse_coord, tokens[2:4])),
                    tokens[4] if len(tokens) > 4 else '',
                    ))
            elif number_count == 6:
                points.append((
                    tuple(map(parse_coord, tokens[0:3])),
                    tuple(map(parse_coord, tokens[3:6])),
                    tokens[6] if len(tokens) > 6 else '',
                    ))
    return points


def print_usage():
    """Prints usage help"""
    print('Usage: python {0} [--opts] +src_opts[=arg,] '
          '+to +tgt_opts[=[~]arg,] filename'.format(
              os.path.basename(__file__)))


def print_projstring(projstring):
    """Prints the projstring :) """
    print(projstring)


def print_residuals(points, residuals):
    """Prints the residuals"""
    # TODO: Handle encoding properly
    print('Residuals:')
    for i, pt in enumerate(points):
        r = residuals[i]
        if len(r) == 2:
            print('{0}\t{1}\t\t{2}'.format(r[0], r[1], pt[2]))
        else:
            print('{0}\t{1}\t{2}\t{3}'.format(r[0], r[1], r[3], pt[2]))


def print_wkt(projstring, esri=False, pretty=False):
    """Prints projection parameters as well-known text"""
    if osr:
        srs = osr.SpatialReference()
        srs.ImportFromProj4(to_str(projstring))
        if esri:
            srs.MorphToESRI()
        print(srs.ExportToPrettyWkt() if pretty else srs.ExportToWkt())
    else:
        raise ImportError('Package GDAL not found')


if __name__ == '__main__':
    src_proj, known, unknown, options, filename = parse_arguments(sys.argv)
    if len(unknown) == 0 or options.get('-h') or options.get('--help'):
        print_usage()
        sys.exit(0)
    encoding = options.get('--encoding', 'utf-8')
    points = read_points(filename, encoding)
    result_projstring, result_dict, residuals = find_params(
        src_proj, known, unknown, points)
    # Projstring output
    if '--proj' in options or '--proj4' in options:
        if result_projstring:
            print_projstring(result_projstring)
            sys.exit(0)
        else:
            sys.exit(1)
    # OGC WKT output
    if '--wkt' in options:
        if result_projstring:
            print_wkt(result_projstring, pretty='--pretty' in options)
            sys.exit(0)
        else:
            sys.exit(1)
    # Esri WKT output
    if '--esri' in options:
        if result_projstring:
            print_wkt(result_projstring, esri=True,
                      pretty='--pretty' in options)
            sys.exit(0)
        else:
            sys.exit(1)
    # Default output
    if result_projstring is None:
        print('Solution not found')
        sys.exit(1)
    print_projstring(result_projstring)
    print_residuals(points, residuals)
    sys.exit(0)