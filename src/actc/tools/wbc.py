#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2014-2016 Gemalto S.A., Ghent University
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Gemalto S.A., Ghent University, nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL GEMALTO S.A., OR GHENT UNIVERSITY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------
''' @package  actc.tools.wbc

@brief   WBC

@author  Patrice Angelini, Jeroen Van Cleemput

@date    2014/10/17
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from glob                       import iglob
from os.path                    import abspath
from os.path                    import basename
from os.path                    import dirname
from os.path                    import join
from os.path                    import getsize
from os.path                    import isdir
from shutil                     import copyfile
from time                       import sleep

from doit.action                import CmdAction

from actc.tools                 import toList
from actc.tools                 import AbstractCmdTool
from actc.tools                 import AbstractBasicCmdTool
from actc.tools                 import AbstractPythonTool

import os
import stat
import re
# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

ANNOTATION_READER = ['perl', '/opt/wbc/annotation_reader.prl']

class WbcAnnotationReader(AbstractBasicCmdTool):
    '''
    WBC Annotation Reader tool
    '''

    def __init__(self, program = None,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(WbcAnnotationReader, self).__init__(program = program,
                                                  options = options,
                                                  outputs = outputs)
    # end def __init__

    _ACTION = 'read annot'

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
        args.append('>')
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

# end class WbcAnnotationReader

CONFIG = '/opt/wbc/config.x'

class WbcXmlConfigGenerator(AbstractBasicCmdTool):
    '''
    XML configuration generation tool
    '''

    def __init__(self, program = None,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(WbcXmlConfigGenerator, self).__init__(program = program,
                                                    options = options,
                                                    outputs = outputs)
    # end def __init__

    _ACTION = 'generate xml'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # constraint
        args.insert(0, 'ulimit -s unlimited &&')

        # options
        args.extend(self._options)

        # output
        args.append('-o')
        args.append(task.targets[0])

        # input
        args.append(list(task.file_dep)[0])

        # /!\ Hack: remove extra {}
        args.append("&& sed -i 's/[{}]//g'")
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

# end class WbcXmlConfigGenerator

WBTA_LICENSE = '/opt/wbc/generate_license.py'

class WbcLicenseTool(AbstractCmdTool):
    '''
    WBC tool for Aspire
    '''

    def __init__(self, program=None,
                       options=None,
                       outputs=None):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(WbcLicenseTool, self).__init__(program=program,
                                              options=options,
                                              outputs=outputs)
    # end def __init__

    _ACTION = 'license'

    def _cmd(self, task, seed):
        '''
        @copydoc actc.tools.AbstractCmdTool._cmd
        '''
        args = list(self._program)

        # output
        args.append(task.targets[0])

        if(seed):
            args.append(seed)
        # end if

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(WbcLicenseTool, self).tasks(*args, **kwargs)

        # Process Files
        path, _ = self._outputs[0]

        dst = join(path, args[0])

        yield {'name'    : self._name(self._ACTION, '\ninto', dst),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd), ],
               'params'  : [{'name'   : 'seed',
                             'short'  : None,
                             'default': kwargs.get('seed', ''),
                            },
                           ],
               'targets' : [dst, ],
               }
    # end for
    #  end def tasks

# end class WbcWhiteBoxTool



WBTA = ['python', '/opt/wbc/wbta/Wbta.py']

class WbcWhiteBoxTool(AbstractCmdTool):
    '''
    WBC tool for Aspire
    '''

    def __init__(self, program = None,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(WbcWhiteBoxTool, self).__init__(program = program,
                                              options = options,
                                              outputs = outputs)
    # end def __init__

    _ACTION = 'wbta'

    def _cmd(self, task, license_file):
        '''
        @copydoc actc.tools.AbstractCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        # input
        args.append('-s')
        args.append(list(task.file_dep)[0])

        # output
        args.append('-o')
        args.append(dirname(task.targets[0]))

        args.append('-n')
        args.append(basename(list(task.file_dep)[0]).split('.', 1)[0])

        if(license_file):
            args.append('-d')
            args.append(license_file)

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(WbcWhiteBoxTool, self).tasks(*args, **kwargs)

        # Process Files
        path, _ = self._outputs[0]

        for i, src in enumerate(args[0]):

            dst = join(path, args[1][i])

            yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
                   'title'   : self._title,
                   'actions' : [CmdAction(self._cmd), ],
                   'params'  : [{'name'   : 'license_file',
                                 'short'  : None,
                                 'default': kwargs.get('license_file', None),
                                },
                               ],
                   'targets' : [dst,],
                   'file_dep': [src,],
                   }
        # end for
    # end def tasks

# end class WbcWhiteBoxTool


