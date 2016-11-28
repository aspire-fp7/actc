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
# DISCLAIMED. IN NO EVENT SHALL NAGRAVISION S.A., OR GEMALTO S.A., BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------
''' @package  actc.tools

@brief   Tools

@author  Ronan Le Gallic

@date    2014/10/07
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from glob                       import iglob
from glob                       import glob
from os                         import getenv
from os                         import pathsep
from os                         import makedirs
from os.path                    import abspath
from os.path                    import basename
from os.path                    import getsize
from os.path                    import isdir
from os.path                    import isfile
from os.path                    import join
from re                         import sub

from doit.action                import CmdAction
from doit.tools                 import run_once

import sys

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

def toList(item):
    '''
    Convert item in list

    @param item [in] (None, list, str) value

    @return (list)
    '''
    items = list()

    if item is None:
        pass

    elif isinstance(item, list):
        items.extend(item)

    else:
        items.append(item)
    # end if

    return items
# end def toList


def createFolder(path):
    '''
    Create folder (if not already exists)

    @param path [in] (str) to create
    '''
    if (isdir(path)):
        return
    # end if

    try:
        makedirs(path)
    except OSError as err:
        # Already created by another process/thread?
        if (isdir(path)):
            return
        # end if

        raise(err)
    # end try
# end def createFolder

class AbstractTool(object):
    '''
    Tool interface
    '''

    def __init__(self, outputs = None):
        '''
        Constructor

        @option outputs   [in] (tuple, list) (dir, ext)
        '''
        self._outputs    = toList(('.', '') if outputs is None else outputs)

        self._outputDirs = dict([(path, ext) for path, ext in self._outputs])
        self._outputExts = dict([(ext, path) for path, ext in self._outputs])
    # end def __init__

    def __repr__(self):
        '''
        Compute the "official" string representation of self

        @return (str)
        '''
        return '%s' % (self.__class__.__name__,)
    # end def __repr__


    @staticmethod
    def _name(action, *args):
        '''
        Format task name

        @param action [in] (str)  to be executed
        @param args   [in] (list) arguments

        @return (str)
        '''
        indent = '\n' + ' ' * 20
        name   = '%-20s' % (action,)

        for arg in args:

            if isinstance(arg, list):
                name += indent.join(arg)

            elif arg.startswith('\n'):
                name += '%-21s' % (arg,)

            else:
                name += arg
            # end if
        # end for

        return name
    # end def _name

    @staticmethod
    def _title(task):
        '''
        Format task title

        @param task [in] (Task) to be executed

        @return (str)
        '''
        step, name = task.name.split(':', 1)
        names = name.strip().splitlines()
        names.insert(0, step)

        return '\n   '.join(names)
    # end def _title

    def tasks(self, *args, **kwargs):                                                                                   # pylint:disable=W0613
        '''
        Task Generator

        @param args   [in] (list) arguments
        @param kwargs [in] (dict) keyword arguments

        @return (generator)
        '''
        # Create Folders
        for path in set(self._outputDirs):

            if isdir(path):
                continue
            # end if

            yield {'name'    : self._name('create', path),
                   'title'   : self._title,
                   'actions' : [(createFolder, (path,))],
                   'targets' : [path,],
                   'uptodate': [run_once,],
                   }
        # end for
    # end def tasks

# end class AbstractTool


class AbstractPythonTool(AbstractTool):
    '''
    Tool with "python-action" interface
    '''

    _ACTION = None

    def _python(self, task):
        '''
        Execute "python-action"

        @param task [in] (Task) to be executed
        '''
        raise NotImplementedError
    # end def _python

# end class AbstractPythonTool


class AbstractBasicPythonTool(AbstractPythonTool):
    '''
    Basic Python Tool

    basename.* --> path/basename.ext
    '''

    def _python(self, task):
        '''
        @copydoc actc.tools.AbstractPythonTool._python
        '''
        raise NotImplementedError
    # end def _python

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractPythonTool.tasks
        '''
        # Create Folders
        yield super(AbstractBasicPythonTool, self).tasks(*args, **kwargs)

        # Process Files
        path, ext = self._outputs[0]

        for arg in toList(args[0]):
            for src in iglob(abspath(arg)):

                if not getsize(src):
                    continue
                # end if

                dst = join(path, basename(src) + ext)

                # Renaming
                pattern = kwargs.get('pattern')
                replace = kwargs.get('replace')

                if (    (pattern is not None)
                    and (replace is not None)):
                    dst = sub(pattern, replace, dst)
                # end if

                yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
                       'title'   : self._title,
                       'actions' : [self._python,],
                       'targets' : [dst,],
                       'file_dep': [src,],
                       }
            # end for
        # end for
    # end def tasks

# end class AbstractBasicPythonTool


_PATHS = getenv('PATH').split(pathsep)


class AbstractCmdTool(AbstractTool):
    '''
    Tool with "cmd-action" interface
    '''

    def __init__(self, program   = 'path',
                       options   = None,
                       outputs   = None):
        '''
        Constructor

        @param  program   [in] (str, list) executable [script]

        @option options   [in] (str, list) by default

        @option outputs   [in] (tuple, list) (dir, ext)
        '''
        # str:   'executable'
        # list: ['executable', 'script']
        self._program   = self._check(program)

        self._options   = toList(options)

        super(AbstractCmdTool, self).__init__(outputs = outputs)
    # end def __init__


    @staticmethod
    def _check(program):
        '''
        Check program path

        @param program [in] (str, list) path

        @return (list)
        '''
        programs = toList(program)

        for name in programs:

            # Current Working Directory?
            if isfile(name):
                continue
            # end if

            # PATH?
            for path in _PATHS:
                if isfile(join(path, name)):
                    break
                # end if
            else:
                sys.exit('actc.py: error: program not found: %s' % (name,))
            # end for
        # end for

        return programs
    # end def _check

    def __repr__(self):
        '''
        @copydoc actc.tools.AbstractTool.__repr__
        '''
        return '%s(%s)' % (self.__class__.__name__, self._program[-1])
    # end def __repr__

    _ACTION = None

    def _cmd(self, task):
        '''
        Build "cmd-action" arguments

        @param task [in] (Task) to be executed

        @return (str) command line
        '''
        raise NotImplementedError
    # end def _cmd

# end class AbstractCmdTool


class AbstractBasicCmdTool(AbstractCmdTool):
    '''
    Basic Command Tool

    basename.* --> path/basename.ext
    '''

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractCmdTool._cmd
        '''
        raise NotImplementedError
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(AbstractBasicCmdTool, self).tasks(*args, **kwargs)

        # Process Files
        path, ext = self._outputs[0]

        for arg in toList(args[0]):
            for src in iglob(abspath(arg)):

                if not getsize(src):
                    continue
                # end if

                dst  = join(path, basename(src) + ext)

                if (len(args) == 3):
                    dst = sub(args[1], args[2], dst)
                # end if

                yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
                       'title'   : self._title,
                       'actions' : [CmdAction(self._cmd),],
                       'targets' : [dst,],
                       'file_dep': [src,],
                       }
            # end for
        # end for
    # end def tasks

# end class AbstractBasicCmdTool

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
