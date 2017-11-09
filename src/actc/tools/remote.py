#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2015-2016 Nagravision S.A., Ghent University
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Nagravision S.A., Ghent University, nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL NAGRAVISION S.A., OR GHENT UNIVERSITY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------
''' @package  actc.tools.remote

@brief   Remote Attestation

@author  Ronan Le Gallic, Jeroen Van Cleemput

@date    2015/11/17
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from os.path                    import dirname
from os.path                    import join

from doit.action                import CmdAction

from actc.tools                 import AbstractCmdTool
from actc.tools                 import AbstractBasicCmdTool
from actc.tools                 import toList

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

ATTESTATOR_SELECTOR = '/opt/remote_attestation/scripts/attestator_selector.sh'

class AttestatorSelector(AbstractCmdTool):
    '''
    AttestatorSelector
    '''

    def __init__(self, program = ATTESTATOR_SELECTOR,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(AttestatorSelector, self).__init__(program = program,
                                                 options = options,
                                                 outputs = outputs)
    # end def __init__

    _ACTION = 'select'

    def _cmd(self, task, target):
        '''
        @copydoc actc.tools.AbstractCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # -a <annotation>
        args.append('-a')
        args.append(list(task.file_dep)[0])

        # -o <outputdir>
        args.append('-o')
        path, _ = self._outputs[0]
        args.append(path)

        # -t <target>
        args.append('-t')
        args.append(target)

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractTool.tasks
        '''
        # Create Folders
        yield super(AttestatorSelector, self).tasks(*args, **kwargs)

        # Process Files
        path, _ = self._outputs[0]

        src = toList(args[0])
        dst = toList(join(path, 'interpreter.out'))

        yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd),],
               'params'  : [{'name'   : 'target',
                             'short'  : None,
                             'default': kwargs.get('target', 'linux'),
                             },
                            ],
               'file_dep': src,
               'task_dep': ['_createfolder_' + path]
               }

    # end def tasks

# end class AttestatorSelector

ANTI_CLONING = '/opt/anti_cloning/annotation/replace.sh'

class AntiCloning(AbstractBasicCmdTool):
    '''
    Anti-cloning
    '''

    def __init__(self, program = ANTI_CLONING,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(AntiCloning, self).__init__(program = program,
                                           options = options,
                                           outputs = outputs)
    # end def __init__

    _ACTION = 'anti-cloning'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # input
        args.append(list(task.file_dep)[0])

        # output
        args.append(task.targets[0])


        return ' '.join(args)
    # end def _cmd

# end class AntiCloning


REACTION_UNIT = '/opt/reaction_unit/script/replace.sh'

class ReactionUnit(AbstractBasicCmdTool):
    '''
    Reaction-Unit
    '''

    _ACTION = 'reaction-unit'

    def __init__(self, program = REACTION_UNIT,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(ReactionUnit, self).__init__(program = program,
                                           options = options,
                                           outputs = outputs)
    # end def __init__

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # input
        args.append(list(task.file_dep)[0])

        # output
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd
# end class ReactionUnit

DCL = '/opt/dcl'
DCL_SCRIPT = '/script/replace.sh'

class DiversifiedCryptoLibrary(AbstractBasicCmdTool):
    '''
    Diversified Crypto Library
    '''

    _ACTION = 'dcl'

    def __init__(self, program = DCL + DCL_SCRIPT,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(DiversifiedCryptoLibrary, self).__init__(program = program,
                                                       options = options,
                                                       outputs = outputs)
    # end def __init__

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # input
        args.append(list(task.file_dep)[0])

        # output
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd
# end class DCL

CFT = '/opt/cf_tagging/cf_tagging.py'

class ControlFlowTagging(AbstractBasicCmdTool):
    '''
    Control Flow Tagging
    '''

    _ACTION = 'cft'

    def __init__(self, program = CFT,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(ControlFlowTagging, self).__init__(program = program,
                                                       options = options,
                                                       outputs = outputs)
    # end def __init__

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list()
        args.append(list(self._program)[0])

        # options
        args.extend(self._options)

        # input
        args.append('-i')
        args.append(list(task.file_dep)[0])

        # output
        args.append('-o')
        args.append(dirname(task.targets[0]))

        return ' '.join(args)
    # end def _cmd
# end class CFT

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
