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
''' @package actc.tools.test.testutils

@brief   Tools utils tests

@author  Ronan Le Gallic

@date    2014/10/14
'''
# ------------------------------------------------------------------------------
# import
# ------------------------------------------------------------------------------
from os.path                    import join

from actc.tools.utils           import Copier
from actc.tools.test.basetest   import DoItTestCase

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

class CopierTestCase(DoItTestCase):
    '''
    Copier tests
    '''

    def task_basic(self):
        '''
        Task: copy src to dst

        @return (Task)
        '''
        src = self.createTmpFile('bar', 'foo')
        dst = join(self.tmpDir, 'BASIC')

        tool = Copier(outputs = (dst, ''))
        yield tool.tasks(src)
    # end def task_basic

    def test_basic(self):
        '''
        Test: copy src to dst
        '''
        self.doIt('basic')
        self.assertTmpFile('BASIC/bar', 'foo')
    # end def test_basic


    def task_ext(self):
        '''
        Task: copy with extension

        @return (Task)
        '''
        src = self.createTmpFile('bar', 'foo')
        dst = join(self.tmpDir, 'EXT')

        tool = Copier(outputs = (dst, '.x'))
        yield tool.tasks(src)
    # end def task_ext

    def test_pattern(self):
        '''
        Test: copy with extension
        '''
        self.doIt('ext')
        self.assertTmpFile('EXT/bar.x', 'foo')
    # end def test_pattern


# end class CopierTestCase

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
