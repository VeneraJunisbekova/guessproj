#!python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import os
import subprocess
try:
    import unittest2 as unittest
except:
    import unittest

import guessproj

class TestFunctions(unittest.TestCase):

    def setUp(self):
        """Setup test case"""

    def test_to_str(self):
        """to_str() function converts byte or Unicode string to str type"""
        self.assertIsNone(guessproj.to_str(None))
        self.assertIsInstance(guessproj.to_str(b'+lon_0=39.0'), str)
        self.assertIsInstance(guessproj.to_str(u'+lon_0=39.0'), str)
        self.assertIsInstance(
            guessproj.to_str(b'\xef', encoding='cp1251'), str)
        self.assertIsInstance(
            guessproj.to_str(u'\u043f', encoding='cp1251'), str)
        self.assertEqual(
            guessproj.to_str(u'\u043f', encoding='cp1251'),
            guessproj.to_str(b'\xef', encoding='cp1251')
            )
        self.assertRaises(ValueError, lambda: guessproj.to_str(True))
        
    def test_to_unicode(self):
        """to_unicode() function converts byte or Unicode string to Unicode"""
        utype = type(u'a')
        self.assertIsNone(guessproj.to_unicode(None))
        self.assertIsInstance(guessproj.to_unicode(b'+lon_0=39.0'), utype)
        self.assertIsInstance(guessproj.to_unicode(u'+lon_0=39.0'), utype)
        self.assertIsInstance(
            guessproj.to_unicode(b'\xef', encoding='cp1251'), utype)
        self.assertIsInstance(
            guessproj.to_unicode(u'\u043f', encoding='cp1251'), utype)
        self.assertEqual(
            guessproj.to_unicode(u'\u043f', encoding='cp1251'),
            guessproj.to_unicode(b'\xef', encoding='cp1251')
            )
        self.assertRaises(ValueError, lambda: guessproj.to_unicode(True))
        
    def test_parse_coord(self):
        """Test parse_coord() function"""
        self.assertEqual(guessproj.parse_coord(u'12.15'), 12.15)
        self.assertEqual(guessproj.parse_coord(b'12.15'), 12.15)
        self.assertEqual(guessproj.parse_coord(u'-13'), -13)
        self.assertEqual(guessproj.parse_coord(b'-13'), -13)
        self.assertEqual(guessproj.parse_coord(u'56,25'), 56.25)
        self.assertEqual(guessproj.parse_coord(b'56,25'), 56.25)
        self.assertEqual(guessproj.parse_coord(b'0'), 0)
        self.assertEqual(guessproj.parse_coord(u'150d7\'30"'), 150.125)
        self.assertEqual(guessproj.parse_coord(u'+150d7\'30"'), 150.125)
        self.assertEqual(guessproj.parse_coord(u'-150d7\'30"'), -150.125)
        self.assertEqual(guessproj.parse_coord(u'-0d'), 0)
        self.assertEqual(guessproj.parse_coord(u'-7\'30"'), -0.125)
        self.assertEqual(guessproj.parse_coord(u'-30"'), -1 / 120.0)
        self.assertEqual(guessproj.parse_coord(b'-123,456d'), -123.456)
        self.assertEqual(guessproj.parse_coord(b'+175d07.5\''), 175.125)
        self.assertEqual(guessproj.parse_coord(b'-7,5\''), -0.125)
        self.assertRaises(TypeError, lambda: guessproj.parse_coord(None))
        self.assertRaises(ValueError, lambda: guessproj.parse_coord(u''))
        self.assertRaises(ValueError, lambda: guessproj.parse_coord(u'1d2m3s'))
        self.assertRaises(ValueError, lambda: guessproj.parse_coord(u'-'))
        self.assertRaises(ValueError, lambda: guessproj.parse_coord(u'--2d'))
        self.assertRaises(ValueError, lambda: guessproj.parse_coord(u'6-1'))
        self.assertRaises(
            ValueError, lambda: guessproj.parse_coord(b'1d60\'0"'))
        self.assertRaises(
            ValueError, lambda: guessproj.parse_coord(b'-140d09\'60.5"'))

    def test_read_points(self):
        """read_points() function reads points data from a text file"""
        # TODO: Implement test that covers all features
        filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'four_points.txt'
            )
        points = guessproj.read_points(filename, 'cp1251')
        self.assertEqual(len(points), 4)
        pt0 = points[0]
        self.assertEqual(len(pt0), 3)
        pair1, pair2, name = pt0
        self.assertEqual(len(pair1), 2)
        self.assertEqual(len(pair2), 2)
        self.assertAlmostEqual(pair1[0], 39, places=8)
        self.assertAlmostEqual(pair1[1], 47, places=8)
        self.assertAlmostEqual(pair2[0], 3e5, places=3)
        self.assertAlmostEqual(pair2[1], 207338.73, places=3)
        self.assertEqual(name, 'pt1')
        
    def test_read_points_from_iterable(self):
        data = [
            '''# Point list''',
            ''' 39d30'00" 56d07'30" 50.6  20000.0 35000.5 52 \u043f_1''',
            b'''40,17d    56d07,5'  60,6 100000,0 35000,5 62 \xd0\xbf_2''',
            ]
        points = guessproj.read_points_from_iterable(data)
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0][0], (39.5, 56.125, 50.6))
        self.assertEqual(points[0][1], (20000.0, 35000.5, 52.0))
        self.assertEqual(points[0][2], '\u043f_1')
        self.assertEqual(points[1][0], (40.17, 56.125, 60.6))
        self.assertEqual(points[1][1], (100000.0, 35000.5, 62.0))
        self.assertEqual(points[1][2], '\u043f_2')
        
    def test_refine_projstring(self):
        """refine_projstring(projstring) returns normalized projstring"""
        test_data = [
            ('+proj=longlat +no_defs',
             '+proj=longlat +ellps=WGS84 +no_defs'),
            # It is strange that osr.SpatialReference replaces +k_0 with +k
            ('+k_0=0.9996 +proj=tmerc +lon_0=39 +no_defs',
             '+proj=tmerc +lat_0=0 +lon_0=39 +k=0.9996 +x_0=0 +y_0=0 '
             '+ellps=WGS84 +units=m +no_defs'),
            ]
        for orig, ctrl in test_data:
            refined = guessproj.refine_projstring(orig).strip()
            self.assertEqual(refined, ctrl)
    
    def test_parse_arguments(self):
        """parse_arguments() parses command line arguments"""
        src_proj, tgt_params, options, input_file = guessproj.parse_arguments([
            'guessproj', '--wkt', b'+proj=longlat', '+ellps=WGS84',
            '+towgs84=0,0,0', '+to', '+proj=tmerc', '+ellps=krass',
            '+towgs84=~30.5,-140,~-80', '+lon_0=33', '+x_0=6.5e6',
            '--k_0~1', '--y_0=0', '--encoding=cp1251', 'filename.txt',
            ])
        self.assertEqual(src_proj, '+proj=longlat +ellps=WGS84 +towgs84=0,0,0')
        self.assertDictEqual(tgt_params, {
            '+proj': ['tmerc'], '+ellps': ['krass'],
            '+towgs84': [30.5, '-140', -80.0],
            '+lon_0': ['33'], '+x_0': ['6.5e6'],
            '--k_0': [1.0], '--y_0': ['0'],
            })
        self.assertDictEqual(options, {'--wkt': True, '--encoding': 'cp1251'})
        self.assertEqual(input_file, 'filename.txt')
        
    def test_prepare_template(self):
        """prepare_template() returns template and list of initial values"""
        template, initial_values = guessproj.prepare_template({
            '+proj': ['tmerc'], '+ellps': ['krass'],
            '+towgs84': [30.5, '-140', -80.0],
            '+lon_0': ['33'], '+x_0': ['6.5e6'],
            '--k_0': [1.0], '--y_0': ['0'],
            })
        self.assertIn('+proj=tmerc', template)
        self.assertIn('+ellps=krass', template)
        self.assertIn('+towgs84={', template)
        self.assertIn('+lon_0=33', template)
        self.assertIn('+x_0=6.5e6', template)
        self.assertNotIn('--k_0', template)
        self.assertNotIn('--y_0', template)
        self.assertEqual(len(initial_values), 2)
    
    def test_find_residuals(self):
        """find_residuals() transforms the points and calculates residuals"""
        src_proj = '+proj=longlat +ellps=WGS84 +no_defs'
        tgt_proj = '+proj=tmerc +ellps=krass +lon_0=39 +x_0=3e5 +y_0=-5e6'
        filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'four_points.txt')
        points = guessproj.read_points(filename, 'cp1251')
        residuals = guessproj.find_residuals(src_proj, tgt_proj, points)
        self.assertEqual(len(residuals), 4)
        for p in residuals:
            self.assertEqual(len(p), 2)
            for r in p:
                self.assertLess(abs(r), 0.01)


if __name__ == '__main__':
    unittest.main()
    
