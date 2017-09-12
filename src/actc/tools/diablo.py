#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2014-2016 Nagravision S.A., Gemalto S.A., Ghent University
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Nagravision S.A., Gemalto S.A., Ghent University, nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL NAGRAVISION S.A., GEMALTO S.A., OR GHENT UNIVERSITY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------
''' @package  actc.tools.diablo

@brief   Diablo frontend

@author  Ronan Le Gallic, Jeroen Van Cleemput, Jens Van den Broeck

@date    2014/10/21
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
import os
import stat

from os.path                    import basename
from os.path                    import dirname
from os.path                    import join
from os.path                    import isdir

from doit.action                import CmdAction

from actc.tools                 import toList
from actc.tools                        import AbstractBasicCmdTool
from actc.tools                 import AbstractCmdTool
from actc.tools                 import AbstractPythonTool

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

DIABLO_EXTRACTOR = '/opt/diablo/bin/diablo-extractor'
CONVERTER = '/opt/diablo/scripts/profiles/reverse-translate.py'

class ProfileTranslator(AbstractBasicCmdTool):
    '''
    ProfileTranslator
    '''

    def __init__(self, program = CONVERTER,
                       options = None,
                       outputs = ('build/bin', '.out')):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(ProfileTranslator, self).__init__(program = program,
                                     options = options,
                                     outputs = outputs)
    # end def __init__

    _ACTION = 'profiletranslation'

    def _cmd(self, task):                                                 # pylint:disable=W0221
        '''
        @copydoc actc.tools.AbstractCmdTool._cmd
        '''
        args = list(self._program)

        # options
        args.extend(self._options)

        return ' '.join(args)
    # end def _cmd

# end class ProfileTranslator


class DiabloExtractor(AbstractCmdTool):
    '''
    diablo-extractor
    '''

    def __init__(self, program = DIABLO_EXTRACTOR,
                       options = None,
                       outputs=None,
                       softvm_diversity_seed=None):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(DiabloExtractor, self).__init__(program = program,
                                              options = options,
                                              outputs = outputs)

        self._softvm_diversity_seed = softvm_diversity_seed
    # end def __init__

    _ACTION = 'extract'

    def _cmd(self, task, annotfile, objdir, bindir, binary):                                                       # pylint:disable=W0221
        '''
        @copydoc actc.tools.AbstractCmdTool._cmd
        '''
        args = list(self._program)

        # -v
        args.extend(self._options)

        args.append('--softvm-diversity-seed')
        args.append(self._softvm_diversity_seed)

        # -O <objdir>
        args.append('-O')
        args.append(objdir)

        # [-L [<libdir>]*]

        # --annotation-file <annotfile>
        args.append('--annotation-file')
        args.append(annotfile)

        # --instructionselector-path <isl>
        args.append('--instructionselector-path')
        args.append('/opt/xtranslator/libbin2vm_linux_pic.so')

        # --extractor-output-file <chunks_file>
        args.append('--extractor-output-file')
        args.append(task.targets[0])

        # --dots-before-path <initial_dot_dir>
        args.append('--dots-before-path')
        args.append(join(bindir, 'diablo-extractor-dots-before'))

        # <binary>
        args.append(binary)

        # > <log>
        args.append('>')
        args.append(join(bindir,'diablo-extractor.log'))

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(DiabloExtractor, self).tasks(*args, **kwargs)

        # Process Files
        path, _ = self._outputs[0]

        src = args[0]
        dst = join(path, basename(src).split('.', 1)[0] + '_chunks.json')

        yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd),],
               'params'  : [{'name'   : 'annotfile',
                             'short'  : None,
                             'default': src,
                             },
                            {'name'   : 'objdir',
                             'short'  : None,
                             'default': kwargs.get('objdir', '.'),
                             },
                            {'name'   : 'bindir',
                             'short'  : None,
                             'default': kwargs.get('bindir', '.'),
                             },
                            {'name'   : 'binary',
                             'short'  : None,
                             'default': kwargs.get('binary'),
                             },
                            ],
               'targets' : [dst,
                            ],
               'file_dep': [src,
                            ],
               'task_dep': ['_createfolder_' + path]
                       }
    # end def tasks

# end class DiabloExtractor


DIABLO_OBFUSCATOR = '/opt/diablo/bin/diablo-obfuscator'
DIABLO_SELFPROFILING = '/opt/diablo/bin/diablo-selfprofiling'

DIABLO_SP_OBJ_LINUX = '/opt/diablo/obj/printarm_linux.o'
DIABLO_SP_OBJ_ANDROID = '/opt/diablo/obj/printarm_android.o'

class DiabloObfuscator(AbstractCmdTool):
    '''
    diablo-obfuscation
    '''

    def __init__(self, aid,
                       program=DIABLO_OBFUSCATOR,
                       options = None,
                       outputs = None,
                       self_profiling = False,
                       softvm_diversity_seed=None,
                       code_mobility_diversity_seed=None):
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(DiabloObfuscator, self).__init__(program = program,
                                               options = options,
                                               outputs = outputs)
        self._self_profiling = self_profiling
        self._softvm_diversity_seed = softvm_diversity_seed
        self._code_mobility_diversity_seed = code_mobility_diversity_seed
        self._aid = aid
    # end def __init__

    _ACTION = 'obfuscate'

    def _cmd(self, task, objdir, stubdir, vmdir, annotfile, chunks_file, binary, runtime_profiles, runtime_profiles_obf):  # pylint:disable=W0221
        '''
        @copydoc actc.tools.AbstractCmdTool._cmd
        '''

        return generateDiabloCommand(self._program, self._options, self._self_profiling,
                                     self._softvm_diversity_seed, self._code_mobility_diversity_seed,
                                     task.targets[0], objdir, stubdir, vmdir, annotfile,
                                     chunks_file, binary, runtime_profiles, runtime_profiles_obf, self._aid)
    # end def _cmd


    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''
        # Create Folders
        yield super(DiabloObfuscator, self).tasks(*args, **kwargs)

        # Process Files
        srcs = toList(args[0])
        dsts = toList(args[1])

        # Process Files
        path, _ = self._outputs[0]

        yield {'name'    : self._name(self._ACTION, srcs, '\ninto', dsts),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd),],
               'params'  : [{'name'   : 'objdir',
                             'short'  : None,
                             'default': kwargs.get('objdir', '.'),
                             },
                            {'name'   : 'stubdir',
                             'short'  : None,
                             'default': kwargs.get('stubdir', '.'),
                             },
                            {'name'   : 'vmdir',
                             'short'  : None,
                             'default': kwargs.get('vmdir', '.'),
                             },
                            {'name'   : 'annotfile',
                             'short'  : None,
                             'default': srcs[0],
                             },
                            {'name'   : 'chunks_file',
                             'short'  : None,
                             'default': kwargs.get('chunks_file', '.'),
                             },
                            {'name'   : 'binary',
                             'short'  : None,
                             'default': srcs[1],
                             },
                            {'name'   : 'runtime_profiles',
                             'short'  : None,
                             'default': kwargs.get('runtime_profiles', None),
                             },
                            {'name'   : 'runtime_profiles_obf',
                             'short'  : None,
                             'default': kwargs.get('runtime_profiles_obf', None),
                             },
                            ],
               'targets' : dsts,
               'file_dep': srcs,
               'task_dep' : ['_createfolder_' + path],
               }
    # end def tasks

# end class DiabloObfuscator

class RenewableMobileBlocksGenerator(AbstractPythonTool):
    '''
    WBC renewability script generator
    '''

    def __init__(self, aid,
                       program=DIABLO_OBFUSCATOR,
                       options=None,
                       outputs=None,
                       self_profiling=False,
                       softvm_diversity_seed=None,
                       code_mobility_diversity_seed=None,
                       script=None,  # Code mobility deployment script
                       ip_addr=None,  # Code mobility server ip address
                       block_path=None):  # Code mobility mobile block path
        '''
        @copydoc actc.tools.AbstractCmdTool.__init__
        '''
        super(RenewableMobileBlocksGenerator, self).__init__(outputs=outputs)

        # Needed to create the diablo command line using DiabloObfuscator._cmd
        self._program = program
        self._options = options
        self._self_profiling = self_profiling
        self._softvm_diversity_seed = softvm_diversity_seed
        self._code_mobility_diversity_seed = code_mobility_diversity_seed
        self._aid = aid
        self._script = script
        self._ip_addr = ip_addr
        self._block_path = block_path
    # end def __init__

    _ACTION = 'generate script'

    def _python(self, task, objdir, stubdir, vmdir, annotfile, chunks_file, binary, runtime_profiles, runtime_profiles_obf, dst_object):
        '''
        @copydoc actc.tools.AbstractPythonTool._cmd
        '''

        src = task.file_dep
        dst = task.targets[0]
        path = join(dirname(task.targets[0]), dst.split('.', 1)[0])

        # Generate renew script
        with open(dst, 'w') as script_file:
            script_file.write(
'''#!/usr/bin/env bash

