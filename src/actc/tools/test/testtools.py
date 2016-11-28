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
''' @package actc.tools.test.testtools

@brief   Tools utils tests

@author  Ronan Le Gallic

@date    2014/10/14
'''
# ------------------------------------------------------------------------------
# import
# ------------------------------------------------------------------------------
from os.path                    import join
from shutil                     import copyfile

from actc.tools                 import AbstractTool
from actc.tools                 import AbstractBasicPythonTool
from actc.tools                 import toList
from actc.tools.test.basetest   import DoItTestCase

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

class ToolTestCase(DoItTestCase):
    '''
    Copier tests
    '''

    def test_toList(self):
        '''
        Test toList function
        '''
        self.assertEqual([], toList(None))

        self.assertEqual(['str',], toList('str'))

        self.assertEqual([('one', 1),], toList(('one', 1)))

        self.assertEqual(['two', 2], toList(['two', 2]))
    # end def test_toList

    def task_tool(self):
        '''
        Task: create folder

        @return (Task)
        '''
        dst = join(self.tmpDir, 'TOOL')

        tool = AbstractTool(outputs = (dst, ''))
        yield tool.tasks()
    # end def task_tool

    def test_tool(self):
        '''
        Test: copy src to dst
        '''
        self.doIt('tool')
        self.assertTmpDir('TOOL')
    # end def test_tool

    def test_tool__repr__(self):
        '''
        Test:
        '''
        tool = AbstractTool()
        self.assertEqual('AbstractTool', str(tool))
    # end def test_tool__repr__

    def task_basicPythonTool(self):
        '''
        Task: create folder

        @return (Task)
        '''

        class BasicPythonTool(AbstractBasicPythonTool):
            '''
            Basic Python Tool
            '''
            def _python(self, task):
                '''
                @copydoc actc.tools.AbstractBasicPythonTool._python
                '''
                copyfile(list(task.file_dep)[0], task.targets[0])
            # end def _python
        # end class BasicPythonTool

        src = self.createTmpFile('bar', 'foo')
        dst = join(self.tmpDir, 'BASIC_PYTHON_TOOL')

        tool = BasicPythonTool(outputs = (dst, ''))
        yield tool.tasks(src)
    # end def task_basicPythonTool

    def test_basicPythonTool(self):
        '''
        Test: copy src to dst
        '''
        self.doIt('basicPythonTool')
        self.assertTmpFile('BASIC_PYTHON_TOOL/bar', 'foo')
    # end def test_basicPythonTool


# end class ToolTestCase

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
