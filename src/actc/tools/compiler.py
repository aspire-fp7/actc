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
#     * Neither the name of the Nagravision S.A, nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL NAGRAVISION S.A. OR GHENT UNIVERSITY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------
''' @package  actc.tools.compiler

@brief   Compiler programs (preprocessor, compiler, linker)

@author  Ronan Le Gallic, Jeroen Van Cleemput

@date    2015/02/04
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from glob                       import glob
from glob                       import iglob
from os.path                    import abspath
from os.path                    import getsize
from os.path                    import basename
from os.path                    import join
from os.path                    import dirname

from re                         import sub


from doit.action                import CmdAction

from actc.tools                 import AbstractBasicCmdTool
from actc.tools                 import AbstractCmdTool
from actc.tools                 import toList

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

FRONTEND = 'gcc'
FRONTEND_FORTRAN = 'gfortran'

class Preprocessor(AbstractCmdTool):
    '''
    Preprocesor
    '''

    def __init__(self, program = FRONTEND,
                       options = None,
                       outputs = ('build/pre', '.i')):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(Preprocessor, self).__init__(program = program,
                                           options = options,
                                           outputs = outputs)
    # end def __init__

    _ACTION = 'preprocess'

    def _cmd(self, task, source):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)
        args.append('-E')
        args.append('-P')

        # output
        args.append('-o')
        args.append(task.targets[0])

        # input
        args.append(source)

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(Preprocessor, self).tasks(*args, **kwargs)

        # Process headers
        headers = []
        for a in kwargs.get('header_files', []):
            headers.extend(glob(abspath(a)))
            # print headers

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
                       'file_dep': [src, ] + headers,
                       'task_dep' : ['_createfolder_' + path]
                       }
            # end for
        # end for
    # end def tasks

# end class Preprocessor


class Compiler(AbstractCmdTool):
    '''
    Clang compiler
    '''

    def __init__(self, program = FRONTEND,
                       options = None,
                       outputs = ('build/obj', '.o'),
                       exit_if_pgm_not_exist = True):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(Compiler, self).__init__(program = program,
                                       options = options,
                                       outputs = outputs,
                                       exit_if_pgm_not_exist=exit_if_pgm_not_exist)
    # end def __init__

    _ACTION = 'compile'

    def _cmd(self, task, source):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # input
        args.append('-c')
        args.append(source)

        # output
        args.append('-o')
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(Compiler, self).tasks(*args, **kwargs)

        # Process headers
        headers = []
        for a in kwargs.get('header_files', []):
            headers.extend(glob(abspath(a)))
            # print headers

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
                       'file_dep': [src, ] + headers,
                       'task_dep': ['_createfolder_' + path]
                       }
            # end for
        # end for
    # end def tasks

# end class Compiler


class CompilerSO(AbstractCmdTool):
    '''
    Clang compiler
    '''

    def __init__(self, program = FRONTEND,
                       options = None,
                       outputs = ('build/obj', '.so')):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(CompilerSO, self).__init__(program = program,
                                       options = options,
                                       outputs = outputs)
    # end def __init__

    _ACTION = 'compileSO'

    def _cmd(self, task, source):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)
        args.append('-shared')

        # input
        args.append('-fPIC')
        args.append(source)

        # output
        args.append('-o')
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(CompilerSO, self).tasks(*args, **kwargs)

        # Process headers
        headers = []
        for a in kwargs.get('header_files', []):
            headers.extend(glob(abspath(a)))
            # print headers

        # Process Files
        path, ext = self._outputs[0]

        for arg in toList(args[0]):
            for src in iglob(abspath(arg)):

                if not getsize(src):
                    continue
                # end if

                if ext.endswith(".so") and len(ext) > 3:
                    dst = join(path, ext)
                else:
                    dst = join(path, basename(src) + ext)
                # end if

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
                       'file_dep': [src, ] + headers,
                       'task_dep': ['_createfolder_' + path]
                       }
            # end for
        # end for
    # end def tasks
# end class CompilerSO


class Linker(AbstractCmdTool):
    '''
    Linker
    '''

    def __init__(self, program = FRONTEND,
                       options = None,
                       outputs = ('build/bin', '.out')):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(Linker, self).__init__(program = program,
                                     options = options,
                                     outputs = outputs)
    # end def __init__

    _ACTION = 'link'

    def _cmd(self, task, objs):                                                 # pylint:disable=W0221
        '''
        @copydoc actc.tools.AbstractCmdTool._cmd
        '''
        args = list(self._program)

        # input
        # Hack to link only .o files
        # Hack to preserve objects order
        #args.extend(list(task.file_dep))
        archive_group = ''
        for i in self._options:
            if 'start-group' in i:
                archive_group = i
                break

        args.extend([obj for obj in objs if not obj.endswith('.json') and (obj not in archive_group)])

        # options
        args.extend(self._options)

        # output
        args.append('-o')
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(Linker, self).tasks(*args, **kwargs)

        # Process Files
        objs = list()

        for arg in toList(args[0]):
            objs.extend(sorted(glob(abspath(arg))))
        # end for

        if not objs:
            return
        # end if

        # Process Files
        path, _ = self._outputs[0]

        dst = toList(args[1])

        yield {'name'    : self._name(self._ACTION, objs, '\ninto', dst),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd),],
               # Hack to preserve objects order
               'params'  : [{'name'   : 'objs',
                             'short'  : None,
                             'default': objs,
                             }],
               'targets' : dst,
               'file_dep': objs,
               'task_dep' : ['_createfolder_' + path]
               }

    # end def tasks

# end class Linker

class Archiver(AbstractCmdTool):
    '''
    Archiver
    '''

    def __init__(self, program=FRONTEND,
                       options=None,
                       outputs=('build/bin', '.out')):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(Archiver, self).__init__(program=program,
                                     options=options,
                                     outputs=outputs)
    # end def __init__

    _ACTION = 'archive'

    def _cmd(self, task, objs):  # pylint:disable=W0221
        '''
        @copydoc actc.tools.AbstractCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.append('rcs')

        # more options options
        args.extend(self._options)

        # output
        args.append(task.targets[0])

        # input
        args.extend(objs)

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(Archiver, self).tasks(*args, **kwargs)

        # Process Files
        objs = list()

        for arg in toList(args[0]):
            objs.extend(sorted(glob(abspath(arg))))
        # end for

        if not objs:
            return
        # end if

        dst = toList(args[1])
        path = dirname(args[1])

        yield {'name'    : self._name(self._ACTION, objs, '\ninto', dst),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd), ],
               # Hack to preserve objects order
               'params'  : [{'name'   : 'objs',
                             'short'  : None,
                             'default': objs,
                             }],
               'targets' : dst,
               'file_dep': objs,
               'task_dep' : ['_createfolder_' + path]
               }

    # end def tasks

# end class Archiver

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