# Parameters:
# 1: optional random seed

function usage {
  echo "Usage: ./%(SCRIPT)s [randomseed]"
  exit -1
}

# Check the number of parameters
if [ "$#" -ge 2 ]; then
    usage
fi

random_seed=0
if [ "$#" -ne 1 ]; then
    random_seed=$( od -An -t d4 -N4  /dev/urandom | tr -d '[[:space:]]')
else
    random_seed=$1
fi

echo "Generation new mobile blocks using random seed ${random_seed}"

''' % { 'SCRIPT' : basename(dst), })
            # HACK, go the the json file directory, some paths in the config file are relative
            script_file.write(generateDiabloCommand([self._program, ], self._options, self._self_profiling,
                                                    self._softvm_diversity_seed, '${random_seed}',
                                                    dst_object, objdir, stubdir, vmdir, annotfile,
                                                    chunks_file, binary, runtime_profiles, runtime_profiles_obf, self._aid).replace('%%', '%') + '\n')



            script_file.write(' '.join([self._script,
                                                '-a' , self._aid,
                                                '-p', '20',
                                                '-i', self._ip_addr,
                                                self._block_path,
                                                '\n']))

        # end with

        # Make file executable
        st = os.stat(dst)
        os.chmod(dst, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # end def _python

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''

        # Process Files
        srcs = toList(args[0])
        dsts = toList(args[1])

        # Process Files
        path, _ = self._outputs[0]

        yield {'name'    : self._name(self._ACTION, srcs, '\ninto', dsts),
               'title'   : self._title,
               'actions' : [self._python, ],
               'params'  : [{'name'   : 'objdir',
                             'short'  : None,
                             'default': kwargs.get('objdir', '.'),
                             },
                            {'name'   : 'stubdir',
                             'short'  : None,
                             'default': kwargs.get('stubdir', '.'),
                             },
                            {'name'   : 'vmdir',
                             'short'  : None,
                             'default': kwargs.get('vmdir', '.'),
                             },
                            {'name'   : 'annotfile',
                             'short'  : None,
                             'default': srcs[0],
                             },
                            {'name'   : 'chunks_file',
                             'short'  : None,
                             'default': kwargs.get('chunks_file', '.'),
                             },
                            {'name'   : 'binary',
                             'short'  : None,
                             'default': srcs[1],
                             },
                             {'name'   : 'runtime_profiles',
                             'short'  : None,
                             'default': kwargs.get('runtime_profiles', None),
                             },
                            {'name'   : 'runtime_profiles_obf',
                             'short'  : None,
                             'default': kwargs.get('runtime_profiles_obf', None),
                             },
                            {'name'   : 'dst_object',
                             'short'  : None,
                             'default': kwargs.get('dst_object', ''),
                             },
                            ],
               'targets' : dsts,
               'file_dep': srcs,
               'task_dep' : ['_createfolder_' + path],
               }
    #  end def tasks
# end class RenewableMobileBlocksGenerator

def generateDiabloCommand(program, options, self_profiling, softvm_diversity_seed, code_mobility_diversity_seed, target, objdir, stubdir, vmdir, annotfile, chunks_file, binary, runtime_profiles, runtime_profiles_obf, aid):
    args = list(program)

    # Hack: run program in output folder (ads file generation)
    args.insert(0, 'cd %s &&' % (dirname(target)))

    # -v
    args.extend(options)
    
    if(aid):
        args.append('--id')
        args.append(aid)

    if(softvm_diversity_seed):
        args.append('--softvm-diversity-seed')
        args.append(softvm_diversity_seed)

    if(code_mobility_diversity_seed):
      args.append('--code_mobility_diversity_seed')
      args.append(code_mobility_diversity_seed)

    # --blockprofilefile <blockprofilefile>

    # --annotation-file <annotfile>
    args.append('--annotation-file')
    args.append(annotfile)

    if(not self_profiling):
        # -L vmdir[:<libdir>]*
        args.append('-L')
        args.append(vmdir)
        # end if

        # --instructionselector-path <isl>
        args.append('--instructionselector-path')
        args.append(join(dirname(dirname(vmdir)), 'libbin2vm_linux_pic.so'))

        # --extractor-output-file <chunks_file>
        args.append('--extractor-output-file')
        args.append(chunks_file)
        # end if

        # -CMO <mobile_blocks_dir>
        args.append('-CMO')
        args.append(join(dirname(target), 'mobile_blocks', '$( date "+%%Y%%m%%d%%H%%M%%S" )_' + code_mobility_diversity_seed))

        # --transformation-log-path <log_dir>
        args.append('--transformation-log-path')
        args.append(join(dirname(target), 'transformation-logs'))

        # --dots-before-path <initial_dot_dir>
        args.append('--dots-before-path')
        args.append(join(dirname(target), 'diablo-obfuscator-dots-before'))

        # --dots-after-path <final_dot_dir>
        args.append('--dots-after-path')
        args.append(join(dirname(target), 'diablo-obfuscator-dots-after'))

    if(runtime_profiles or runtime_profiles_obf):
        args.append('--rawprofiles')
        args.append('off')

    if(runtime_profiles):
        args.append('--blockprofilefile')
        args.append(runtime_profiles)

# TODO BART uncomment this when obfuscated runtime profiles are supported
#     if(runtime_profiles_obf):
#         args.append('--blockprofilefile-obfuscated')
#         args.append(runtime_profiles_obf)

    # -O <objdir>:<stubdir>:<vmdir>
    args.append('-O')
    args.append(':'.join([objdir, stubdir, vmdir]))

    # -o <output>
    args.append('-o')
    args.append(target)

    # <binary>
    args.append(binary)

    # > <log>
    args.append('>')
    args.append(join(dirname(target), 'diablo-obfuscator.log'))

    return ' '.join(args)
#end def generateDiabloCommand

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
