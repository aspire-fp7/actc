#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2014-2015 Nagravision S.A.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Nagravision S.A. nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL NAGRAVISION S.A. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------
''' @package actc.test.testcli

@brief   CLI tests

@author  Ronan Le Gallic

@date    2014/10/13
'''
# ------------------------------------------------------------------------------
# import
# ------------------------------------------------------------------------------
from cStringIO          import StringIO
from glob               import iglob
from os                 import mkdir
from os                 import remove
from os.path            import isdir
from os.path            import isfile
from os.path            import join
from unittest           import TestCase

from actc.cli           import Main
from actc.consts        import APP_VERSION

import sys

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

class CliTestCase(TestCase):
    '''
    CLI tests
    '''

    def setUp(self):
        '''
        @copydoc unittest.TestCase.setUp
        '''
        self._stderr = list()
        self._stdout = list()
        self._status = None

        self._tmpDir = '/tmp/actc'

        if (not isdir(self._tmpDir)):
            mkdir(self._tmpDir)
        # end if

        for path in iglob(join(self._tmpDir, '*.*')):
            remove(path)
        # end for


        TestCase.setUp(self)
    # end def setUp

    def actc(self, *args):
        '''
        actc wrapper

        @param args [in] (list) of arguments
        '''
        self._status = 0                                                                                                # pylint:disable=W0201

        try:
            # Backup
            sys_stderr = sys.stderr
            sys_stdout = sys.stdout

            sys.stderr = StringIO()
            sys.stdout = StringIO()

            sys.argv = ['actc.py'] + list(args)
            Main()

        except SystemExit as msg:
            self._status = msg.code

        finally:
            self._stderr = sys.stderr.getvalue().splitlines()
            self._stdout = sys.stdout.getvalue().splitlines()

            # Restore
            sys.stderr = sys_stderr
            sys.stdout = sys_stdout

        # end try
    # end def actc

    def assertStatus(self, status, msg = ''):
        '''
        Signal a test failure if status is not the expected one

        @param  status [in] (int) code
        @option msg    [in] (str) explaination
        '''
        self.assertEqual(status, self._status, msg)
    # end def assertStatus

    def test_version(self):
        '''
        Test --version option
        '''
        self.actc('--version')
        self.assertStatus(0)
        self.assertEqual(APP_VERSION, self._stderr[0])
    # end def test_version

    def test_help(self):
        '''
        Test -h / --help option
        '''
        self.actc('-h')
        self.assertStatus(0)
        self.assertTrue(self._stdout[0].startswith('usage'))

        self.actc('--help')
        self.assertStatus(0)
        self.assertTrue(self._stdout[0].startswith('usage'))
    # end def test_help

    def test_xyz(self):
        '''
        Test unknown option
        '''
        self.actc('-x')
        self.assertStatus(2)

        self.actc('--xyz')
        self.assertStatus(2)
    # end def test_xyz

    def test_arg(self):
        '''
        Test invalid argument
        '''
        self.actc('arg')
        self.assertStatus(2)
    # end def test_arg

    def test_generate(self):
        '''
        Test -g / --generate option
        '''
        jsonPath = join(self._tmpDir, 'test_generate.json')

        self.actc('-g', jsonPath)
        self.assertStatus(0)
        self.assertTrue(isfile(jsonPath))
    # end def test_generate

# end class CliTestCase

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