class WbcHeaderIncluder(AbstractPythonTool):
    '''
    WBC header inclusion
    '''

    def __init__(self, outputs = None):
        '''
        @copydoc actc.tools.AbstractPythonTool.__init__
        '''
        super(WbcHeaderIncluder, self).__init__(outputs = outputs)
    # end def __init__

    _ACTION = 'add include from'

    def _python(self, task):
        '''
        @copydoc actc.tools.AbstractPythonTool._cmd
        '''
        src = list(task.file_dep)[0]
        dst = task.targets[0]

        # SC04.01/client_headers_<module>.txt
        with open(src, 'r') as fo:
            lines = ['#include "%s"\n' % (line.strip(),) for line in fo.readlines()]
        # end fo


        src = re.sub(r'SC04.02(|-.*)(?=/.*$)', r'SC03\1', dst)  # Use the SC04.02 suffix with SC03 if it exists

        # SC04/<module>.h
        with open(src, 'r') as fo:
            lines.extend(fo.readlines())
        # end with

        # SC04.02/<module>.h
        with open(dst, 'w') as fo:
            fo.writelines(lines)
        # end with

        copyfile(src.replace('.h', '.c'), dst.replace('.h', '.c'))
    # end def _python

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractPythonTool.tasks
        '''
        # Create Folders
        yield super(WbcHeaderIncluder, self).tasks(*args, **kwargs)

        # Process Files
        path, _ = self._outputs[0]

        for arg in toList(args[0]):
            for src in iglob(abspath(arg)):

                dst = join(path, basename(src).replace('client_headers_', '') \
                                              .replace('.txt', '.h'))

                yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
                       'title'   : self._title,
                       'actions' : [self._python,],
                       'targets' : [dst,],
                       'file_dep': [src,],
                       }
            # end for
        # end for
    # end def tasks

# end class WbcHeaderIncluder

CONVERT_PRAGMAS = ['python', '/opt/wbc/convert_pragmas.py']

class WbcPragmaConverter(AbstractBasicCmdTool):
    '''
    Convert pragmas
    '''

    def __init__(self, program = None,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(WbcPragmaConverter, self).__init__(program = program,
                                                 options = options,
                                                 outputs = outputs)
    # end def __init__

    _ACTION = 'convert pragma from'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # input
        args.append(list(task.file_dep)[0])

        # output
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

# end class PragmaConverter

class WbcPragmaConverterReverse(AbstractBasicCmdTool):
    '''
    Convert pragmas back to their original
    '''

    def __init__(self, program = None,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(WbcPragmaConverterReverse, self).__init__(program = program,
                                                        options = options,
                                                        outputs = outputs)
    # end def __init__

    _ACTION = 'reverse pragma from'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        args.append('-r')

        # input
        args.append(list(task.file_dep)[0])

        # output
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

# end class PragmaConverterReverse

WBC = '/opt/wbc/wbc.x'

class WbcSourceRewriter(AbstractBasicCmdTool):
    '''
    WBC source rewriting tool
    '''

    def __init__(self, program = None,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(WbcSourceRewriter, self).__init__(program = program,
                                                options = options,
                                                outputs = outputs)
    # end def __init__

    _ACTION = 'rewrite'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # constraint
        args.insert(0, 'ulimit -s unlimited &&')

        # options
        args.extend(self._options)

        # output
        args.append('-o')
        args.append(task.targets[0])

        # input
        args.append(list(task.file_dep)[0])

        # [- -l logfile.json]
        args.append('-')
        args.append('-l')
        args.append(join(dirname(task.targets[0]), 'log',
                         basename(task.targets[0]) + '.json'))

        return ' '.join(args)
    # end def _cmd

# end class SourceRewriter

class WbcAnnotationExtractor(AbstractBasicCmdTool):
    '''
    Annotation extraction
    '''

    def __init__(self, program = None,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(WbcAnnotationExtractor, self).__init__(program = program,
                                                     options = options,
                                                     outputs = outputs)
    # end def __init__

    _ACTION = 'extract annotations'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # input
        args.append(list(task.file_dep)[0])

        # output
        args.append(task.targets[0])

        return args
    # end def _cmd

# end class AnnotationExtractor


class WbcDataObfuscator(AbstractBasicCmdTool):
    '''
    Annotation extraction
    '''

    def __init__(self, program = None,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(WbcDataObfuscator, self).__init__(program = program,
                                                options = options,
                                                outputs = outputs)
    # end def __init__

    _ACTION = 'obfuscate data'

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''
        args = list(self._program)

        # input
        args.append(list(task.file_dep)[0])

        # output
        args.append(task.targets[0])

        return args
    # end def _cmd

# end class WbcDataObfuscator

WBC_RENEW = '/opt/wbc/generate_license.py'

class WbcRenewabilityGenerator(AbstractPythonTool):
    '''
    WBC renewability script generator
    '''

    def __init__(self, outputs=None):
        '''
        @copydoc actc.tools.AbstractPythonTool.__init__
        '''
        super(WbcRenewabilityGenerator, self).__init__(outputs=outputs)
    # end def __init__

    _ACTION = 'generate script'

    def _python(self, task, wbta_tool, pre_opts, compile_opts, frontend, json_path, patch_tool):
        '''
        @copydoc actc.tools.AbstractPythonTool._cmd
        '''

        src = task.file_dep
        dst = task.targets[0]
        path = join(dirname(task.targets[0]), dst.split('.', 1)[0])
        license_file = dst.split('.', 1)[0] + '.lic'

        # Hack: parallel execution issue (create_folder not yet finished)
        while (not isdir(dirname(dst))):
            sleep(0.01)
        # end if

        # Generate renew script
        with open(dst, 'w') as script_file:
            script_file.write(
'''#!/usr/bin/env bash

