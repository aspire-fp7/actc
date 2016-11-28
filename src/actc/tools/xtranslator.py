#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2014-2015 Nagravision S.A., Gemalto S.A.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Nagravision S.A., Gemalto S.A., nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL NAGRAVISION S.A., OR GEMALTO S.A. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------
''' @package  actc.tools.xtranslator

@brief   X-translator

@author  Ronan Le Gallic

@date    2014/10/21
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from actc.tools                 import AbstractBasicCmdTool

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

XTRANSLATOR = '/opt/xtranslator/xtranslator'

class Xtranslator(AbstractBasicCmdTool):
    '''
    X-translator
    '''

    def __init__(self, program = XTRANSLATOR,
                       options = None,
                       outputs = ('build/stub', '.s')):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(Xtranslator, self).__init__(program = program,
                                          options = options,
                                          outputs = outputs)
    # end def __init__

    _ACTION = 'x-translate'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # <json>
        args.append(list(task.file_dep)[0])

        # <stubdir>/<stubfile>.s
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

# end class Xtranslator

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
