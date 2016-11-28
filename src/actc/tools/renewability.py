#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2016 Ghent University
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Ghent University, nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL GHENT UNIVERSITY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------
''' @package  actc.tools.renewability

@brief   Renewability

@author  Jeroen Van Cleemput

@date    2016/08/18
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------

from actc.tools                 import AbstractCmdTool
from doit.tools                 import CmdAction
from doit.tools                 import run_once

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

RENEWABILITY = '/opt/renewability'

RENEWABILITY_CREATE_SCRIPT = RENEWABILITY + '/scripts/create_new_application.sh'

class RenewabilityCreate(AbstractCmdTool):
    '''
    Register new application in renewability database

    '''

    def __init__(self, program=RENEWABILITY_CREATE_SCRIPT,
                       options=None,
                       outputs=None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(RenewabilityCreate, self).__init__(program=program,
                                                    options=options,
                                                    outputs=outputs)
    # end def __init__

    _ACTION = 'register_app'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # create target
        args.extend(['&&', 'touch', task.targets[0]])

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''

        # Process Files
        dst, _ = self._outputs[0]

        yield {'name'    : self._name(self._ACTION, dst),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd), ],
               'targets' : [dst, ],
               'uptodate': [run_once],
               }
    # end def tasks

# end class RenewabilityCreate

RENEWABILITY_POLICY_SCRIPT = RENEWABILITY + '/scripts/set_application_policy.sh'
RENEWABILITY_REVISION_DURATION = 72000
RENEWABILITY_TIMEOUT_MANDATORY = False

class RenewabilityPolicy(AbstractCmdTool):
    '''
    Set the renewability policy for the application
    '''

    def __init__(self, program=RENEWABILITY_POLICY_SCRIPT,
                       options=None,
                       outputs=None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(RenewabilityPolicy, self).__init__(program=program,
                                                    options=options,
                                                    outputs=outputs)
    # end def __init__

    _ACTION = 'set_policy'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # create target
        args.extend(['&&', 'touch', task.targets[0]])

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''

        # Process Files
        dst, _ = self._outputs[0]

        yield {'name'    : self._name(self._ACTION, dst),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd), ],
               'targets' : [dst, ],
               'uptodate': [run_once],
               }
    # end def tasks

# end class RenewabilityPolicy
