#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2014 Nagravision S.A.
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
''' @package actc.tools.test.basetest

@brief   Tools test harness

@author  Ronan Le Gallic

@date    2014/10/14
'''
# ------------------------------------------------------------------------------
# import
# ------------------------------------------------------------------------------
from os                         import makedirs
from os                         import remove
from os.path                    import basename
from os.path                    import dirname
from os.path                    import isdir
from os.path                    import isfile
from os.path                    import join
from shutil                     import rmtree
from tempfile                   import mkdtemp
from unittest                   import TestCase

from actc.dodo                  import AbstractDodo

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

class BaseTestCase(TestCase):
    '''
    ACTC Test Case
    '''

    def setUp(self):
        '''
        setUp test case
        '''
        self.tmpDir = mkdtemp(prefix = 'actc')
    # end def setUp

    def tearDown(self):
        '''
        tearDown test case
        '''
        rmtree(self.tmpDir, ignore_errors = True)

    # end def tearDown

    def mkTmpDir(self, path):
        '''
        Create temporary path

        @param path [in] (str) path relative to tmpDir

        @return (str)
        '''
        path = join(self.tmpDir, path)
        if not isdir(path):
            makedirs(path)
        # end if
        return path
    # end def mkTmpDir

    def createTmpFile(self, path, content = ''):
        '''
        Create temporary file

        @param  path    [in] (str) path relative to tmpDir
        @option content [in] (str) text

        @return (str)
        '''
        path = join(self.mkTmpDir(dirname(path)), basename(path))

        with open(path, 'w') as fo:
            fo.write(content)
        # end with

        return path
    # end def createTmpFile

    def assertTmpDir(self, path):
        '''
        Assert Dir exists

        @param  path    [in] (str) path relative to tmpDir
        '''
        path = join(self.tmpDir, path)

        self.assertTrue(isdir(path))
    # end def assertTmpDir


    def assertTmpFile(self, path, content = ''):
        '''
        Assert File exists

        @param  path    [in] (str) path relative to tmpDir
        @option content [in] (str) text
        '''
        path = join(self.tmpDir, path)

        self.assertTrue(isfile(path))

        with open(path, 'r') as fo:
            text = fo.read()
        # end with

        self.assertEqual(content, text)
    # end def assertTmpFile


# end class BaseTestCase


class DoItTestCase(BaseTestCase, AbstractDodo):
    '''
    ACTC + DoIt Test Case
    '''

    def __init__(self, methodName = 'runTest'):
        '''
        Constructor

        @option methodName [in] (str) named test method
        '''
        BaseTestCase.__init__(self, methodName = methodName)
        AbstractDodo.__init__(self)
    # end def __init__

    def doIt(self, *args):
        '''
        Run DoIt

        @param args [in] (list) arguments
        '''
        try:
            self._doIt(*args)
        except SystemExit:
            pass
        finally:
            if isfile('.actc.db'):
                remove('.actc.db')
            # end if
        # end try
    # end def doIt

# end class DoItTestCase


# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
