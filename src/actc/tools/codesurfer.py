#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2015 Nagravision S.A.
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
''' @package  actc.tools.codesurfer

@brief   Code Surfer

@author  Ronan Le Gallic

@date    2015/06/08
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from glob                       import glob
from os.path                    import abspath
from os.path                    import dirname
from os.path                    import join

from doit.action                import CmdAction

from actc.tools                 import AbstractCmdTool
from actc.tools                 import AbstractBasicCmdTool
from actc.tools                 import toList

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

CSURF = '/opt/codesurfer/csurf/bin/csurf'

class CodeSurferInitializer(AbstractCmdTool):
    '''
    CodeSurfer project creation

    *.i --> CSURF/CSURF.prj
    '''

    def __init__(self, program = CSURF,
                       options = None,
                       outputs = ('build', '')):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(CodeSurferInitializer, self).__init__(program = program,
                                                    options = options,
                                                    outputs = outputs)
    # end def __init__

    _ACTION = 'csurf init'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # Hack: run program in output folder (.o generation)
        args.insert(0, 'cd %s &&' % (dirname(task.targets[0])))

        args.append('hook-build')
        args.append('project')

        args.append('-preset-build-options')
        args.append('highest')

        args.append('-error-limit')
        args.append('100')

        args.append('---')

        args.append('gcc')
        args.append('-Wall')

        args.append('-c')
        args.append('-std=c99')

        # options
        args.extend(self._options)

        # *.i
        args.extend(task.file_dep)

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(CodeSurferInitializer, self).tasks(*args, **kwargs)

        # Process Files
        preps = list()

        for arg in toList(args[0]):
            preps.extend(glob(abspath(arg)))
        # end for

        if (not preps):
            return
        # end if

        path, _ = self._outputs[0]
        prj     = join(path, 'project.prj')

        yield {'name'    : self._name(self._ACTION, preps, '\ninto', prj),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd),],
               'targets' : [prj,],
               'file_dep': preps,
               }

    # end def tasks

# end class CodeSurferInitializer


class CodeSurferAnalyser(AbstractBasicCmdTool):
    '''
    CodeSurfer script analyser

    <module>.c.i --> <module>c-aaa-bbb-dd-HH-MM-SS.log | unpredictable!
                 --> <module>.c.i.analysed             | added as target
    '''

    def __init__(self, program = CSURF,
                       options = None,
                       outputs = ('build', 'analysed')):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(CodeSurferAnalyser, self).__init__(program = program,
                                                 options = options,
                                                 outputs = outputs)
    # end def __init__

    _ACTION = 'csurf analyse'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        args.insert(0, 'cd %s &&' % (dirname(task.targets[0]),))

        args.append('-nogui')

        # options
        # -l .../script.stk
        args.extend(self._options)

        args.append('CSURF')

        args.append('-args')

        # <module>.i
        args.extend(task.file_dep)

        # && touch <module>.i.analysed
        args.append('&& touch %s' % (task.targets[0],))

        return ' '.join(args)
    # end def _cmd

# end class CodeSurferAnalyser

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
