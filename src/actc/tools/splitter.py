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
''' @package  actc.tools.splitter

@brief   Client Server Code Splitter

@author  Ronan Le Gallic, Jeroen Van Cleemput

@date    2015/08/03
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from glob                       import iglob
from os.path                    import abspath
from os.path                    import basename
from os.path                    import dirname
from os.path                    import join

from doit.action                import CmdAction

from actc.tools                 import AbstractCmdTool
from actc.tools                 import toList
from actc.tools.codesurfer      import CSURF

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

CLIENT_SERVER_SPLITTER = '/opt/client_server_splitter'

PROCESS = [join(CLIENT_SERVER_SPLITTER,'process.sh')]

class SplitterProcess(AbstractCmdTool):
    '''
    Processing of the input (preprocessed) file to analyse
    '''

    def __init__(self, program = PROCESS,
                 options = None,
                 outputs = None):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(SplitterProcess, self).__init__(program = program,
                                                 options = options,
                                                 outputs = outputs)
    # end def __init__

    _ACTION = 'process'
    def _cmd(self,task,fact_folder):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''

        # program
        args = list(self._program)

        # constraint
        args.insert(0, 'ulimit -s unlimited &&')

        # <input_file>
        args.append(list(task.file_dep)[0])

        # <output_file>
        args.append(task.targets[0])

        #fact folder
        args.append(fact_folder + '/')
        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(SplitterProcess, self).tasks(*args, **kwargs)

        # Process Files
        path, ext = self._outputs[0]

        for arg in toList(args[0]):
            for src in iglob(abspath(arg)):

                dst  = join(path, basename(src) + ext)

                yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
                       'title'   : self._title,
                       'actions' : [CmdAction(self._cmd),],
                       'params'  : [{'name'   : 'fact_folder',
                                     'short'  : None,
                                     'default': kwargs.get('fact_folder', 'facts/'),
                                     },
                                    ],
                       'targets' : [dst,],
                       'file_dep': [src,],
                       'task_dep': ['_createfolder_' + path]
                       }
            # end for
        # end for
    # end def tasks
# end class SplitterProcess


TRANSFORMATION = [join(CLIENT_SERVER_SPLITTER,'code_transformation.sh')]

class SplitterCodeTransformation(AbstractCmdTool):
    '''
    Processing of the input (preprocessed) file to analyse
    '''

    def __init__(self, program = TRANSFORMATION,
                 options = None,
                 outputs = None):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(SplitterCodeTransformation, self).__init__(program = program,
                                                 options = options,
                                                 outputs = outputs)
    # end def __init__

    _ACTION = 'transform'
    def _cmd(self,task,fact_folder,csurf_folder,client_folder,server_folder,log_folder):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''

        # program
        args = list(self._program)

        # constraint
        args.insert(0, 'ulimit -s unlimited &&')

        # constraint: csurf in path
        args.insert(0, 'export PATH=%s:$PATH &&' % (dirname(CSURF),))

        # –l <log_file>
        args.append('-l')
        args.append(join(log_folder,
                         basename(task.targets[0]) + '.json'))

        # <input_file>
        args.append(list(task.file_dep)[0])

        #fact folder
        args.append(fact_folder + '/')

        #csurf folder
        args.append(csurf_folder + '/')

        #client folder
        args.append(client_folder + '/')

        #server folder
        args.append(server_folder + '/')

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(SplitterCodeTransformation, self).tasks(*args, **kwargs)

        # Process Files
        path, ext = self._outputs[0]

        for arg in toList(args[0]):
            for src in iglob(abspath(arg)):

                dst  = join(path, basename(src) + ext)

                yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
                       'title'   : self._title,
                       'actions' : [CmdAction(self._cmd),],
                       'params'  : [{'name'   : 'fact_folder',
                                     'short'  : None,
                                     'default': kwargs.get('fact_folder'),
                                     },
                                    {'name'   : 'csurf_folder',
                                     'short'  : None,
                                     'default': kwargs.get('csurf_folder'),
                                     },
                                    {'name'   : 'client_folder',
                                     'short'  : None,
                                     'default': kwargs.get('client_folder'),
                                     },
                                    {'name'   : 'server_folder',
                                     'short'  : None,
                                     'default': kwargs.get('server_folder'),
                                     },
                                     {'name'   : 'log_folder',
                                     'short'  : None,
                                     'default': kwargs.get('log_folder'),
                                     },
                                    ],
                       'targets' : [dst,],
                       'file_dep': [src,],
                       'task_dep': ['_createfolder_' + path]
                       }
            # end for
        # end for
    # end def tasks
# end class SplitterCodeTransformation

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