# Parameters:
# 1: directory containing the mobile blocks to be patched

function usage {
  echo "Usage: ./%(SCRIPT)s <mobile_block_dir>"
  exit -1
}


# Check the number of parameters
if [ "$#" -ne 1 ]; then
    usage
fi

%(LICENSE_TOOL)s %(LICENSE)s

license_file=$( readlink -e %(LICENSE)s )
mobile_block_dir=$( readlink -e $1 )

if [ ! -d ${mobile_block_dir} ]; then
    usage
fi
''' % { 'LICENSE_TOOL' : WBC_RENEW,
        'SCRIPT' : basename(dst),
        'LICENSE' : basename(license_file), })
            # HACK, go the the json file directory, some paths in the config file are relative
            script_file.write('cd %s\n' % json_path)

            # Process xml file
            xml = list(src)[0]

            include = xml.replace('SLC03.02', 'SLC03.01').replace('xml', 'include')

            with open(include, 'r') as fo:
                lines = fo.readlines()
            #  end with

            source = ''
            if (lines):
                source = lines[0].strip().replace('"', '')
            # end if

            # found a source file,  generate compilation script
            if(source):
                pass

                # =============
                # WBTA
                # =============
                wbta_tool = ' '.join(wbta_tool)
                name = basename(xml).split('.', 1)[0]
                wbta_command = '%(TOOL)s -s %(SOURCE)s -o %(TARGET)s -n %(NAME)s -d ${license_file}' % {'TOOL': wbta_tool,
                                                                                             'SOURCE': xml,
                                                                                             'TARGET': path,
                                                                                             'NAME': name}
                script_file.write(wbta_command + '\n')

                # =============
                # PREPROCESSING
                # =============
                preprocessing = list([frontend, ])

                # options
                preprocessing.extend(pre_opts)
                preprocessing.append('-std=c99')
                preprocessing.append('-E')
                preprocessing.append('-P')

                # output
                preprocessing.append('-o')
                preprocessing.append(join(path, source + '.i'))

                # input
                preprocessing.append(join(path, source))

                script_file.write(' '.join(preprocessing) + '\n')


                # =============
                # COMPILATION
                # =============
                compilation = list([frontend, ])

                # options
                compilation.extend(compile_opts)

                # input
                compilation.append('-c')
                compilation.append(join(path, source + '.i'))

                # output
                compilation.append('-o')
                compilation.append(join(path, source + '.i.o'))

                script_file.write(' '.join(compilation) + '\n')

                # ==================
                # PATCH MOBILE BLOCK
                # ==================
                tool_name = 'update_mobile_blocks.sh'

                patch = list([join(patch_tool, tool_name), ])
                patch.append('${mobile_block_dir}')
                patch.append(join(path, source + '.i.o'))
                patch.append('wbc_' + basename(list(src)[0]).split('.', 1)[0])

                script_file.write(' '.join(patch) + '\n')

            # end if
        # end with

        # Make file executable
        st = os.stat(dst)
        os.chmod(dst, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # end def _python

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractPythonTool.tasks
        '''
        # Create Folders
        yield super(WbcRenewabilityGenerator, self).tasks(*args, **kwargs)

        # Process Files
        path, _ = self._outputs[0]

        for arg in toList(args[0]):
            for src in iglob(abspath(arg)):

                if not getsize(src):
                    continue
                # end if

                dst = join(path, "renew_" + basename(src).split('.', 1)[0] + ".sh")


                yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
                       'title'   : self._title,
                       'actions' : [self._python, ],
                       'params'  : [{'name'   : 'wbta_tool',
                             'short'  : None,
                             'default': kwargs.get('wbta_tool', ''),
                             },
                             {'name'   : 'pre_opts',
                             'short'  : None,
                             'default': kwargs.get('pre_opts', ''),
                             },
                             {'name'   : 'compile_opts',
                             'short'  : None,
                             'default': kwargs.get('compile_opts', ''),
                             },
                             {'name'   : 'frontend',
                             'short'  : None,
                             'default': kwargs.get('frontend', ''),
                             },
                             {'name'   : 'json_path',
                             'short'  : None,
                             'default': kwargs.get('json_path', ''),
                             },
                             {'name'   : 'patch_tool',
                             'short'  : None,
                             'default': kwargs.get('patch_tool', ''),
                             },
                            ],
                       'targets' : [dst, ],
                       'file_dep': [src, ],
                       }
            # end for
        # end for
    # end def tasks
# end class WbcRenewabilityGenerator

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
