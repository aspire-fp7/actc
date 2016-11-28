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
''' @package  actc.dodo

@brief   DoIt customization

@author  Ronan Le Gallic

@date    2014/10/10
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from inspect                    import getmembers
from inspect                    import ismethod
from inspect                    import getsourcelines
from os.path                    import abspath
from shutil                     import rmtree

from doit.action                import CmdAction
from doit.cmd_base              import ModuleTaskLoader
from doit.doit_cmd              import DoitMain
from doit.reporter              import ExecutedOnlyReporter
from doit.tools                 import create_folder

from actc.consts                import CFG_JOBS

import sys

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

class DebugReporter(ExecutedOnlyReporter):
    '''
    Custom reporter that print commands
    '''

    def __init__(self, outstream, options):
        '''
        @copydoc doit.reporter.ExecutedOnlyReporter.__init__
        '''
        super(DebugReporter, self).__init__(outstream, options)
    # end def __init__

    def execute_task(self, task):
        '''
        @copydoc doit.reporter.ExecutedOnlyReporter.execute_task
        '''
        if (task.actions and (task.name[0] != '_')):

            debug = list()
            for action in task.actions:
                if (isinstance(action, CmdAction)):
                    debug.append('\n\n')
                    debug.append(action.expand_action())
                    debug.append('\n')
                # end if
            # end for

            self.write('.  %s%s\n' % (task.title(), ''.join(debug)))
        # end if
    # end def execute_task

# end class DebugReporter


def monoprocess(task):
    '''
    Decorator to force monoprocess execution

    @param task [in] (func) to decorate

    @return (func)
    '''
    task.process = 1
    return task
# end def monoprocess


class AbstractDodo(object):
    '''
    DoIt dodo
    '''
    def __init__(self, output = 'build', debug = False, verbose = False):
        '''
        Constructor
        '''
        self._output = abspath(output)
        create_folder(self._output)

        self._tasks  = [(name, method)
                        for name, method in getmembers(self, predicate = ismethod)
                        if  name.startswith('task_')]

        self._tasks.sort(cmp = lambda x,y: cmp(getsourcelines(x[1])[1],
                                               getsourcelines(y[1])[1]))

        self._dep_file  = '.actc.db'
        self._reporter  = DebugReporter if debug else ExecutedOnlyReporter
        self._verbosity = 2 if verbose else 1
    # end def __init__

    # --------------------------------------------------------------------------
    # Tasks
    # --------------------------------------------------------------------------

    # Define your tasks

    # --------------------------------------------------------------------------
    # DoIt management
    # --------------------------------------------------------------------------

    def build(self, jobs = CFG_JOBS):
        '''
        Build targets

        @option jobs [in] (int) 1..N jobs at once
        '''
        # Ideally, a build should be deterministic:
        #   module.in --> tool --> module.out
        #
        # In our case, depending on annotations,
        # a tool can generate more or fewer files
        #
        # Tasks are then called the one after the other
        for name, method in self._tasks:
            self._doIt('run',
                       '--process', str(getattr(method, 'process', jobs)),
                       tasks = {name: method})
        # end for

    # end def build


    def clean(self):
        '''
        Clean all targets
        '''
        rmtree(self._output, ignore_errors = True)
        self._doIt('forget')
    # end def clean


    def _doIt(self, *args, **kwargs):
        '''
        DoIt wrapper

        @param args   [in] (list) arguments
        @param kwargs [in] (dict) keyword arguments
        '''
        members = dict(kwargs.get('tasks', self._tasks))
        members.update(DOIT_CONFIG = {'backend'   : 'json',
                                      'dep_file'  : self._dep_file,
                                      'reporter'  : self._reporter,
                                      'verbosity' : self._verbosity,
                                      'minversion': '0.27.0'})

        status = DoitMain(ModuleTaskLoader(members)).run(args)
        if status:
            sys.exit(status)
        # end if

    # end def _doIt

# end class AbstractDodo

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
