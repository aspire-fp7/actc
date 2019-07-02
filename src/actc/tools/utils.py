#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2014-2016 Nagravision S.A.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Nagravision S.A., nor the
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
''' @package  actc.tools.utils

@brief   Utilities

@author  Ronan Le Gallic

@date    2014/10/07
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from glob                       import iglob
from os.path                    import abspath
from os.path                    import dirname
from os.path                    import getsize
from os.path                    import isdir
from os.path                    import join
from os.path                    import basename
from shutil                     import copyfile
import copy

from doit.action                import CmdAction

from actc.tools                 import AbstractBasicPythonTool
from actc.tools                 import AbstractBasicCmdTool
from actc.tools                 import AbstractCmdTool
from actc.tools                 import toList

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

INCLUDE_PATH_REWRITER = '/projects/scripts/include_rel2abs.sh'

class Copier(AbstractBasicPythonTool):
    '''
    Copy files from src to dest[.ext]
    '''

    _ACTION = 'copy'

    def _python(self, task):
        '''
        @copydoc actc.tools.AbstractPythonTool._python
        '''
        copyfile(list(task.file_dep)[0], task.targets[0])
    # end def _python

# end class Copier

class ExtendedCopier(AbstractCmdTool):
    '''
    Preprocesor
    '''

    def __init__(self, program = INCLUDE_PATH_REWRITER,
                       options = None,
                       outputs = ('')):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(ExtendedCopier, self).__init__(program = program,
                                           options = options,
                                           outputs = outputs)
    # end def __init__

    _ACTION = 'extended copy'

    def _cmd(self, task, source):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # input
        args.append(source)

        # output
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(ExtendedCopier, self).tasks(*args, **kwargs)

        # Process Files
        path, ext = self._outputs[0]

        for arg in toList(args[0]):
            for src in iglob(abspath(arg)):

                if not getsize(src):
                    continue
                # end if

                dst = join(path, basename(src) + ext)

                if (len(args) == 3):
                    dst = sub(args[1], args[2], dst)
                # end if

                yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
                       'title'   : self._title,
                       'actions' : [CmdAction(self._cmd), ],
                       # HACK, file_dep does not maintain ordering
                       'params'  : [{'name'   : 'source',
                                     'short'  : None,
                                     'default': src,
                        }],
                       'targets' : [dst, ],
                       'file_dep': [src, ],
                       'task_dep' : ['_createfolder_' + path]
                       }
            # end for
        # end for
    # end def tasks

# end class ExtendedCopier


def make_hash(o):
    """
    Makes a hash from a dictionary, list, tuple or set to any level, that contains
    only other hashable types (including any lists, tuples, sets, and
    dictionaries).
    """

    if isinstance(o, (set, tuple, list)):
        return hash(tuple([make_hash(e) for e in o]))

    elif not isinstance(o, dict):
        return hash(o)

    new_o = copy.deepcopy(o)
    for k, v in new_o.items():
        new_o[k] = make_hash(v)
    return hash(tuple(frozenset(sorted(new_o.items()))))

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
