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
''' @package  actc.core

@brief   Main

@author  Ronan Le Gallic, Jeroen Van Cleemput

@date    2014/10/06
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from glob                       import glob
from glob                       import iglob
from os                         import stat
from os                         import getcwd
from os                         import listdir
from os                         import symlink
from os                         import remove
from os.path                    import abspath
from os.path                    import basename
from os.path                    import dirname
from os.path                    import isdir
from os.path                    import isfile
from os.path                    import islink
from os.path                    import getsize
from os.path                    import join
from os.path                    import sep
from subprocess                 import call
from time                       import strftime
from uuid                       import getnode
from collections                import OrderedDict
import hashlib

from doit.action                import CmdAction
from doit.tools                 import LongRunning
from doit.tools                 import check_timestamp_unchanged

from actc.config                import Config
from actc.consts                import CFG_JOBS
from actc.dodo                  import AbstractDodo
from actc.dodo                  import monoprocess

from actc.tools                 import toList
from actc.tools.annotation      import AnnotationExtractor
from actc.tools.annotation      import AnnotationMerger
from actc.tools.annotation      import filterAnnotations
from actc.tools.annotation      import AnnotationPatcher
from actc.tools.annotation      import AnnotationRewriter
from actc.tools.annotation      import updateFolders
from actc.tools.codesurfer      import CodeSurferInitializer


from actc.tools.data            import DataObfuscator

from actc.tools.diablo          import DiabloExtractor
from actc.tools.diablo          import DiabloObfuscator
from actc.tools.diablo          import RenewableMobileBlocksGenerator
from actc.tools.diablo          import DIABLO_SP_OBJ_LINUX
from actc.tools.diablo          import DIABLO_SP_OBJ_ANDROID
from actc.tools.diablo          import ProfileTranslator

from actc.tools.compiler        import Compiler
from actc.tools.compiler        import CompilerSO
from actc.tools.compiler        import Linker
from actc.tools.compiler        import Preprocessor
from actc.tools.compiler        import Archiver

from actc.tools.remote          import AttestatorSelector
from actc.tools.remote          import AntiCloning
from actc.tools.remote          import ReactionUnit
from actc.tools.remote          import ControlFlowTagging
from actc.tools.remote          import DiversifiedCryptoLibrary

from actc.tools.codeguard       import CodeGuard

from actc.tools.splitter        import SplitterProcess
from actc.tools.splitter        import SplitterCodeTransformation

from actc.tools.utils           import Copier

from actc.tools.wbc             import WbcAnnotationReader
from actc.tools.wbc             import WbcHeaderIncluder
from actc.tools.wbc             import WbcPragmaConverter
from actc.tools.wbc             import WbcPragmaConverterReverse
from actc.tools.wbc             import WbcSourceRewriter
from actc.tools.wbc             import WbcXmlConfigGenerator
from actc.tools.wbc             import WbcLicenseTool
from actc.tools.wbc             import WbcWhiteBoxTool
from actc.tools.wbc             import WbcRenewabilityGenerator

from actc.tools.xtranslator     import Xtranslator

from actc.tools.renewability    import RenewabilityCreate
from actc.tools.renewability    import RenewabilityPolicy

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------
class Actc(AbstractDodo):                                                       # pylint:disable=R0902
    '''
    Aspire Compiler Tool Chain
    '''

    def __init__(self, path, debug = False, verbose = False, aid = None):
        '''
        Constructor

        @param path [in] (str) configuration file
        '''
        self._json   = abspath(path)
        self._config = Config(path)

        # .../aspire.json --> build/*
        # .../<module>.json --> build/<module>/*
        self._module = basename(path).split('.', 1)[0]
        output = 'build/%s' % (self._module if self._module != 'aspire' else '.',)

        super(Actc, self).__init__(output = output, debug = debug, verbose = verbose)

        if aid is None:
            # Get the hardware address as a 48-bit positive integer.
            mac = getnode()
            if ((mac >> 40) % 2):
                # The first time this runs, it may launch a separate program, which could
                # be quite slow.  If all attempts to obtain the hardware address fail, we
                # choose a random 48-bit number with its eighth bit set to 1 as recommended
                # in RFC 4122.
                raise OSError('MAC address not available')
            # end if

            # AID = md5(json path + mac address)
            md5 = hashlib.md5()
            md5.update(self._json)
            md5.update('%X' % (mac,))
            self._aid = md5.hexdigest().upper()
        else:
            # In case AID is fixed
            print "Fixing AID to: " + str(aid)
            self._aid = aid

        with open(join(self._output, 'AID.txt'), 'w') as fo:
            fo.write(self._aid)
        # end with

        # src2src
        self._skip_SLP01    = False
        self._skip_SLP02    = False
        self._skip_SLP03    = False
        self._skip_SLP03_01 = False
        self._skip_SLP03_02 = False
        self._skip_SLP03_03 = False
        self._skip_SLP03_04 = False
        self._skip_SLP03_05 = False
        self._skip_SLP04    = False
        self._skip_SLP05    = False
        self._skip_SLP05_01 = False
        self._skip_SLP05_02 = False

        self._skip_SLP06    = False
        self._skip_SLP06_01 = False
        self._skip_SLP06_02 = False
        self._skip_SLP06_03 = False

        self._skip_SLP07    = False
        self._skip_SLP08    = False
        self._skip_SLP09    = False
        self._skip_SLP10    = False
        self._skip_SLP11    = False
        self._skip_SLP12    = False

        # bin2bin
        self._skip_BLP00       = False
        self._skip_BLP00_01    = False
        self._skip_BLP00_02    = False
        self._skip_BLP00_03    = False
        self._skip_BLP01       = False
        self._skip_BLP02       = False
        self._skip_BLP03       = False
        self._skip_BLP04       = False
        self._skip_BLP04_01    = False
        self._skip_BLP04_02    = False
        self._skip_BLP04_DYN    = False
        self._skip_BLP04_DYN_01 = False
        self._skip_BLP04_DYN_02 = False

        # metrics
        self._skip_M01      = False
        self._skip_M01_01   = False
        self._skip_M01_02   = False
        self._skip_M01_03   = False
        self._skip_M01_04   = False

        # dot
        self._dotTasks      = None

        #Headers
        self.accl_headers       = join(self._config.tools.accl,'include')
        self.ascl_headers       = join(self._config.tools.ascl,'include')

        self.curl_headers       = join(self._config.tools.third_party,
                                       'curl', self._config.platform, 'include')

        self.openssl_headers    = join(self._config.tools.third_party,
                                       'openssl', self._config.platform, 'include')

        self.websocket_headers  = join(self._config.tools.third_party,
                                       'libwebsockets', self._config.platform, 'include')

        # librariess
        self.curl_lib           = join(self._config.tools.third_party,
                                       'curl', self._config.platform, 'lib')

        self.openssl_lib        = join(self._config.tools.third_party,
                                       'openssl', self._config.platform, 'lib')

        self.websocket_lib      = join(self._config.tools.third_party,
                                       'libwebsockets', self._config.platform, 'lib')

        # Annotation flags used to enable/disable binary protection techniques or link in required libraries, populated in SLP04_parse
        self._binary_annotations = dict()

        # List of annotations per task
        self._annotations_list = {'SLP03' : ['wbc'],  # WBC
                                  'SLP05' : ['data_to_proc', 'rnc', 'xor', 'merge_vars'],  # Data obfuscation
                                  'SLP06' : ['barrier_slicing', ],  # Client-server splitter
                                  'SLP08' : ['guarded_region', 'guard_attestator', 'guard_verifier', ],  # Code guards
                                  'SLP09' : ['anti_cloning', ],  # Anti-cloning
                                  'SLP10' : ['timebombs'],  # Reaction unit
                                  'SLP11' : ['dcl'],  # Diversified crypto lib
                                  'SLP12' : ['cf_tagging'],  # Control flow tagging
                                  'SLP04' : [],  # Annotation Extraction (updated below)
                                  'SLP07' : ['remote_attestation', 'invariant_monitoring'],  # Remote attestation
                                  'BLP04' : ['call_stack_check', 'anti_debugging', 'softvm', 'obfuscations', 'code_mobility', ],  # Binary obfuscations (updated below)
                                  }
        # BLP04 needs some source code annotations
        self._annotations_list['BLP04'].extend(self._annotations_list['SLP07'])
        self._annotations_list['BLP04'].extend(self._annotations_list['SLP08'])

        # Annotations for BLP04 are extracted during SLP04
        self._annotations_list['SLP04'].extend(self._annotations_list['BLP04'])

        # Output folders of the individual source code tasks, can be updated by the caching tool
        self._folders = OrderedDict()
        self._folders['SLP01'] = {'out': 'SC02', 'suffix' : ''}  # get source code and annotate
        self._folders['SPLIT_C'] = {'out': 'SC03', 'suffix' : ''}
        self._folders['SLP03'] = {'intermediate' :'SLC03', 'out': 'SC04', 'suffix' : ''}  # WBC
        self._folders['SLP02'] = {'out': 'SC05', 'suffix' : ''}  # preprocessing
        self._folders['SLP05'] = {'out': 'SC06', 'suffix' : ''}  # Data obfuscation
        self._folders['SLP06'] = {'out': 'SC07', 'server' : 'SCS01', 'suffix' : ''}  # Client-server splitter
        self._folders['SLP08'] = {'out': 'SC08', 'suffix' : ''}  # Code guards
        self._folders['SLP09'] = {'out': 'SC09', 'suffix' : ''}  # Anti-cloning
        self._folders['SLP10'] = {'out': 'SC10', 'suffix' : ''}  # Reaction unit
        self._folders['SLP11'] = {'out': 'SC11', 'suffix' : ''}  # DCL
        self._folders['SLP12'] = {'out': 'SC12', 'out_be': 'SC12.01', 'suffix': ''}  # Control Flow Tagging, with BackEnd output
        self._folders['SPLIT_CPP'] = {'out': 'SC12', 'suffix' : ''}  # Changed order to make sure suffix is calculated correctly
        self._folders['SPLIT_FORTRAN'] = {'out': 'SC12', 'suffix' : ''}  # Changed order to make sure suffix is calculated correctly
        self._folders['SLP04'] = {'out': 'D01', 'suffix' : ''}  # Annotation extraction
        self._folders['SLP07'] = {'out': 'BC07', 'suffix' : ''}  # Remote attestation
        self._folders['COMPILE_C'] = {'out': 'BC08', 'suffix' : ''}  # Compile C files
        self._folders['COMPILE_CPP'] = {'out': 'BC08', 'suffix' : ''}  # Compile CPP files, same as COMPILE_C
        self._folders['COMPILE_FORTRAN'] = {'out': 'BC08', 'suffix' : ''}  # Compile Fortran files
        self._folders['ACCL'] = {'out': 'BC08', 'suffix' : ''}  # Compile ACCL files
        self._folders['LINK'] = {'out': 'BC02', 'suffix' : ''}  # Linker

        self._folders['BLP00'] = {'out_sp': 'BC02_SP', 'out_dyn': 'BC02_DYN', 'out_migrate': 'profile_BC02_migrated_to_BC04', 'suffix' : ''}  # Self-profiling binaries on vanilla
        self._folders['BLP01'] = {'out': 'BLC02', 'suffix' : ''}  # Extractor
        self._folders['BLP02'] = {'out': 'BC03', 'suffix' : ''}
        self._folders['BLP03'] = {'out': 'BC04', 'suffix' : ''}
        self._folders['BLP04'] = {'out': 'BC05', 'suffix' : ''}
        self._folders['BLP04_DYN'] = {'out': 'BC05_DYN', 'suffix' : ''}
        self._folders['M01'] = {'out': 'M01', 'suffix' : ''}

        # Generate output folders based on annotation configuration is caching is enabled
        self._caching = True if self._config.src2src.SLP01.external_annotations and self._config.src2src.SLP01.annotations_patch else False
        if(self._caching):
            updateFolders(self._folders, self._config.src2src.SLP01.external_annotations, self._annotations_list)

    # end def __init__


    def build(self, jobs = CFG_JOBS):
        '''
        @copydoc actc.dodo.AbstractDodo.build
        '''
        # Force to rebuild after configuration file update
        if (isfile(self._dep_file)):
            if (stat(self._config.path).st_mtime > stat(self._dep_file).st_mtime):
                self._doIt('forget')
            # end if
        # end if

        super(Actc, self).build(jobs = jobs)
    # end def build

    # pylint:disable=W0212

    # ==========================================================================
    def task_SLP01(self):
        '''
        Get source code (with annotations) --> SC02

        @return (Task)
        '''
        self._dotTasks = list()

        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP01 = self._config.src2src.excluded \
                        or self._config.src2src.SLP01.excluded

        if (self._skip_SLP01):
            return
        # end if

        # input and output folders
        output_folder = self._folders['SLP01']['out'] + self._folders['SLP01']['suffix']

        # Get source code
        # ----------------------------------------------------------------------
        src = self._config.src2src.SLP01.source

        # Copy ADSS generated patch file if present
        if(self._config.src2src.SLP01.annotations_patch):
            src.append(self._config.src2src.SLP01.annotations_patch)

        # Copy ADSS generated external annotations file if present
        if(self._config.src2src.SLP01.external_annotations):
            src.append(self._config.src2src.SLP01.external_annotations)

        dst = join(self._output, output_folder)

        tool = Copier(outputs = (dst, ''))
        yield tool.tasks(src)
    # end def task_SLP01

    # ==========================================================================
    def task_SLP01_patch(self):
        '''
        SC02 --> Replace security requirement annotations  with unique ID placeholders using an ADSS patch file --> SC02

        @return (Task)
        '''

        patch_file = join(self._output, 'SC02', basename(self._config.src2src.SLP01.annotations_patch))
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP01
            or self._config.src2src.SLP01.traverse
            or not patch_file
            or not isfile(patch_file)):
            return
        # end if

        # input and output folders
        output_folder = self._folders['SLP01']['out'] + self._folders['SLP01']['suffix']


        # Get source code
        # ----------------------------------------------------------------------
        src = patch_file
        dst = join(self._output, output_folder, '.patched')

        tool = AnnotationPatcher(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP01_patch', output_folder, output_folder)
    # end def task_SLP01_patch

    # ==========================================================================
    def task_SPLIT_C(self):
        '''
        SC02 --> split source code (.c|.h) --> SC03

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP01):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP01']['out'] + self._folders['SLP01']['suffix']
        output_folder = self._folders['SPLIT_C']['out'] + self._folders['SPLIT_C']['suffix']

        # Split *.c | *.h
        # ----------------------------------------------------------------------
        src  = [join(self._output, input_folder, '*.c'),
                join(self._output, input_folder, '*.h')]

        dst  =  join(self._output, output_folder)

        tool = Copier(outputs = (dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SPLIT_C', input_folder, output_folder)
    # end def task_SPLIT_C


    # ==========================================================================
    def task_SPLIT_CPP(self):
        '''
        SC02 --> split source code (.cpp|.hpp|.h) --> SC012

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP01):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP01']['out'] + self._folders['SLP01']['suffix']
        output_folder = self._folders['SPLIT_CPP']['out'] + self._folders['SPLIT_CPP']['suffix']

        # Split *.cpp | *.hpp | *.h
        # ----------------------------------------------------------------------
        src  = [join(self._output, input_folder, '*.cpp'),
                join(self._output, input_folder, '*.hpp'),
                join(self._output, input_folder, '*.h')]

        dst  =  join(self._output, output_folder)

        tool = Copier(outputs = (dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SPLIT_CPP', input_folder, output_folder)
    # end def task_SPLIT_CPP

    # ==========================================================================
    def task_SPLIT_FORTRAN(self):
        '''
        SC02 --> split source code (.f) --> SC012

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP01):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP01']['out'] + self._folders['SLP01']['suffix']
        output_folder = self._folders['SPLIT_FORTRAN']['out'] + self._folders['SPLIT_FORTRAN']['suffix']

        # Split *.f
        # ----------------------------------------------------------------------
        src  = [join(self._output, input_folder, '*.f'),
                join(self._output, input_folder, '*.f90')]

        dst  =  join(self._output, output_folder)

        tool = Copier(outputs = (dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SPLIT_FORTRAN', input_folder, output_folder)
    # end def task_SPLIT_FORTRAN

    # ==========================================================================
    def task_SLP03(self):
        '''
        SC03 --> white-box crypto --> SC04

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP03 = self._config.src2src.excluded \
                        or self._config.src2src.SLP03.excluded

        if (self._skip_SLP03):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SPLIT_C']['out'] + self._folders['SPLIT_C']['suffix']
        output_folder = self._folders['SLP03']['out'] + self._folders['SLP03']['suffix']

        # SC03 --> Traverse --> SC04
        # ----------------------------------------------------------------------
        if (self._config.src2src.SLP03.traverse):

            self._skip_SLP03 = True

            src = [join(self._output, input_folder, '*.h'),
                    join(self._output, input_folder, '*.c')]

            dst = join(self._output, output_folder)

            tool = Copier(outputs = (dst, ''))

            yield tool.tasks(src)

            # ------------------------------------------------------------------
            self._updateDot('SLP03_TRAVERSE', input_folder, output_folder)

        # end if

    # end def task_SLP03

    def task_SLP03_cache(self):
        '''
        SC03 --> Cache a copy with the new suffix --> SC03

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03
            or not self._caching):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SPLIT_C']['out'] + self._folders['SPLIT_C']['suffix']
        output_folder = self._folders['SPLIT_C']['out'] + self._folders['SLP03']['suffix']

        # Return of no caching is required
        if(input_folder == output_folder):
            return

        # Copy source files
        # ----------------------------------------------------------------------
        src = [join(self._output, input_folder, '*.h'),
                    join(self._output, input_folder, '*.c')]

        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_cache', input_folder, output_folder)
    # end def task_SLP03_cache

    def task_SLP03_annotate(self):
        '''
        SC03 --> Replace security requirement annotations (see D5.01) with some "concrete annotations" --> SC03

        @return (Task)
        '''

        external_annotations = self._config.src2src.SLP01.external_annotations
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03
            or self._config.src2src.SLP03.traverse
            or not external_annotations
            or not isfile(external_annotations)):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SPLIT_C']['out'] + self._folders['SLP03']['suffix']
        output_folder = input_folder


        # Get source code
        # ----------------------------------------------------------------------
        src = external_annotations
        dst = join(self._output, output_folder, '.annotated')

        tool = AnnotationRewriter(outputs=(dst, ''))
        yield tool.tasks(src,
                        filter=self._annotations_list['SLP03'],
                        keep_placeholders=False,  # TXL based tools do not support multiple protections in a single annotation
                        replace_all=False,
                        preprocessed=False,)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_annotate', input_folder, output_folder)
    # end def task_SLP03_annotate


    # ==========================================================================
    def task_SLP03_01(self):
        '''
        SC03 --> WBC annotation extraction tool

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP03_01 = self._skip_SLP03 \
                           or self._config.src2src.SLP03._01.excluded

    # end def task_SLP03_01

    # ==========================================================================
    def task_SLP03_01_EXTRACT(self):
        '''
        SC03 --> Extract annotations --> SLC03.01

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_01):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SPLIT_C']['out'] + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['intermediate'] + '.01' + self._folders['SLP03']['suffix']

        # Extract annotations
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.c')

        dst = join(self._output, output_folder)

        tool = WbcAnnotationReader(program = self._config.tools.annotation_reader,
                                   outputs = (dst, '.annot'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_01_EXTRACT', input_folder, output_folder)
    # end def task_SLP03_01_EXTRACT

    # ==========================================================================
    def task_SLP03_01_XML(self):
        '''
        SLC03.01 --> XML generation from annotated files --> SLC03.02

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_01):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP03']['intermediate'] + '.01' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['intermediate'] + '.02' + self._folders['SLP03']['suffix']

        # SLC03.01/<module>.c.annot --> SLC03.01/<module>.c.annot.include
        #                               SLC03.02/<module>.c.annot.xml
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.annot')

        dst = join(self._output, output_folder)

        tool = WbcXmlConfigGenerator(program = self._config.tools.config,
                                     outputs = (dst, '.xml'))

        modules = list()
        for module in iglob(src):
            if (getsize(module)):
                modules.append(module)
            # end if
        # end for
        yield tool.tasks(modules)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_01_XML', input_folder, output_folder)
    # end def task_SLP03_01_XML

    # ==========================================================================
    def task_SLP03_01_PREPROCESS(self):
        '''
        SLC03.01 --> Preprocess not annotated files --> SC04

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_01):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SPLIT_C']['out'] + self._folders['SLP03']['suffix']
        intermediate_folder = self._folders['SLP03']['intermediate'] + '.01' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + self._folders['SLP03']['suffix']

        # SLC03.01/<module>.c.annot is empty
        #
        # SC03/<module>.c --> SC04/<module>.c.i
        # ----------------------------------------------------------------------
        src = join(self._output, intermediate_folder, '*.annot')

        dst = join(self._output, output_folder)

        tool = Preprocessor(program = self._config.tools.frontend,
                            options = self._config.src2bin.options
                            + self._config.src2bin.PREPROCESS.options
                            + ['-D', 'ASPIRE_AID=%s' % (self._aid,)],
                            outputs = (dst, '.i'))

        modules = list()
        for module in iglob(src):
            if (not getsize(module)):
                modules.append(module.replace(intermediate_folder, input_folder) \
                                     .replace('.c.annot', '.c'))
            # end if
        # end for
        yield tool.tasks(modules,
                        header_files=[join(self._output, input_folder, '*.h'), ])

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_01_PREPROCESS', input_folder, output_folder)
    # end def task_SLP03_01_PREPROCESS


    # ==========================================================================
    def task_SLP03_02(self):
        '''
        SLC03.02 --> WBC tool --> SC04.01

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP03_02 = self._skip_SLP03 \
                           or self._config.src2src.SLP03._02.excluded

    # end def task_SLP03_02

    # ==========================================================================
    def task_SLP03_02_LICENSE(self):
        '''
        Generate License file --> SLC03.02/license.json

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_02
            or self._config.src2src.SLP03.seed not in ('aid', 'random')):
            return
        # end if

        # input and output folders
        output_folder = self._folders['SLP03']['intermediate'] + '.02' + self._folders['SLP03']['suffix']


        # wbta_license generator tool --> SLC03.02/license.json
        # ----------------------------------------------------------------------

        dst = join(self._output, output_folder, 'license.json')

        tool = WbcLicenseTool(program=self._config.tools.wbta_license)

        if(self._config.src2src.SLP03.seed == 'aid'):
            seed_source = (self._aid + self._aid).lower()
        else:
            seed_source = None

        yield tool.tasks(dst,
                         seed=seed_source)

        # ----------------------------------------------------------------------
        self._updateDot('task_SLP03_02_LICENSE', self._config.tools.wbta_license , output_folder)
    # end def task_SLP03_02_LICENSE

    # ==========================================================================
    def task_SLP03_02_WHITEBOX(self):
        '''
        SLC03.02 --> WBC tool --> SC04.01

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP03']['intermediate'] + '.02' + self._folders['SLP03']['suffix']
        include_folder = self._folders['SLP03']['intermediate'] + '.01' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + '.01' + self._folders['SLP03']['suffix']

        # SLC03.02/<module>.c.annot.xml
        #                           |
        # SLC03.01/<module>.c.annot.include
        #                           |
        #                           "<wbfile>.c"
        #
        # SLC03.02/<module>.c.annot.xml --> SC04.01/<wbfile>.c
        #                                   SC04.01/client_headers_file.txt
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.xml')

        dst = join(self._output, output_folder)

        tool = WbcWhiteBoxTool(program = self._config.tools.wbta,
                               outputs=(dst, ''))

        srcs = list()
        dsts = list()
        for xml in iglob(src):

            include = xml.replace(input_folder, include_folder).replace('xml', 'include')

            with open(include, 'r') as fo:
                lines = fo.readlines()
            # end with

            if (lines):
                srcs.append(xml)
                dsts.append(lines[0].strip().replace('"', ''))
            # end if
        # end for

        lf=None
        if(self._config.src2src.SLP03.seed != 'none'):
            lf = join(self._output, input_folder, 'license.json')
        # end if

        yield tool.tasks(srcs, dsts,
                         license_file=lf)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_02_WHITEBOX', input_folder, output_folder)
    # end def task_SLP03_02_WHITEBOX

    # ==========================================================================
    def task_SLP03_02_PREPROCESS(self):
        '''
        SC03.02 --> Preprocess not included files --> SC04

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP03']['intermediate'] + '.02' + self._folders['SLP03']['suffix']
        include_folder = self._folders['SLP03']['intermediate'] + '.01' + self._folders['SLP03']['suffix']
        sources_folder = self._folders['SPLIT_C']['out'] + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + self._folders['SLP03']['suffix']

        # SLC03.02/<module>.c.annot.xml
        #                           |
        # SLC03.01/<module>.c.annot.include is empty
        #
        # SC0<module>le.c --> SC04/<module>.c.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.xml')

        dst = join(self._output, output_folder)

        tool = Preprocessor(program = self._config.tools.frontend,
                            options = self._config.src2bin.options
                            + self._config.src2bin.PREPROCESS.options
                            + ['-I', join(self._output, sources_folder),
                               '-D', 'ASPIRE_AID=%s' % (self._aid,)],
                            outputs = (dst, '.i'))

        modules = list()
        for xml in iglob(src):

            include = xml.replace(input_folder, include_folder).replace('xml', 'include')

            if (not getsize(include)):
                modules.append(xml.replace(input_folder, sources_folder) \
                                  .replace('.c.annot.xml', '.c'))
            # end if
        # end for
        yield tool.tasks(modules,
                         header_files=[join(self._output, sources_folder, '*.h'), ])

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_02_PREPROCESS', sources_folder, output_folder)
    # end def task_SLP03_02_PREPROCESS

    # ==========================================================================
    def task_SLP03_03(self):
        '''
        SC03 + SC04.01 --> Header inclusion tool --> SC04.02

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP03_03 = self._skip_SLP03 \
                           or self._config.src2src.SLP03._03.excluded

    # end def task_SLP03_03

    # ==========================================================================
    def task_SLP03_03_HEADER(self):
        '''
        SC03 + SC04.01 --> Header inclusion tool --> SC04.02

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_03):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP03']['out'] + '.01' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + '.02' + self._folders['SLP03']['suffix']

        # SC04.01/client_headers_<module>.txt
        #                        |
        # SC03/<module>.h       -+->  SC04.02/<module>.h
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, 'client_headers_*.txt')

        dst = join(self._output, output_folder)

        tool = WbcHeaderIncluder(outputs = (dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_03_HEADER', input_folder, output_folder)
    # end def task_SLP03_03_HEADER


    # ==========================================================================
    def task_SLP03_03_MERGE(self):
        '''
        SC04.01 \
                 --> merge source code --> SC04.03
        SC04.02 /

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_03):
            return
        # end if

        # input and output folders
        input_folder1 = self._folders['SLP03']['out'] + '.01' + self._folders['SLP03']['suffix']
        input_folder2 = self._folders['SLP03']['out'] + '.02' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + '.03' + self._folders['SLP03']['suffix']

        # SC04.01/client_*_<module>.txt
        #                   |
        #          SC04.01/<module>.* -+
        #                              |
        #          SC04.02/*.h -+------+-> SC04.03
        #          SC04.02/*.c -+
        # ----------------------------------------------------------------------
        src = [join(self._output, input_folder2, '*.c'),
                join(self._output, input_folder2, '*.h')]

        dst = join(self._output, output_folder)

        tool = Copier(outputs = (dst, ''))

        for client in iglob(join(self._output, input_folder1, 'client_*.txt')):

            with open(client, 'r') as fo:
                for module in fo.readlines():
                    module = join(self._output, input_folder1, module.strip())

                    if (module not in src):
                        src.append(module)
                    # end if
                # end for
            # end with
        # end for

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_03_MERGE', [input_folder1, input_folder2], output_folder)
    # end def task_SLP03_03_MERGE

    # ==========================================================================
    def task_SLP03_04(self):
        '''
        SC04.03 --> preprocessor --> SC04.04

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP03_04 = self._skip_SLP03 \
                           or self._config.src2src.SLP03._04.excluded

    # end def task_SLP03_04

    # ==========================================================================
    def task_SLP03_04_PREPROCESS(self):
        '''
        SC04.03 --> preprocessor --> SC04.04

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_04):
            return
        # end if

        # input and output folders
        include_folder = self._folders['SPLIT_C']['out'] + self._folders['SLP03']['suffix']
        input_folder = self._folders['SLP03']['out'] + '.03' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + '.04' + self._folders['SLP03']['suffix']

        # SC04.03/*.c --> SC04.04/*.c.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.c')
        dst = join(self._output, output_folder)

        tool = Preprocessor(program = self._config.tools.frontend,
                            options = self._config.src2bin.options
                                    + self._config.src2bin.PREPROCESS.options
                                    + ['-I', join(self._output, include_folder),
                                       '-D', 'ASPIRE_AID=%s' % (self._aid,)],
                            outputs = (dst, '.i'))

        yield tool.tasks(src,
                         header_files=[join(self._output, input_folder, '*.h'), ])

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_04_PREPROCESS', input_folder, output_folder)
    # end def task_SLP03_04_PREPROCESS

    # ==========================================================================
    def task_SLP03_05(self):
        '''
        SC04.04 --> WBC source rewriting Tool --> SC04

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP03_05 = self._skip_SLP03 \
                           or self._config.src2src.SLP03._05.excluded

    # end def task_SLP03_05

    # ==========================================================================
    def task_SLP03_05_CONVERT(self):
        '''
        SC04.04 --> Convert Pragmas --> SC04.05

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_05):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP03']['out'] + '.04' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + '.05' + self._folders['SLP03']['suffix']

        # SC04.04/*.i --> SC04.05/*.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')

        dst = join(self._output, output_folder)

        tool = WbcPragmaConverter(program = self._config.tools.convert_pragmas,
                                  outputs = (dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_05_CONVERT', input_folder, output_folder)
    # end def task_SLP03_05_CONVERT

    # ==========================================================================
    def task_SLP03_05_REWRITE(self):
        '''
        SC04.05 --> Rewrite --> SC04.06

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_05):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP03']['out'] + '.05' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + '.06' + self._folders['SLP03']['suffix']

        # SC04.05/*.i --> SC04.06/*.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')

        dst = [join(self._output, output_folder),
                join(self._output, output_folder, 'log')]

        tool = WbcSourceRewriter(program = self._config.tools.wbc,
                                 options = self._config.src2src.SLP03._05.options,
                                 outputs = [(path, '') for path in dst])
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_05_REWRITE', input_folder, output_folder)
    # end def task_SLP03_05_REWRITE

    # ==========================================================================
    def task_SLP03_05_REVERSE(self):
        '''
        SC04.06 --> Reverse Pragmas --> SC04

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP03_05):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP03']['out'] + '.06' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + self._folders['SLP03']['suffix']

        # SC04.06/*.i --> SC04/*.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')

        dst = join(self._output, output_folder)

        tool = WbcPragmaConverterReverse(program = self._config.tools.convert_pragmas,
                                         outputs = (dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP03_05_REVERSE', input_folder, output_folder)
    # end def task_SLP03_05_REVERSE

    def task_SLP03_06_RENEWABILITY(self):
        '''
        SLC03.02 --> Generate renewability script --> SC04_R/renew.sh

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP03_06 = self._skip_SLP03 \
                           or not self._config.src2src.SLP03.renewability_script

        if (self._skip_SLP03_06):
            return
        # end if

        # input and output folders
        include_folder = self._folders['SPLIT_C']['out'] + self._folders['SLP03']['suffix']
        input_folder = self._folders['SLP03']['intermediate'] + '.02' + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP03']['out'] + '_R' + self._folders['SLP03']['suffix']

        # SLC03.02/*.xml --> SC04_R/renew.sh
        # ----------------------------------------------------------------------

        src = join(self._output, input_folder, '*.xml')
        dst = join(self._output, output_folder)

        wbta_tool = self._config.tools.wbta
        pre_opts = self._config.src2bin.options \
                            + self._config.src2bin.PREPROCESS.options \
                            + ['-I', join(self._output, include_folder),
                               '-D', 'ASPIRE_AID=%s' % (self._aid,)]
        compile_opts = self._config.src2bin.options \
                            + self._config.src2bin.PREPROCESS.options \
                            + ['-D', 'ASPIRE_AID=%s' % (self._aid,)] \
                            + self._config.src2bin.COMPILE.options \
                            + self._config.src2bin.COMPILE.options_c \
                            + ['-g',
                               '-mfloat-abi=softfp',
                               '-msoft-float',
                               '-mfpu=neon']
        frontend = self._config.tools.frontend

        tool = WbcRenewabilityGenerator(outputs=(dst, ''))
        yield tool.tasks(src,
                         wbta_tool=wbta_tool,
                         frontend=frontend,
                         pre_opts=pre_opts,
                         compile_opts=compile_opts,
                         json_path=dirname(self._json),
                         patch_tool=self._config.tools.code_mobility
                         )
        # ----------------------------------------------------------------------
        self._updateDot('SLP03_06_RENEWABILITY', input_folder, output_folder)
    # end def task_SLP03_06_RENEWABILITY

    # ==========================================================================
    def task_SLP02(self):
        '''
        SC04 --> preprocessor --> SC05

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP02 = self._config.src2src.excluded \
                        or self._config.src2src.SLP02.excluded

    # end def task_SLP02

    # ==========================================================================
    def task_SLP02_PREPROCESS(self):
        '''
        SC04 --> preprocess --> SC05

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP03']['out'] + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP02']['out'] + self._folders['SLP02']['suffix']

        # SC04/*.c --> SC05/*.c.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.c')

        dst = join(self._output, output_folder)

        # C standard
        c_standard = "c99"
        if self._config.src2bin.PREPROCESS.c_standard:
            c_standard = self._config.src2bin.PREPROCESS.c_standard

        tool = Preprocessor(program = self._config.tools.frontend,
                            options = self._config.src2bin.options
                                    + ['-std=%s' % (c_standard)]
                                    + self._config.src2bin.PREPROCESS.options
                                    + ['-D', 'ASPIRE_AID=%s' % (self._aid,)],
                            outputs = (dst, '.i'))

        yield tool.tasks(src,
                         header_files=[join(self._output, input_folder, '*.h'), ])

        # ----------------------------------------------------------------------
        self._updateDot('SLP02_PREPROCESS', input_folder, output_folder)
    # end def task_SLP02_PREPROCESS

    # ==========================================================================
    def task_SLP02_COPY(self):
        '''
        SC04 --> preprocessed --> SC05

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP03']['out'] + self._folders['SLP03']['suffix']
        output_folder = self._folders['SLP02']['out'] + self._folders['SLP02']['suffix']

        # With SLP03, some files are already preprocessed
        # /!\ DO NOT preprocess them again
        #
        # SC04/*.c.i --> SC05/*.c.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')

        dst = join(self._output, output_folder)

        tool = Copier(outputs = (dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP02_COPY', input_folder, output_folder)
    # end def task_SLP02_COPY

    # ==========================================================================
    def task_SLP05(self):
        '''
        SC05 --> data hiding --> SC06

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP05 = self._config.src2src.excluded
        if (self._skip_SLP05):
            return
        # end if

        self._skip_SLP05 = self._config.src2src.SLP05.excluded

        # input and output folders
        input_folder = self._folders['SLP02']['out'] + self._folders['SLP02']['suffix']
        output_folder = self._folders['SLP05']['out'] + self._folders['SLP05']['suffix']

        # SC05 --> Traverse --> SC06
        # ----------------------------------------------------------------------
        if (self._config.src2src.SLP05.traverse
            or (self._config.src2src.SLP05.excluded and not self._config.src2src.SLP02.excluded)):

            self._skip_SLP05 = True

            src  = join(self._output, input_folder, '*.i')

            dst  = join(self._output, output_folder)

            tool = Copier(outputs = (dst, ''))

            yield tool.tasks(src)

            # ------------------------------------------------------------------
            self._updateDot('SLP05_TRAVERSE', input_folder, output_folder)
        # end if

    # end def task_SLP05

    def task_SLP05_cache(self):
        '''
        SC05 --> Cache a copy with the new suffix --> SC05

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP05
            or not self._caching):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP02']['out'] + self._folders['SLP02']['suffix']
        output_folder = self._folders['SLP02']['out'] + self._folders['SLP05']['suffix']

        # Return of no caching is required
        if(input_folder == output_folder):
            return

        # Copy source files
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP05_cache', input_folder, output_folder)
    # end def task_SLP05_cache

    # ==========================================================================
    def task_SLP05_annotate(self):
        '''
        SC05 --> Replace security requirement annotations (see D5.01) with some "concrete annotations" --> SC05

        @return (Task)
        '''

        external_annotations = self._config.src2src.SLP01.external_annotations
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP05
            or not external_annotations
            or not isfile(external_annotations)):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP02']['out'] + self._folders['SLP05']['suffix']
        output_folder = input_folder


        # Get source code
        # ----------------------------------------------------------------------
        src = external_annotations
        dst = join(self._output, output_folder, '.annotated')

        tool = AnnotationRewriter(outputs=(dst, ''))
        yield tool.tasks(src,
                        filter=self._annotations_list['SLP05'],
                        keep_placeholders=False,  # TXL based tools do not support multiple protections in a single annotation
                        replace_all=False,
                        preprocessed=True,)

        # ------------------------------------------------------------------
        self._updateDot('SLP05_annotate', input_folder, output_folder)
    # end def task_SLP05_annotate

    # ==========================================================================
    def task_SLP05_01(self):
        '''
        SC05 --> source code analysis --> D05.01

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP05_01 = self._skip_SLP05 \
                           or self._config.src2src.SLP05._01.excluded

    # end def task_SLP05_01

    # ==========================================================================
    def task_SLP05_02(self):
        '''
        SC05 + D05.01 --> data obfuscation --> SC06

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP05_02 = self._skip_SLP05 \
                           or self._config.src2src.SLP05._02.excluded

    # end def task_SLP05_02

    # ==========================================================================
    def task_SLP05_02_OBFUSCATE(self):
        '''
        SC05 + D05.01 --> data obfuscation --> SC05

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP05_02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP02']['out'] + self._folders['SLP05']['suffix']
        output_folder = input_folder


        # DataObfuscator generates output in current directory...
        # SC05/*.i --> SC05/*.i.obf
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')

        dst = [join(self._output, output_folder),
                join(self._output, output_folder, 'log')]

        tool = DataObfuscator(program = self._config.tools.data_obfuscate,
                              options = self._config.src2src.SLP05._02.options,
                              outputs = [(path, '.obf') for path in dst])

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP05_02_OBFUSCATE', input_folder, output_folder)
    # end def task_SLP05_02_OBFUSCATE

    # ==========================================================================
    def task_SLP05_02_COPY(self):
        '''
        SC05 --> copy/rename --> SC06

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP05_02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP02']['out'] + self._folders['SLP05']['suffix']
        output_folder = self._folders['SLP05']['out'] + self._folders['SLP05']['suffix']

        # ... then copy result in output dir
        # SC05/*.i.obf --> SC06/*.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i.obf')

        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))

        yield tool.tasks(src,
                         pattern=r'\.obf$',
                         replace='')

        # ----------------------------------------------------------------------
        self._updateDot('SLP05_02_COPY', input_folder, output_folder)
    # end def task_SLP05_02_COPY

    # ==========================================================================
    def task_SLP05_02_PREPROCESS(self):
        '''
        SC05 --> preprocess generated files --> SC06

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP05_02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP02']['out'] + self._folders['SLP05']['suffix']
        output_folder = self._folders['SLP05']['out'] + self._folders['SLP05']['suffix']

        # ... preprocess generated files
        # SC05/*_aspire_do_oc.i.obf --> SC06/*.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.obfs.c')

        dst = join(self._output, output_folder)

        tool = Preprocessor(program=self._config.tools.frontend,
                            options=self._config.src2bin.options
                                    + self._config.src2bin.PREPROCESS.options
                                    + ['-D', 'ASPIRE_AID=%s' % (self._aid,)]
                                    + ['-x', 'c'],
                            outputs=(dst, '.i'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP05_02_PREPROCESS', input_folder, output_folder)
    # end def task_SLP05_02_PREPROCESS

    # ==========================================================================
    def task_SLP06(self):
        '''
        SC06 --> client server code splitting --> SC07

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP06 = self._config.src2src.excluded
        if (self._skip_SLP06):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP05']['out'] + self._folders['SLP05']['suffix']
        output_folder = self._folders['SLP06']['out'] + self._folders['SLP06']['suffix']

        self._skip_SLP06 = self._config.src2src.SLP06.excluded

        # SC06 --> Traverse --> SC07
        # ----------------------------------------------------------------------
        if (self._config.src2src.SLP06.traverse
            or (self._config.src2src.SLP06.excluded and not self._config.src2src.SLP05.excluded)):
            self._skip_SLP06 = True

            src = join(self._output, input_folder, '*.i')

            dst = join(self._output, output_folder)

            tool = Copier(outputs = (dst, ''))

            yield tool.tasks(src)

            # ------------------------------------------------------------------
            self._updateDot('SLP06_TRAVERSE', input_folder, output_folder)
        # end if

    # end def task_SLP06

    # ==========================================================================
    def task_SLP06_cache(self):
        '''
        SC06 --> Cache a copy with the new suffix --> SC06

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP06
            or not self._caching):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP05']['out'] + self._folders['SLP05']['suffix']
        output_folder = self._folders['SLP05']['out'] + self._folders['SLP06']['suffix']

        # Return of no caching is required
        if(input_folder == output_folder):
            return

        # Copy source files
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP06_cache', input_folder, output_folder)
    # end def task_SLP06_cache

    # ==========================================================================
    def task_SLP06_annotate(self):
        '''
        SC06 --> Replace security requirement annotations (see D5.01) with some "concrete annotations" --> SC06

        @return (Task)
        '''

        external_annotations = self._config.src2src.SLP01.external_annotations
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP06
            or not external_annotations
            or not isfile(external_annotations)):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP05']['out'] + self._folders['SLP06']['suffix']
        output_folder = input_folder

        # Get source code
        # ----------------------------------------------------------------------
        src = external_annotations
        dst = join(self._output, output_folder, '.annotated')

        tool = AnnotationRewriter(outputs=(dst, ''))
        yield tool.tasks(src,
                        filter=self._annotations_list['SLP06'],
                        keep_placeholders=True,
                        replace_all=False,
                        preprocessed=True,)

        # ------------------------------------------------------------------
        self._updateDot('SLP06_annotate', input_folder, output_folder)
    # end def task_SLP06_annotate

    # ==========================================================================
    def task_SLP06_01_PROCESS(self):
        '''
        SC06 --> Processing of the input (preprocessed) file to analyse --> SC06.01

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP06_01 = self._skip_SLP06 \
                           or self._config.src2src.SLP06._01.excluded

        if (self._skip_SLP06_01):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP05']['out'] + self._folders['SLP06']['suffix']
        output_folder = self._folders['SLP05']['out'] + '.01' + self._folders['SLP06']['suffix']

        # SC06/*.i --> SC06.01/*.i
        #          --> SC06.01/facts/*.i.*
        # ----------------------------------------------------------------------
        facts = join(self._output, output_folder, 'facts')
        src = join(self._output, input_folder, '*.i')
        dst = [join(self._output, output_folder),
                facts]



        tool = SplitterProcess(program = join(self._config.tools.client_server_splitter,'process.sh'),
                               options=self._config.src2src.SLP06._01.options,
                                  outputs = [(path, '') for path in dst])

        yield tool.tasks(src,fact_folder=facts)

        # ----------------------------------------------------------------------
        self._updateDot('SLP06_01_PROCESS', input_folder, output_folder)
    # end def tastk_SLP06_01_PROCESS

    def task_SLP06_02_CHECK(self):
        '''
        Check to continue code splitting
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP06_02 = self._skip_SLP06 \
                            or self._config.src2src.SLP06._02.excluded

        if (self._skip_SLP06_02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP05']['out'] + self._folders['SLP06']['suffix']
        facts_folder = self._folders['SLP05']['out'] + '.01' + self._folders['SLP06']['suffix']
        output_folder = self._folders['SLP06']['out'] + self._folders['SLP06']['suffix']

        # Check facts
        # ----------------------------------------------------------------------
        facts = join(self._output, facts_folder, 'facts')

        if(isdir(facts) and not listdir(facts)):
            self._skip_SLP06 = True

            src = join(self._output, input_folder, '*.i')

            dst = join(self._output, output_folder)

            tool = Copier(outputs = (dst, ''))

            yield tool.tasks(src)

            self._updateDot('SLP06_02_CHECK', input_folder, output_folder)

        # end if
    # def task_SLP06_02_CHECK

    # ==========================================================================
    @monoprocess
    def task_SLP06_02_CSURF(self):
        '''
        SC06.01 --> Create CodeSurfer project --> SC06.01/csurf-project
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP06_02 = self._skip_SLP06 \
                           or self._config.src2src.SLP06._02.excluded

        if (self._skip_SLP06_02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP05']['out'] + '.01' + self._folders['SLP06']['suffix']
        output_folder = input_folder

        # SC06.01/*.i --> SC06.01/csurf-project
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder, 'csurf-project')

        tool = CodeSurferInitializer(program = self._config.tools.csurf,
                                     outputs = (dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP06_02_CSURF', input_folder, output_folder)
    # end def task_SLP06_02_CSURF

    # ==========================================================================
    def task_SLP06_03_PREPROCESS_CLIENT(self):
        '''
        Library --> preprocess accl-message-wrapper.c --> SC07
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP06_03 = self._skip_SLP06 \
                           or self._config.src2src.SLP06._03.excluded


        if (self._skip_SLP06_03):
            return
        # end if

        # input and output folders
        output_folder = self._folders['SLP06']['out'] + self._folders['SLP06']['suffix']

        # client_server_splitter/libraries/client/accl-message-wrapper.c --> SC07
        # ----------------------------------------------------------------------
        src  = join(self._config.tools.client_server_splitter,
                    'libraries', 'client', 'accl-message-wrapper.c')

        if(not isfile(src)):
            print 'WARNING: \'%s\' not found' % src
            return

        dst = join(self._output, output_folder)

        tool = Preprocessor(program = self._config.tools.frontend,
                            options = self._config.src2bin.options
                            + self._config.src2bin.PREPROCESS.options
                            + ['-I', self.accl_headers]
                            + ['-I', self.curl_headers]
                            + ['-I', self.openssl_headers]
                            + ['-I', self.websocket_headers]
                            + ['-D', 'ASPIRE_AID=%s' % (self._aid,)],
                            outputs = (dst, '.i'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP06_03_PREPROCESS_CLIENT', 'libraries/client', output_folder)
    # end def task_SLP06_03_PREPROCESS

    # ==========================================================================
    def task_SLP06_03_TRANSFORMATION(self):
        '''
        SC06.02 --> Analysis, generation of client, generation of server-side code --> SC07 (client), SCS01 (server)

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP06_03):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP05']['out'] + '.01' + self._folders['SLP06']['suffix']
        output_folder = self._folders['SLP06']['out'] + self._folders['SLP06']['suffix']
        server_folder = self._folders['SLP06']['server'] + self._folders['SLP06']['suffix']


        # SC06.01/*.i    --> SC07  (Client)
        #                --> SCS01 (Server
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')
        dst = [join(self._output, output_folder),  # Client Code
               join(self._output, server_folder),  # Server Code
               join(self._output, output_folder, 'log')]  # Logs

        tool = SplitterCodeTransformation(program = join(self._config.tools.client_server_splitter,'code_transformation.sh'),
                                          outputs = [(path, '') for path in dst])
        yield tool.tasks(src, fact_folder   = join(self._output, input_folder, 'facts'),
                         csurf_folder       = join(self._output, input_folder, 'csurf-project'),
                         client_folder      = join(self._output, output_folder),
                         server_folder      = join(self._output, server_folder),
                         log_folder         = join(self._output, output_folder, 'log')
                         )
        # ----------------------------------------------------------------------
        self._updateDot('SLP06_03_TRANSFORMATION', input_folder, ['SC07', server_folder])

    # end def task_SLP06_03_TRANSFORMATION


    # ==========================================================================
    def task_SLP08_CG(self):
        '''SC07 -->  Codeguard --> SC08
        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP08 = self._config.src2src.excluded \
                        or self._config.src2src.SLP08.excluded

        if (self._skip_SLP08):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP06']['out'] + self._folders['SLP06']['suffix']
        output_folder = self._folders['SLP08']['out'] + self._folders['SLP08']['suffix']

        src  = join(self._output, input_folder, '*.i')

        dst  = join(self._output, output_folder)

        if(self._config.src2src.SLP08.traverse):
            #
            # SC07/*.{i,cpp,h} --> Traverse --> SC08/*.{i,cpp,h}
            # ----------------------------------------------------------------------
            self._skip_SLP08 = True

            tool = Copier(outputs = (dst,''))

            yield tool.tasks(src)

            # ----------------------------------------------------------------------
            self._updateDot('SLP08_CG_TRAVERSE', input_folder, output_folder)
    # end def task_SLP08_CG

    # ==========================================================================
    def task_SLP08_cache(self):
        '''
        SC07 --> Cache a copy with the new suffix --> SC07

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP08
            or not self._caching):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP06']['out'] + self._folders['SLP06']['suffix']
        output_folder = self._folders['SLP06']['out'] + self._folders['SLP08']['suffix']

        # Return of no caching is required
        if(input_folder == output_folder):
            return

        # Copy source files
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP08_cache', input_folder, output_folder)
    # end def task_SLP08_cache

    # ==========================================================================
    def task_SLP08_annotate(self):
        '''
        SC07 --> Replace security requirement annotations (see D5.01) with some "concrete annotations" --> SC07

        @return (Task)
        '''

        external_annotations = self._config.src2src.SLP01.external_annotations
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP08
            or not external_annotations
            or not isfile(external_annotations)):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP06']['out'] + self._folders['SLP08']['suffix']
        output_folder = input_folder

        # Get source code
        # ----------------------------------------------------------------------
        src = external_annotations
        dst = join(self._output, input_folder, '.annotated')

        tool = AnnotationRewriter(outputs=(dst, ''))
        yield tool.tasks(src,
                        filter=self._annotations_list['SLP08'],
                        keep_placeholders=True,
                        replace_all=False,
                        preprocessed=True,)

        # ------------------------------------------------------------------
        self._updateDot('SLP08_annotate', input_folder, output_folder)
    # end def task_SLP08_annotate

    # ==========================================================================
    def task_SLP08_01_CG(self):
        '''SC07 -->  Codeguard --> SC08
        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP08):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP06']['out'] + self._folders['SLP08']['suffix']
        output_folder = self._folders['SLP08']['out'] + self._folders['SLP08']['suffix']

        #
        # SC07/*.{i,cpp,h} --> Codeguard --> SC08/*.{i,cpp,h}
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')

        dst = join(self._output, output_folder)

        tool = CodeGuard(program = self._config.tools.codeguard,
                         options = self._config.src2src.SLP08.options +
                         ['-a', self._aid],
                         outputs = (dst,''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('task_SLP08_01', input_folder, output_folder)
    # end def task_SLP08_01

    # ==========================================================================
    def task_SLP08_02_PREPROCESS(self):
        '''
        SC08 --> preprocess generated c files --> SC08

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP08):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP08']['out'] + self._folders['SLP08']['suffix']
        output_folder = input_folder

        # SC08/*.c --> SC08/*.c.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.c')

        dst = join(self._output, output_folder)

        tool = Preprocessor(program = self._config.tools.frontend,
                            options = self._config.src2bin.options
                                    + self._config.src2bin.PREPROCESS.options
                                    + ['-D', 'ASPIRE_AID=%s' % (self._aid,)],
                            outputs = (dst, '.i'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP08_02_PREPROCESS', input_folder, output_folder)
    # end def task_SLP08_02_PREPROCESS

    # ==========================================================================
    def task_SLP09_AC(self):
        '''
        SC08 --> anti-cloning transformations --> SC09

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP09 = self._config.src2src.excluded \
                            or self._config.src2src.SLP09.excluded
        if (self._skip_SLP09):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP08']['out'] + self._folders['SLP08']['suffix']
        output_folder = self._folders['SLP09']['out'] + self._folders['SLP09']['suffix']


        src = join(self._output, input_folder, '*.i')

        dst = join(self._output, output_folder)

        if(self._config.src2src.SLP09.traverse):
            #
            # SC08/*.i --> Traverse --> SC09/*.i
            # ----------------------------------------------------------------------
            self._skip_SLP09 = True

            tool = Copier(outputs = (dst,''))

            yield tool.tasks(src)

            # ----------------------------------------------------------------------
            self._updateDot('SLP09_AC_TRAVERSE', input_folder, output_folder)
    # end def task_SLP09_AC

    # ==========================================================================
    def task_SLP09_cache(self):
        '''
        SC08 --> Cache a copy with the new suffix --> SC08

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP09
            or not self._caching):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP08']['out'] + self._folders['SLP08']['suffix']
        output_folder = self._folders['SLP08']['out'] + self._folders['SLP09']['suffix']

        # Return of no caching is required
        if(input_folder == output_folder):
            return

        # Copy source files
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP09_cache', input_folder, output_folder)
    # end def task_SLP09_cache

    # ==========================================================================
    def task_SLP09_annotate(self):
        '''
        SC08 --> Replace security requirement annotations (see D5.01) with some "concrete annotations" --> SC08

        @return (Task)
        '''

        external_annotations = self._config.src2src.SLP01.external_annotations
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP09
            or not external_annotations
            or not isfile(external_annotations)):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP08']['out'] + self._folders['SLP09']['suffix']
        output_folder = input_folder

        # Get source code
        # ----------------------------------------------------------------------
        src = external_annotations
        dst = join(self._output, output_folder, '.annotated')

        tool = AnnotationRewriter(outputs=(dst, ''))
        yield tool.tasks(src,
                        filter=self._annotations_list['SLP09'],
                        keep_placeholders=True,
                        replace_all=False,
                        preprocessed=True,)

        # ------------------------------------------------------------------
        self._updateDot('SLP09_annotate', input_folder, output_folder)
    # end def task_SLP09_annotate

    # ==========================================================================
    def task_SLP09_01_AC(self):
        '''
        SC08 --> anti-cloning transformations --> SC09

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP09):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP08']['out'] + self._folders['SLP09']['suffix']
        output_folder = self._folders['SLP09']['out'] + self._folders['SLP09']['suffix']

        # SC08/*.c --> SC09/*.c.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')

        dst = join(self._output, output_folder)

        tool = AntiCloning(program = self._config.tools.anti_cloning,
                            options = self._config.src2src.SLP09.options,
                                    #+ ['-a', self._aid],
                            outputs = (dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP09_01_AC', input_folder, output_folder)
    # end def task_SLP09_01_AC

    # ==========================================================================
    def task_SLP09_02_PREPROCESS(self):
        '''
        preprocess anti_cloning sources --> SC09

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP09):
            return
        # end if

        # input and output folders
        output_folder = self._folders['SLP09']['out'] + self._folders['SLP09']['suffix']

        # anti_cloning sources --> SC09/*.c.i
        # ----------------------------------------------------------------------
        src  = join('/opt/anti_cloning/src/','*.c')

        dst = join(self._output, output_folder)

        tool = Preprocessor(program = self._config.tools.frontend,
                            options = self._config.src2bin.options
                                    + self._config.src2bin.PREPROCESS.options
                                    + ['-D', 'ASPIRE_AID=%s' % (self._aid,)]
                                    + ['-I', self.accl_headers]
                                    + ['-I', self.websocket_headers],
                            outputs = (dst, '.i'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP09_02_PREPROCESS', '/opt/anti_cloning/src/', output_folder)
    # end def task_SLP09_02_PREPROCESS

    # ==========================================================================
    def task_SLP10(self):
        '''
        SC09 --> reaction unit --> SC10

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP10 = self._config.src2src.excluded \
                           or self._config.src2src.SLP10.excluded
        if (self._skip_SLP10):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP09']['out'] + self._folders['SLP09']['suffix']
        output_folder = self._folders['SLP10']['out'] + self._folders['SLP10']['suffix']

        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        if (self._config.src2src.SLP10.traverse):
            #
            # SC09/*.i --> Traverse --> SC10/*.i
            # ----------------------------------------------------------------------
            self._skip_SLP10 = True
            tool = Copier(outputs=(dst, ''))
            yield tool.tasks(src)

            # ----------------------------------------------------------------------
            self._updateDot('SLP10_TRAVERSE', input_folder, output_folder)


    # end def task_SLP10

    # ==========================================================================
    def task_SLP10_cache(self):
        '''
        SC09 --> Cache a copy with the new suffix --> SC09

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP10
            or not self._caching):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP09']['out'] + self._folders['SLP09']['suffix']
        output_folder = self._folders['SLP09']['out'] + self._folders['SLP10']['suffix']

        # Return of no caching is required
        if(input_folder == output_folder):
            return

        # Copy source files
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP10_cache', input_folder, output_folder)
    # end def task_SLP09_cache

    # ==========================================================================
    def task_SLP10_annotate(self):
        '''
        SC09 --> Replace security requirement annotations (see D5.01) with some "concrete annotations" --> SC09

        @return (Task)
        '''

        external_annotations = self._config.src2src.SLP01.external_annotations
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP10
            or not external_annotations
            or not isfile(external_annotations)):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP09']['out'] + self._folders['SLP10']['suffix']
        output_folder = input_folder

        # Get source code
        # ----------------------------------------------------------------------
        src = external_annotations
        dst = join(self._output, output_folder, '.annotated')

        tool = AnnotationRewriter(outputs=(dst, ''))
        yield tool.tasks(src,
                        filter=self._annotations_list['SLP10'],
                        keep_placeholders=True,
                        replace_all=False,
                        preprocessed=True,)

        # ------------------------------------------------------------------
        self._updateDot('SLP10_annotate', input_folder, output_folder)
    # end def task_SLP10_annotate

    # ==========================================================================
    def task_SLP10_01_REACTIONUNIT(self):
        '''
        SC09 --> reaction unit --> SC10

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP10):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP09']['out'] + self._folders['SLP10']['suffix']
        output_folder = self._folders['SLP10']['out'] + self._folders['SLP10']['suffix']

        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        # SC09/*.i --> SC10/*.i
        # ----------------------------------------------------------------------
        tool = ReactionUnit(program=self._config.tools.reaction_unit,
                            options=self._config.src2src.SLP10.options,
                            outputs=(dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP10_01_REACTIONUNIT', input_folder, output_folder)
        # end if
    # end task_SLP10_01_REACTIONUNIT


    # ==========================================================================
    def task_SLP10_02_PREPROCESS(self):
        '''
        preprocess reaction_unit sources --> SC10

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP10):
            return
        # end if

        # input and output folders
        output_folder = self._folders['SLP10']['out'] + self._folders['SLP10']['suffix']

        # reaction_unit sources --> SC10/*.c.i
        # ----------------------------------------------------------------------
        src = join('/opt/reaction_unit/src/', '*.c')
        dst = join(self._output, output_folder)

        tool = Preprocessor(program=self._config.tools.frontend,
                            options=self._config.src2bin.options
                                    + self._config.src2bin.PREPROCESS.options
                                    + ['-D', 'ASPIRE_AID=%s' % (self._aid,)]
                                    + ['-I', self.accl_headers]
                                    + ['-I', self.websocket_headers]
                                    + ['-D', '__need_timespec'],
                            outputs=(dst, '.i'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP10_02_PREPROCESS', '/opt/reaction_unit/src/', output_folder)

    # end def task_SLP10_02_PREPROCESS

    # ==========================================================================
    def task_SLP11(self):
        '''
        SC10 --> diversified crypto library --> SC11

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP11 = self._config.src2src.excluded \
                           or self._config.src2src.SLP11.excluded
        if (self._skip_SLP11):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP10']['out'] + self._folders['SLP10']['suffix']
        output_folder = self._folders['SLP11']['out'] + self._folders['SLP11']['suffix']

        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        if (self._config.src2src.SLP11.traverse):
            #
            # SC10/*.i --> Traverse --> SC11/*.i
            # ----------------------------------------------------------------------
            self._skip_SLP11 = True
            tool = Copier(outputs=(dst, ''))
            yield tool.tasks(src)

            # ----------------------------------------------------------------------
            self._updateDot('SLP11_TRAVERSE', input_folder, output_folder)
        # end if

    # end def task_SLP11

    # ==========================================================================
    def task_SLP11_cache(self):
        '''
        SC10 --> Cache a copy with the new suffix --> SC10

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP11
            or not self._caching):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP10']['out'] + self._folders['SLP10']['suffix']
        output_folder = self._folders['SLP10']['out'] + self._folders['SLP11']['suffix']

        # Return of no caching is required
        if(input_folder == output_folder):
            return

        # Copy source files
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP11_cache', input_folder, output_folder)
    # end def task_SLP11_cache

    # ==========================================================================
    def task_SLP11_annotate(self):
        '''
        SC10 --> Replace security requirement annotations (see D5.01) with some "concrete annotations" --> SC10

        @return (Task)
        '''

        external_annotations = self._config.src2src.SLP01.external_annotations
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP11
            or not external_annotations
            or not isfile(external_annotations)):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP10']['out'] + self._folders['SLP11']['suffix']
        output_folder = input_folder

        # Get source code
        # ----------------------------------------------------------------------
        src = external_annotations
        dst = join(self._output, output_folder, '.annotated')

        tool = AnnotationRewriter(outputs=(dst, ''))
        yield tool.tasks(src,
                        filter=self._annotations_list['SLP11'],
                        keep_placeholders=True,
                        replace_all=False,
                        preprocessed=True,)

        # ------------------------------------------------------------------
        self._updateDot('SLP11_annotate', input_folder, output_folder)
    # end def task_SLP11_annotate

    # ==========================================================================
    def task_SLP11_01_DCL(self):
        '''
        SC10 --> diversified crypto library --> SC11

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP11):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP10']['out'] + self._folders['SLP11']['suffix']
        output_folder = self._folders['SLP11']['out'] + self._folders['SLP11']['suffix']

        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        # SC10/*.i --> SC11/*.i
        # ----------------------------------------------------------------------
        tool = DiversifiedCryptoLibrary(program=self._config.tools.dcl + '/script/replace.sh',
                                        options=self._config.src2src.SLP11.options,
                                        outputs=(dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP11', input_folder, output_folder)

    #end task_SLP11_01_DCL

    # ==========================================================================
    def task_SLP11_02_PREPROCESS(self):
        '''
        preprocess dcl sources --> SC11

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP11):
            return
        # end if

        # input and output folders
        output_folder = self._folders['SLP11']['out'] + self._folders['SLP11']['suffix']

        # dcl sources --> SC11/*.c.i
        # ----------------------------------------------------------------------
        src = join(self._config.tools.dcl + '/wrapper/', '*.c')
        dst = join(self._output, output_folder)

        tool = Preprocessor(program=self._config.tools.frontend,
                            options=self._config.src2bin.options
                                    + self._config.src2bin.PREPROCESS.options
                                    + ['-D', 'ASPIRE_AID=%s' % (self._aid,)],
                            outputs=(dst, '.i'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP11_02_PREPROCESS', self._config.tools.dcl + '/wrapper/', output_folder)
    # end def task_SLP11_02_PREPROCESS

    # ==========================================================================
    def task_SLP11_03_COPY(self):
        '''
        Library files --> DCL

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP11):
            return
        # end if

        # input and output folders
        output_folder = self._folders['SLP11']['out'] + self._folders['SLP11']['suffix']

        # Library - assets files
        # ----------------------------------------------------------------------
        src = join(self._config.tools.dcl + '/dist/assets/', '*.txt')
        dst = join(self._output, output_folder, 'dist/assets/')
        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        src = join(self._config.tools.dcl + '/dist/assets/armeabi-v7a', '*')
        dst = join(self._output, output_folder, 'dist/assets/armeabi-v7a')
        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # Library - libs files
        # ----------------------------------------------------------------------
        src = join(self._config.tools.dcl + '/dist/libs/armeabi-v7a', '*')
        dst = join(self._output, output_folder, 'dist/libs/armeabi-v7a')
        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP11_03_COPY', self._config.tools.dcl + '/dist', output_folder + '/dist')
    # end def task_SLP11_03_COPY

    # ==========================================================================
    def task_SLP11_04_GENKEY(self):
        '''
        Generate key (perso data) for DCL protection

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP11):
            return
        # end if

        # Because task 'clean' still executing this task,
        # so this checking will help to skip the subcall
        #if (not isdir(self._output)):
#            return

        # input and output folders
        output_folder = self._folders['SLP11']['out'] + self._folders['SLP11']['suffix']

        if (isfile('dclsecretkey.bin')):
            admin_cmd = list(
                ['java', '-jar',
                 self._config.tools.dcl + '/dist/tool/AdminCmdGenerator-1.1.jar',
                 'genAdminCmd',
                 '-commandID', '0x10015',
                 '-authorizingSD', '103A6BC4-4F5B-B087-9CDA-0E9DE465758F',
                 '-taorsdID', 'AABBCCDD-AABB-CCDD-EEFF-200000000001',
                 '-inputObjID', '1',
                 '-objType', '0xA0000010',
                 '-acf', '0x00000021',
                 '-inputSKObj', 'dclsecretkey.bin',
                 '-outputCmd', join(self._output, output_folder, 'dist/assets/armeabi-v7a/secretkey_aes.com')])
            # admin_cmd.extend(self._config.src2src.SLP11.options)
            call(admin_cmd)

            # remove temporary file
            remove('dclsecretkey.bin')
        # end if

        # ----------------------------------------------------------------------
        self._updateDot('SLP11_04_GENKEY', '.', join(self._output, 'SC11'))

    # end def task_SLP11_04_GENKEY

    # ==========================================================================
    def task_SLP12(self):
        '''
        SC11 --> control flow tagging --> SC12

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP12 = self._config.src2src.excluded \
                           or self._config.src2src.SLP12.excluded
        if (self._skip_SLP12):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP11']['out'] + self._folders['SLP11']['suffix']
        output_folder = self._folders['SLP12']['out'] + self._folders['SLP12']['suffix']

        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        if (self._config.src2src.SLP12.traverse):
            #
            # SC11/*.i --> Traverse --> SC12/*.i
            # ----------------------------------------------------------------------
            self._skip_SLP12 = True
            tool = Copier(outputs=(dst, ''))
            yield tool.tasks(src)

            # ----------------------------------------------------------------------
            self._updateDot('SLP12_TRAVERSE', input_folder, output_folder)

    # end def task_SLP12

    # ==========================================================================
    def task_SLP12_cache(self):
        '''
        SC11 --> Cache a copy with the new suffix --> SC11

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP12
            or not self._caching):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP11']['out'] + self._folders['SLP11']['suffix']
        output_folder = self._folders['SLP11']['out'] + self._folders['SLP12']['suffix']

        # Return if no caching is required
        if (input_folder == output_folder):
            return

        # Copy source files
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP12_cache', input_folder, output_folder)

    # end def task_SLP12_cache

    # ==========================================================================
    def task_SLP12_annotate(self):
        '''
        SC11 --> Replace security requirement annotations (see D5.01) with some "concrete annotations" --> SC11

        @return (Task)
        '''

        external_annotations = self._config.src2src.SLP01.external_annotations
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP12
            or not external_annotations
            or not isfile(external_annotations)):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP11']['out'] + self._folders['SLP12']['suffix']
        output_folder = input_folder

        # Get source code
        # ----------------------------------------------------------------------
        src = external_annotations
        dst = join(self._output, output_folder, '.annotated')

        tool = AnnotationRewriter(outputs=(dst, ''))
        yield tool.tasks(src,
                         filter=self._annotations_list['SLP12'],
                         keep_placeholders=True,
                         replace_all=False,
                         preprocessed=True, )

        # ------------------------------------------------------------------
        self._updateDot('SLP12_annotate', input_folder, output_folder)

    # end def task_SLP12_annotate

    # ==========================================================================
    def task_SLP12_01_CFT(self):
        '''
        SC11 --> control flow tagging --> SC12

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP12):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP11']['out'] + self._folders['SLP12']['suffix']
        output_folder = self._folders['SLP12']['out'] + self._folders['SLP12']['suffix']
        output_be_folder = self._folders['SLP12']['out_be'] + self._folders['SLP12']['suffix']

        src = join(self._output, input_folder, '*.i')
        dst = join(self._output, output_folder)
        dst_be = join(self._output, output_be_folder)

        dsts = [dst, dst_be, '']

        # SC11/*.i --> SC12/*.i
        # ----------------------------------------------------------------------
        tool = ControlFlowTagging(program=self._config.tools.cft,
                                  options=self._config.src2src.SLP12.options
                                    + ['-a', '%s' % (self._aid)]
                                    + ['-rv', '%s' % (dst_be)],
                                  outputs=[(dst, ''), (dst_be, '')])
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP12_01_CFT', input_folder, output_folder)

        # SC11/*.i --> SC12_BE/*.i
        # ----------------------------------------------------------------------
        #tool = ControlFlowTagging(program=self._config.tools.cft,
        #                          options=self._config.src2src.SLP12.options
        #                            + ['-a', '%s' % (self._aid)],
        #                          outputs=(dst_be, ''))
        #yield tool.tasks(src)
        # ----------------------------------------------------------------------
        #self._updateDot('SLP12_01_CFT', input_folder, output_folder, output_be_folder)

        # end if

    # end task_SLP12_01_CFT

    # ==========================================================================
    def task_SLP12_02_PREPROCESS(self):
        '''
        preprocess cft sources --> SC12

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP12):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP12']['out'] + self._folders['SLP12']['suffix']
        output_folder = input_folder

        # cft sources --> SC12/*.c.i
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.c')
        dst = join(self._output, output_folder)

        tool = Preprocessor(program=self._config.tools.frontend,
                            options=self._config.src2bin.options
                                    + self._config.src2bin.PREPROCESS.options
                                    + ['-D', 'ASPIRE_AID=%s' % (self._aid,)]
                                    + ['-I', self.accl_headers]
                                    + ['-I', self.websocket_headers],
                            outputs=(dst, '.i'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP12_02_PREPROCESS', input_folder, output_folder)

        # end def task_SLP12_02_PREPROCESS

    # ==========================================================================
    def task_SLP12_03_COMPILESO(self):
        '''
        preprocess cft sources --> SC12

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP12):
            return
        # end if

        # input and output folders
        # input_folder = self._folders['SLP12']['out_be'] + self._folders['SLP12']['suffix']
        output_folder = self._folders['SLP12']['out_be'] + self._folders['SLP12']['suffix']

        # cft sources --> SC10/*.c.i
        # ----------------------------------------------------------------------
        src = join(self._output, output_folder, '*.c')
        dst = join(self._output, output_folder)

        tool = CompilerSO(options=self._config.src2bin.options
                                    + self._config.src2bin.PREPROCESS.options
                                    + ['-I', self.accl_headers]
                                    + ['-I', self.websocket_headers],
                            outputs=(dst, self._aid + '.so'))



        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP12_02_PREPROCESS', output_folder, output_folder)

        # end def task_SLP12_02_PREPROCESS

    # ==========================================================================
    def task_SLP04(self):
        '''
        SC12 --> annotation extraction --> D01

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP04 = self._config.src2src.excluded \
                        or self._config.src2src.SLP04.excluded

    # end def task_SLP04

    # ==========================================================================
    def task_SLP04_cache(self):
        '''
        SC12 --> Cache a copy with the new suffix --> SC12

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP04
            or not self._caching):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP12']['out'] + self._folders['SLP12']['suffix']
        output_folder = self._folders['SLP12']['out'] + self._folders['SLP04']['suffix']

        # Return of no caching is required
        if(input_folder == output_folder):
            return

        # Copy source files
        # ----------------------------------------------------------------------
        src = [join(self._output, input_folder, '*.i'),
               join(self._output, input_folder, '*.h'),
               join(self._output, input_folder, '*.cpp'),
               join(self._output, input_folder, '*.hpp'),]
        dst = join(self._output, output_folder)

        tool = Copier(outputs=(dst, ''))
        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP04_cache', input_folder, output_folder)
    # end def task_SLP04_cache

    # ==========================================================================
    def task_SLP04_annotate(self):
        '''
        SC12 --> Replace security requirement annotations (see D5.01) with some "concrete annotations" --> SC09

        @return (Task)
        '''

        external_annotations = self._config.src2src.SLP01.external_annotations
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP04
            or not external_annotations
            or not isfile(external_annotations)):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP12']['out'] + self._folders['SLP04']['suffix']
        output_folder = input_folder

        # Get source code
        # ----------------------------------------------------------------------
        src = external_annotations
        dst = join(self._output, output_folder, '.annotated')

        tool = AnnotationRewriter(outputs=(dst, ''))
        yield tool.tasks(src,
                        filter=self._annotations_list['SLP07']
                                + self._annotations_list['BLP04'],
                        keep_placeholders=True,
                        replace_all=False,
                        preprocessed=True,)

        # ------------------------------------------------------------------
        self._updateDot('SLP04_annotate', input_folder, output_folder)
    # end def task_SLP04_annotate

    # ==========================================================================
    def task_SLP04_EXTRACT(self):
        '''
        SC12 --> annotations extraction --> D01

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP04):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP12']['out'] + self._folders['SLP04']['suffix']
        output_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']

        # SC07/<module>.i --> D01/<module>.i.json
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')

        dst = join(self._output, output_folder)

        tool = AnnotationExtractor(program = self._config.tools.read_annot,
                                   options = self._config.src2src.SLP04.options,
                                   outputs = (dst, '.json'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP04_EXTRACT', input_folder, output_folder)
    # end def task_SLP04_EXTRACT

    # ==========================================================================
    def task_SLP04_COPY(self):
        '''
        External annotations files --> D01

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP04):
            return
        # end if

        # input and output folders
        output_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']

        # External annotations files --> D01/<module>.i.json
        # ----------------------------------------------------------------------
        src  = self._config.src2src.SLP04.external

        dst = join(self._output, output_folder)

        tool = Copier(outputs = (dst, '.i.json'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SLP04_COPY', [dirname(external) for external in src], output_folder)
    # end def task_SLP04_COPY

    # ==========================================================================
    def task_SLP04_MERGE(self):
        '''
        D01 --> annotations merge --> D01

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP04):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']
        output_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']

        # Diablo requires only one annotations file
        #
        # D01/*.i.json --> D01/annotations.json
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i.json')

        dst = join(self._output, output_folder)

        tool = AnnotationMerger(outputs = (dst, '.json'))

        yield tool.tasks(src, join(dst, 'annotations.json'))

        # ----------------------------------------------------------------------
        self._updateDot('SLP04_MERGE', input_folder, output_folder)
    # end def task_SLP04_MERGE

    # ==========================================================================
    def task_SLP07_RA(self):
        '''
        D01 --> BC07

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_SLP07 = (self._config.src2src.excluded \
                        or self._config.src2src.SLP07.excluded)

        if (self._skip_SLP07):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']  # D01
        output_folder = self._folders['SLP07']['out'] + self._folders['SLP07']['suffix']  # BC07

        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, 'annotations.json')
        dst = join(self._output, output_folder)

        tool = AttestatorSelector(program=self._config.tools.attestator_selector,
                                  options=self._config.src2src.SLP07.options,
                                  outputs=(dst, ''))

        yield tool.tasks(src,
                         target=self._config.platform)

        # ----------------------------------------------------------------------
        self._updateDot('SLP07_RA', input_folder, output_folder)
    # end def task_SLP07_RA

    # ==========================================================================
    def task_SLP04_PARSE(self):
        '''
        D01/annotations.json -> self._binary_annotations

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_SLP04):
            return
        # end if

        # input and output folders
        annotations_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']

        self._binary_annotations = { 'anti_debugging'       : False,
                                     'barrier_slicing'      : isdir(join(self._output, 'SCS01')),
                                     'code_mobility'        : False,
                                     'remote_attestation'   : False,
                                     'invariant_monitoring' : False,
                                     'softvm'               : False,
                                     'anti_cloning'         : not self._skip_SLP09,  # Hack, annotations have been removed by the anti_cloning tool
                                     'call_stack_check'     : False,
                                     'obfuscations'         : False,
                                     'guarded_region'       : False,
                                     'guard_attestator'     : False,
                                     'guard_verifier'       : False,
                                     'timebombs'            : not self._skip_SLP10,
                                     'dcl'                  : not self._skip_SLP11,
                                     'cf_tagging'           : False,
                                     }

        # Force code mobility if softVM has mobile flag
        softvm_code_mobility = False

        # Update self._binary_annotations based on extracted annotations
        json = join(self._output, annotations_folder, 'annotations.json')
        if (isfile(json)):
            d01 = filterAnnotations(json)

            for filtered_annotations in [a['filtered'] for a in d01]:
                for protection, annotation in filtered_annotations.iteritems():

                    # Set annotation
                    self._binary_annotations[protection] = True

                    # Check for mobile bytecode in softvm annotations
                    if protection == 'softvm' and ('mobile=1' in annotation
                                                   or ('mobile' in annotation and not 'mobile=' in annotation)
                                                   ):
                        softvm_code_mobility = True
                # end if
            # end for
        # end if

        # disable annotations based on configuration file
        for key, values in self._annotations_list.iteritems():
            disabled = getattr(self, '_skip_' + key, False)
            for value in values:
                if(self._binary_annotations.has_key(value)):
                    self._binary_annotations[value] = self._binary_annotations[value] and (not disabled)
        #end for

        # disable annotations based on BLP04 configuration
        self._binary_annotations['anti_debugging'] &= self._config.bin2bin.BLP04['anti_debugging']
        self._binary_annotations['obfuscations'] &= self._config.bin2bin.BLP04['obfuscations']
        self._binary_annotations['call_stack_check'] &= self._config.bin2bin.BLP04['call_stack_check']
        self._binary_annotations['softvm'] &= self._config.bin2bin.BLP04['softvm']
        self._binary_annotations['code_mobility'] &= self._config.bin2bin.BLP04['code_mobility']  # disabled in json
        self._binary_annotations['code_mobility'] |= (self._binary_annotations['softvm'] and softvm_code_mobility)  # turn on for mobile softvm code
        # enable renewability based on SERVER.RENEWABILITY settings and 'code_mobility'
        self._binary_annotations['renewability'] = not (self._config.SERVER.excluded or self._config.SERVER.RENEWABILITY.excluded) and self._binary_annotations['code_mobility']
    # end def task_SLP04_PARSE

    # ==========================================================================
    def task_COMPILE_C(self):
        '''
        SC12 --> compiler --> BC08

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._config.src2bin.excluded):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP12']['out'] + self._folders['SLP04']['suffix']  # cached output of SLP09 with inserted annotations in SLP04
        output_folder = self._folders['COMPILE_C']['out'] + self._folders['COMPILE_C']['suffix']

        # SC09/*.i --> BC08/*.o
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.i')

        dst = join(self._output, output_folder)


        tool = Compiler(program = self._config.tools.frontend,
                        options = self._config.src2bin.options
                                + self._config.src2bin.PREPROCESS.options
                                + ['-D', 'ASPIRE_AID=%s' % (self._aid,)]
                                + self._config.src2bin.COMPILE.options
                                + self._config.src2bin.COMPILE.options_c
                                + ['-g',
                                   '-mfloat-abi=softfp',
                                   '-msoft-float',
                                   '-mfpu=neon'],
                        outputs = (dst, '.o'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('COMPILE_C', input_folder, output_folder)
    # end def task_COMPILE_C

    # ==========================================================================
    def task_COMPILE_CPP(self):
        '''
        SC12 --> compiler --> BC08

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._config.src2bin.excluded):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP12']['out'] + self._folders['SLP04']['suffix']  # cached output of SLP09 with inserted annotations in SLP04
        output_folder = self._folders['COMPILE_CPP']['out'] + self._folders['COMPILE_CPP']['suffix']

        # SC12/*.cpp --> BC08/*.o
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*.cpp')

        dst = join(self._output, output_folder)

        tool = Compiler(program = self._config.tools.frontend,
                        options = self._config.src2bin.options
                                + self._config.src2bin.PREPROCESS.options
                                + ['-D', 'ASPIRE_AID=%s' % (self._aid,)]
                                + self._config.src2bin.COMPILE.options
                                + self._config.src2bin.COMPILE.options_cpp
                                + ['-g',
                                   '-mfloat-abi=softfp',
                                   '-msoft-float',
                                   '-mfpu=neon'],
                        outputs = (dst, '.o'))

        yield tool.tasks(src,
                         header_files=[join(self._output, input_folder, '*.h'),
                                        join(self._output, input_folder, '*.hpp')])

        # ----------------------------------------------------------------------
        self._updateDot('COMPILE_CPP', input_folder, output_folder)
    # end def task_COMPILE_CPP

    # ==========================================================================
    def task_COMPILE_FORTRAN(self):
        '''
        SC12 --> compiler --> BC08

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._config.src2bin.excluded):
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP12']['out'] + self._folders['SLP04']['suffix']  # cached output of SLP09 with inserted annotations in SLP04
        output_folder = self._folders['COMPILE_FORTRAN']['out'] + self._folders['COMPILE_FORTRAN']['suffix']

        # SC12/*.cpp --> BC08/*.o
        # ----------------------------------------------------------------------
        src = [join(self._output, input_folder, '*.f'),
                join(self._output, input_folder, '*.f90')]

        dst = join(self._output, output_folder)

        tool = Compiler(program = self._config.tools.frontend_fortran,
                        options = self._config.src2bin.options
                                + self._config.src2bin.PREPROCESS.options
                                + ['-D', 'ASPIRE_AID=%s' % (self._aid,)]
                                + self._config.src2bin.COMPILE.options
                                + ['-g',
                                   '-mfloat-abi=softfp',
                                   '-msoft-float',
                                   '-mfpu=neon'],
                        outputs = (dst, '.o'))

        yield tool.tasks(src, header_files=[])

        # ----------------------------------------------------------------------
        self._updateDot('COMPILE_FORTRAN', input_folder, output_folder)
    # end def task_COMPILE_ FORTRAN

    # ==========================================================================
    def task_COMPILE_ACCL(self):
        '''
        self._config.tools.accl --> compile ACCL libs --> BC08/accl

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._config.src2bin.excluded):
            return
        # end if

        if(not(self._binary_annotations['barrier_slicing']
            or self._binary_annotations['code_mobility']
            or self._binary_annotations['remote_attestation']
            or self._binary_annotations['anti_cloning']
            or self._binary_annotations['timebombs'])): #reaction_unit
            return
        # end if

        # input and output folders
        output_folder = join(self._folders['ACCL']['out'] + self._folders['ACCL']['suffix'], 'accl')

        # self._config.tools.accl/src/accl.c --> BC08/accl/accl.c.o
        # ----------------------------------------------------------------------
        src  = join(self._config.tools.accl, 'src', 'accl.c')

        dst = join(self._output, output_folder)

        #HACK, ACCL does not compile with all 'self._config.tools.frontend' options
        frontends = {'linux'        : '/opt/diablo-gcc-toolchain/bin/arm-diablo-linux-gnueabi-gcc',
                     'android'      : '/opt/diablo-android-gcc-toolchain/bin/arm-linux-androideabi-gcc',
                     'serverlinux'  : 'gcc'}

        tool_options = self._config.src2bin.PREPROCESS.options + \
                                    ['-I', self.accl_headers,
                                    '-I', self.curl_headers,
                                    '-I', self.websocket_headers,
                                    '-Wall',
                                    '-g',
                                    '-Os',
                                    '-static',
                                    #'-mfloat-abi=softfp',
                                    #'-msoft-float'
                                    '-mfpu=neon',
                                    '-DACCL_ASPIRE_PORTAL_ENDPOINT=\\"%(PROTOCOL)s://%(ENDPOINT)s:%(PORT)s\\"' \
                                            % {
                                            'PROTOCOL' : self._config.src2bin.COMPILE_ACCL.protocol,
                                            'ENDPOINT' : self._config.src2bin.COMPILE_ACCL.endpoint,
                                            'PORT' : self._config.src2bin.COMPILE_ACCL.port,
                                            },
                                    '-DACCL_WS_ASPIRE_PORTAL_HOST=\\"%(ENDPOINT)s\\"'
                                            % {'ENDPOINT' : self._config.src2bin.COMPILE_ACCL.endpoint,},
                                    '-DASPIRE_APPLICATION_ID=\\"%(AID)s\\"'
                                            % {'AID' : self._aid},
                                    '-DACCL_FILE_PATH=\\"%(PATH)s\\"'
                                            % {'PATH' : self._config.src2bin.COMPILE_ACCL.file_path},
                                    '-lz',
                                    '-fPIC']

        tool = Compiler(program = frontends[self._config.platform],
                        options = tool_options,
                        outputs = (dst, '.o'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('COMPILE_ACCL', join(self._config.tools.accl, 'src'), output_folder)
    # end def task_COMPILE_ACCL

    # ==========================================================================
    def task_LINK(self):
        '''
        BC08 --> linker --> BC02

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._config.src2bin.excluded):
            return
        # end if

        # input and output folders
        input_folder = self._folders['COMPILE_C']['out'] + self._folders['COMPILE_C']['suffix']
        output_folder = self._folders['LINK']['out'] + self._folders['LINK']['suffix']
        accl_folder = self._folders['ACCL']['out'] + self._folders['ACCL']['suffix']

        # BC08/*.o --> BC02/<binary>
        # ----------------------------------------------------------------------
        src = [join(self._output, input_folder, '*.o'), ]

        dst = join(self._output, output_folder)

        dot = [input_folder, ]

        if(self._binary_annotations['barrier_slicing']
           or self._binary_annotations['anti_cloning']
           or self._binary_annotations['timebombs']):
            src.extend([join(self._output, accl_folder, 'accl', 'accl.c.o'),
                        join(self.websocket_lib, 'libwebsockets.a')])
            dot.extend([join(accl_folder, 'accl'), self.websocket_lib])
        # end if

        if (self._binary_annotations['barrier_slicing']
            or self._binary_annotations['anti_cloning']
            or self._binary_annotations['timebombs']
            or self._binary_annotations['dcl']):

            src.extend([join(self.curl_lib, 'libcurl.a'),
                    join(self.openssl_lib, 'libssl.a'),
                    join(self.openssl_lib, 'libcrypto.a')])

            dot.extend([self.curl_lib, self.openssl_lib])
        # end if

        if (self._config.platform == 'linux'):
            obj = DIABLO_SP_OBJ_LINUX

        elif (self._config.platform == 'android'):
            obj = DIABLO_SP_OBJ_ANDROID

        else:
            assert False, 'Unknown platform: %s\n' % self._config.platform
        # end if
        src.append(obj)
        dot.append(obj)

#         if (self._binary_annotations['dcl']):
#             print('----------------------APPENDING DCL!!!')
#             src.append(join(self._folders['SLP11']['out'] + self._folders['SLP11']['suffix'], 'dist/libs/armeabi-v7a'))
#             dot.append(join(self._folders['SLP11']['out'] + self._folders['SLP11']['suffix'], 'dist/libs/armeabi-v7a'))
#         # end if

        options = list()
        if (self._config.platform == 'linux'):
            options.append('-lpthread')  # required for reaction units
        #  end if

        tool = Linker(program = self._config.tools.frontend,
                      options = self._config.src2bin.options
                              + self._config.src2bin.LINK.options
                              + ['-g',
                                 '-ldl',
                                 '-mfloat-abi=softfp',
                                 '-msoft-float',
                                 '-mfpu=neon',
                                 '-Wl,-Map,%s.map'
                                 % (join(dst, self._config.src2bin.LINK.binary),)]
                              + options,
                      outputs = (dst, ''))

        yield tool.tasks(src, join(dst, self._config.src2bin.LINK.binary))

        # ----------------------------------------------------------------------
        self._updateDot('LINK', dot, output_folder)
    # end def task_LINK

    # ==========================================================================
    def task_BLP00_VANILLA_METRICS(self):
        '''
        BC02 + D01 --> Generate selfprofiling binaries and collect metrics --> BC02_SP

        @return (Task)
        '''
        # Check configuration
        self._skip_BLP00 = self._config.bin2bin.excluded \
                        or self._config.bin2bin.BLP00.excluded

    # end def task_BLP00_VANILLA_METRICS

    # ==========================================================================
    def task_SERVER_P10_SP(self):
        '''
        Server side management - code splitting (early deploy for self-profiling code)

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if self._skip_BLP00 or self._config.SERVER.excluded:
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP06']['server'] + self._folders['SLP06']['suffix']  # SCS01
        output_folder = input_folder  # SCS01

        # ----------------------------------------------------------------------
        src = join(self._output, input_folder)
        dst = join(src, '.p10_sp_done')

        if (not (isdir(src) and self._config.SERVER.P10.script)):
            return
        # end if

        # Create symlinks before yielding task
        self._create_symlinks()

        yield {'title'   : lambda task: task.name.replace(':', '', 1),
               'name'    : '\n   %-20s%s' % ('code splitting (sp)', src),
               'actions' : [LongRunning(' '.join([self._config.SERVER.P10.script,
                                                '-a' , self._aid,
                                                '-p', '10',
                                                '-i', self._config.SERVER.ip_address,
                                                self._output,
                                                '&&', 'touch', dst])), ],
               'targets' : [dst, ],
               'file_dep': glob(join(src, '*.c')),
               }

        # ----------------------------------------------------------------------
        self._updateDot('SERVER_P10_SP', input_folder, output_folder)
    # end def task_SERVER_P10_SP

    # ==========================================================================
    def task_BLP00_01_SP(self):
        '''
        BC02 + D01 (+BC08)--> compile selfprofiling binary --> BC02_SP

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_BLP00_01 = self._skip_BLP00 \
                            or self._config.bin2bin.BLP00._01.excluded

        if (self._skip_BLP00_01):
            return
        # end if

        # input and output folders
        input_folder = self._folders['LINK']['out'] + self._folders['LINK']['suffix']  # BC02
        annotations_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']  # D01
        object_folder = self._folders['COMPILE_C']['out'] + self._folders['COMPILE_C']['suffix']  # BC08
        output_folder = self._folders['BLP00']['out_sp'] + self._folders['BLP00']['suffix']  # BC02_SP


        # ----------------------------------------------------------------------
        cbin, dbin = self._outfilenames()


        src = [join(self._output, annotations_folder, 'annotations.json'),
                join(self._output, input_folder, cbin)]

        dst = join(self._output, output_folder)


        tool = DiabloObfuscator(program = self._config.tools.obfuscator_sp,
                                options = self._config.bin2bin.BLP00._01.options
                                + ['-SP', 'none'],
                                aid=self._aid,
                                outputs = (dst, ''),
                                self_profiling = True)

        yield tool.tasks(src,
                         join(dst, dbin),
                         objdir=join(self._output, object_folder),)

        # ----------------------------------------------------------------------
        self._updateDot('task_BLP00_01', [input_folder, object_folder, annotations_folder], output_folder)
    # end def def task_BLP00_01_SP:

    def task_BLP00_02_SP(self):
        '''
        BC02_SP --> collect runtime profile on target board --> BC02_SP/profiles

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_BLP00_02 = self._skip_BLP00 \
                            or self._config.bin2bin.BLP00._02.excluded

        if (self._skip_BLP00_02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['BLP00']['out_sp'] + self._folders['BLP00']['suffix']  # BC02_SP
        output_folder = input_folder  # BC02_SP

        # ----------------------------------------------------------------------
        cbin, _ = self._outfilenames()

        src = join(self._output, input_folder)

        dst = join(src, 'profiles', '.BLP00_02done')

        if (not (isdir(src) and self._config.bin2bin.BLP00._02.script)):
            #sys.exit("task_BLP00_02_SP: script '%s' not found " % self._config.bin2bin.BLP00._02.script)
            self._skip_BLP00 =  True
            return
        # end if

        yield {'title'   : lambda task: task.name.replace(':', '', 1),
               'name'    : '\n   %-20s%s' % ('collect metrics', src),
               'actions' : [CmdAction(' '.join([self._config.bin2bin.BLP00._02.script,
                                                self._aid,
                                                src,
                                                '>', join(src, 'BLP00_02_SP.log'), '2>&1',
                                                '&&', 'touch', dst])),],
               'targets' : [dst,],
               'file_dep': glob(join(src, cbin + '*')),
               }
        # ----------------------------------------------------------------------
        self._updateDot('task_BLP00_02', [input_folder], output_folder)
    # end def task_BLP00_02_SP:


    def task_BLP00_03_DYN(self):
        '''
        BC02 + D01 (+BC08 + BC02_SP) --> recompile using execution profile and calculate dynamic metrics --> BC02_DYN

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_BLP00_03 = self._skip_BLP00 \
                            or self._config.bin2bin.BLP00._03.excluded

        if (self._skip_BLP00_03):
            return
        # end if

        # input and output folders
        linker_folder = self._folders['LINK']['out'] + self._folders['LINK']['suffix']  # BC02
        sp_folder = self._folders['BLP00']['out_sp'] + self._folders['BLP00']['suffix']  # BC02_SP
        annotations_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']  # D01
        object_folder = self._folders['COMPILE_C']['out'] + self._folders['COMPILE_C']['suffix']  # BC08
        output_folder = self._folders['BLP00']['out_dyn'] + self._folders['BLP00']['suffix']  # BC02_DYN

        # ----------------------------------------------------------------------
        cbin, dbin = self._outfilenames()

        src = [join(self._output, annotations_folder, 'annotations.json'),
                join(self._output, linker_folder, cbin),
                join(self._output, sp_folder, 'profiles', 'profiling_data.' + cbin + '.self_profiling.plaintext')]

        dst = join(self._output, output_folder)

        tool = DiabloObfuscator(program = self._config.tools.obfuscator_sp,
                                options=self._config.bin2bin.BLP00._03.options,
                                aid=self._aid,
                                outputs = (dst, ''),
                                self_profiling = True)

        yield tool.tasks(src,
                         join(dst, dbin),
                         objdir=join(self._output, object_folder),
                         runtime_profiles = src[2])

        # ----------------------------------------------------------------------
        self._updateDot('BLP00_03_DYN', [linker_folder, sp_folder, object_folder, annotations_folder], output_folder)
    # end def def task_BLP00_03_DYN:

    # ==========================================================================
    def task_BLP01(self):
        '''
        BC02 + BC08 + D01 --> extractor --> BLC02

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_BLP01 = self._config.bin2bin.excluded \
                        or self._config.bin2bin.BLP01.excluded \
                        or not self._binary_annotations['softvm']

        if (self._skip_BLP01):
            return
        # end if

        # input and output folders
        linker_folder = self._folders['LINK']['out'] + self._folders['LINK']['suffix']  # BC02
        output_folder = self._folders['BLP03']['out'] + self._folders['BLP03']['suffix']  # BC04


        # BC02/a.out   --> Traverse --> BC04/c.out
        # BC02/liba.so --> Traverse --> BC04/libc.so
        # ----------------------------------------------------------------------
        if (self._config.bin2bin.BLP01.traverse):

            self._skip_BLP01 = True

            src = join(self._output, linker_folder, self._config.src2bin.LINK.binary + '*')

            dst = join(self._output, output_folder)

            tool = Copier(outputs = (dst, ''))

            yield tool.tasks(src,
                             pattern = r'(?P<lib>lib|)a(?P<ext>\.out|\.so)',
                             replace = r'\1c\2')

            # ------------------------------------------------------------------
            self._updateDot('BLP01_TRAVERSE', linker_folder, output_folder)
        # end if

    # end def task_BLP01

    # ==========================================================================
    def task_BLP01_EXTRACT(self):
        '''
        BC08 + BC02 + D01 --> extractor --> BLC02

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_BLP01):
            return
        # end if

        # input and output folders
        linker_folder = self._folders['LINK']['out'] + self._folders['LINK']['suffix']  # BC02
        annotations_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']  # D01
        object_folder = self._folders['COMPILE_C']['out'] + self._folders['COMPILE_C']['suffix']  # BC08
        output_folder = self._folders['BLP01']['out'] + self._folders['BLP01']['suffix']  # BLC02

        #
        # ----------------------------------------------------------------------
        src = [join(self._output, annotations_folder, 'annotations.json')]

        profile_folder = self._folders['BLP00']['out_sp'] + self._folders['BLP00']['suffix']  # BC02_SP
        profiles = join(self._output, profile_folder, 'profiles', 'profiling_data.' + self._config.src2bin.LINK.binary + '.self_profiling.plaintext')
        if not isfile(profiles):
            profiles = None
        else:
            src.append(profiles)

        dst = join(self._output, output_folder)

        tool = DiabloExtractor(program = self._config.tools.extractor,
                               options = self._config.bin2bin.BLP01.options
                                       + ['--id', self._aid, ],
                               outputs=(dst, ''),
                               softvm_diversity_seed=self._config.bin2bin.bytecode_diversity_seed)

        yield tool.tasks(src,
                         objdir=join(self._output, object_folder),
                         bindir=join(self._output, linker_folder),
                         binary=join(self._output, linker_folder, self._config.src2bin.LINK.binary),
                         runtime_profiles=profiles)

        # ----------------------------------------------------------------------
        self._updateDot('BLP01_EXTRACT', [linker_folder, object_folder, annotations_folder], output_folder)
    # end def task_BLP01_EXTRACT

    # ==========================================================================
    def task_BLP02(self):
        '''

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_BLP02 = self._config.bin2bin.excluded \
                        or self._config.bin2bin.BLP02.excluded \
                        or self._config.bin2bin.BLP01.traverse \
                        or not self._binary_annotations['softvm']

    # end def task_BLP02

    # ==========================================================================
    def task_BLP02_XTRANSLATE(self):
        '''
        BLC02 --> x-translator --> BC03

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_BLP02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['BLP01']['out'] + self._folders['BLP01']['suffix']  # BLC02
        output_folder = self._folders['BLP02']['out'] + self._folders['BLP02']['suffix']  # BC03


        # BLC02/*_chunks.json --> BC03/*_chunks.json.s
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*_chunks.json')

        dst = join(self._output, output_folder, '.')

        tool = Xtranslator(program = self._config.tools.xtranslator,
                           options = self._config.bin2bin.BLP02.options +
                           ['--gen-VM',
                            '--gen-VM-out-dir', join(dst, 'out_gen_vm')],
                           outputs = (dst, '.s'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('BLP02_XTRANSLATE', input_folder, output_folder)
    # end def task_BLP02_XTRANSLATE


    # ==========================================================================
    def task_BLP02_COMPILE(self):
        '''
        BC03--> compile --> BC03

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_BLP02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['BLP02']['out'] + self._folders['BLP02']['suffix']  # BC03
        output_folder = input_folder  # BC03

        # BC03/*_chunks.json.s --> BC03/*_chunks.json.s.o
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, '*_chunks.json.s')

        dst = join(self._output, output_folder)

        tool = Compiler(program = self._config.tools.frontend,
                        options = self._config.src2bin.options
                                + self._config.src2bin.PREPROCESS.options
                                + self._config.src2bin.COMPILE.options
                                + self._config.src2bin.COMPILE.options_c
                                + ['-mfloat-abi=softfp',
                                   '-msoft-float',
                                   '-mfpu=neon'],
                        outputs = (dst, '.o'))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('BLP02_COMPILE', input_folder, output_folder)
    # end def task_BLP02_COMPILE

        # ==========================================================================
    def task_BLP02_COMPILE_VM(self):
        '''
        BC03/out_gen_vm --> compile VM --> BC03/out_gen_vm/out

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_BLP02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['BLP02']['out'] + self._folders['BLP02']['suffix']  # BC03
        output_folder = input_folder  # BC03

        # BC03/*_chunks.json.s --> BC03/*_chunks.json.s.o
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, 'out_gen_vm', '*.c')

        dst = join(self._output, output_folder, 'out_gen_vm', 'out')

        tool = Compiler(program=self._config.tools.frontend,
                        options=self._config.src2bin.options
                                + self._config.src2bin.PREPROCESS.options
                                + self._config.src2bin.COMPILE.options
                                + self._config.src2bin.COMPILE.options_c
                                + ['-std=c99',
                                   '-Wall',
                                   '-pedantic',
                                   '-fpic',
                                   '-O2',
                                   '-I%s' % dirname(src),
                                   '-DFOR_EXECUTABLE' if not self._config.src2bin.LINK.binary.endswith('.so') else ''],
                        outputs=(dst, ''))

        yield tool.tasks(src, '\.c$', '.o')

        # ----------------------------------------------------------------------
        self._updateDot('BLP02_COMPILE_VM', input_folder, output_folder)
    #  end def task_BLP02_COMPILE_VM

    # ==========================================================================
    def task_BLP02_ARCHIVE_VM(self):
        '''
        BC03/out_gen_vm/out/ --> archive vm --> BC03/out_gen_vm/out/vm.a

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_BLP02):
            return
        # end if

        # input and output folders
        input_folder = self._folders['BLP02']['out'] + self._folders['BLP02']['suffix']  # BC03
        output_folder = input_folder  # BC03

        # BC03/*_chunks.json.s --> BC03/*_chunks.json.s.o
        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, 'out_gen_vm', 'out', '*.o')

        dst = join(self._output, output_folder, 'out_gen_vm', 'out')

        # HACK select proper archiving tool
        frontend = self._config.tools.frontend
        if frontend.endswith('gcc'):
            frontend = frontend[:-3] + 'ar'

        elif frontend.endswith('clang'):
            frontend = join(dirname(frontend), 'llvm-ar')
        # end if

        tool = Archiver(program=frontend,
                        options=[],
                        outputs=(dst, ''))

        yield tool.tasks(src, join(dst, 'vm.a'))

        # ----------------------------------------------------------------------
        self._updateDot('BLP02_ARCHIVE_VM', input_folder, output_folder)
    #  end def task_BLP02_ARCHIVE_VM


    # ==========================================================================
    def task_BLP03(self):
        '''
        BC03 + BC08 + D01 --> linker --> BC04

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_BLP03 = self._config.bin2bin.excluded \
                        or self._config.bin2bin.BLP03.excluded \
                        or self._config.bin2bin.BLP01.traverse

    # end def task_BLP03


    # ==========================================================================
    def task_BLP03_LINK(self):                                                  # pylint:disable=R0912
        '''
        BC03 + BC08 + D01 --> linker --> BC04

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_BLP03):
            return
        # end if

        # input and output folders
        annotations_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']  # D01
        object_folder = self._folders['COMPILE_C']['out'] + self._folders['COMPILE_C']['suffix']  # BC08
        xtranslator_folder = self._folders['BLP02']['out'] + self._folders['BLP02']['suffix']  # BC03
        output_folder = self._folders['BLP03']['out'] + self._folders['BLP03']['suffix']  # BC04
        ra_folder = self._folders['SLP07']['out'] + self._folders['SLP07']['suffix']  # BC07
        accl_folder = self._folders['ACCL']['out'] +self._folders['ACCL']['suffix'] #BC08

        # ----------------------------------------------------------------------

        json = join(self._output, annotations_folder, 'annotations.json')

        # ----------------------------------------------------------------------

        remote_lib = join(self._output, ra_folder)

        binder_obj      = join(self._config.tools.code_mobility,
                               'binder', 'obj', self._config.platform)

        debugger_obj    = join(self._config.tools.anti_debugging,
                               'obj', self._config.platform)

        downloader_obj  = join(self._config.tools.code_mobility,
                               'downloader', 'obj', self._config.platform)
        renewability_obj = join(self._config.tools.renewability,
                               'obj', self._config.platform)

        xtranslator_obj = join(self._output, xtranslator_folder, 'out_gen_vm', 'out')

        src = [json,
               join(self._output, xtranslator_folder, '*.o'),
               join(self._output, object_folder, '*.o')]

        frontend = self._config.tools.frontend

        options  = list()
        if (self._config.platform == 'linux'):
            options.append('-lpthread')

        elif (self._config.platform == 'android'):
            options.append('-fuse-ld=bfd')
        # end if

        dot = [xtranslator_folder, object_folder]

        if (self._binary_annotations['remote_attestation']):
            src.append(join(remote_lib, '*.o'))

            dot.append(remote_lib)
        # end if

        if (self._binary_annotations['code_mobility']):
            src.extend([join(binder_obj, 'binder.o'), join(downloader_obj, 'downloader.o')])
            dot.extend([binder_obj, downloader_obj])

            # link in renewability object if requested
            if self._binary_annotations['renewability']:
                src.append(join(renewability_obj, 'renewability.o'))
                dot.append(renewability_obj)
        # end if

        if (self._binary_annotations['anti_debugging']):
            src.append(join(debugger_obj, '*.o'))

            dot.append(debugger_obj)
        # end if

        if (self._binary_annotations['softvm']):
            src.append(join(xtranslator_obj, 'vmExecute.o'))

            dot.append(xtranslator_obj)
        # end if

        if(self._config.bin2bin.BLP04['self-profiling']):
            obj = 'none'
            if (self._config.platform == 'linux'):
                obj = DIABLO_SP_OBJ_LINUX

            elif (self._config.platform == 'android'):
                obj = DIABLO_SP_OBJ_ANDROID

            else:
                assert False, 'Unknown platform: %s\n' % self._config.platform
            # end if
            src.append(obj)
            dot.append(obj)
        # end if

#         if (self._binary_annotations['dcl']):
#             src.append(join(self._folders['SLP11']['out'] + self._folders['SLP11']['suffix'], 'dist/libs/armeabi-v7a'))
#             dot.append(join(self._folders['SLP11']['out'] + self._folders['SLP11']['suffix'], 'dist/libs/armeabi-v7a'))
#         # end if

        '''
        if (self._binary_annotations['barrier_slicing']
            or self._binary_annotations['anti_cloning']
            or self._binary_annotations['timebombs']
            or self._binary_annotations['dcl']):

            src.extend([join(self.curl_lib, 'libcurl.a'),
                    join(self.openssl_lib, 'libssl.a'),
                    join(self.openssl_lib, 'libcrypto.a')])

            dot.extend([self.curl_lib, self.openssl_lib])
        # end if

        if(self._binary_annotations['barrier_slicing']
           or self._binary_annotations['anti_cloning']
           or self._binary_annotations['timebombs']):
            src.extend([join(self._output, accl_folder, 'accl', 'accl.c.o'),
                        join(self.websocket_lib, 'libwebsockets.a')])
            dot.extend([join(accl_folder, 'accl'), self.websocket_lib])
        # end if
        '''

        lzAdded = False

        if (self._binary_annotations['barrier_slicing']
            or self._binary_annotations['code_mobility']
            or self._binary_annotations['remote_attestation']
            or self._binary_annotations['anti_cloning']
            or self._binary_annotations['timebombs']):
            src.extend([join(self._output, accl_folder, 'accl', 'accl.c.o'),
                        join(self.websocket_lib, 'libwebsockets.a')])

            if (self._config.platform == 'android'):
                # Issue 155
                options.append('-lz')
                lzAdded = True
            #  end if

            dot.extend([join(accl_folder, 'accl'), self.websocket_lib])
        # end if

        if (self._binary_annotations['barrier_slicing']
            or self._binary_annotations['code_mobility']
            or self._binary_annotations['remote_attestation']
            or self._binary_annotations['anti_cloning']
            or self._binary_annotations['timebombs']
            or self._binary_annotations['dcl']):
            src.extend([join(self.curl_lib,      'libcurl.a'),
                        join(self.openssl_lib,   'libssl.a'),
                        join(self.openssl_lib,   'libcrypto.a')])

            if ((self._config.platform == 'android') and not lzAdded):
                # Issue 155
                options.append('-lz')
            # end if

            dot.extend([self.curl_lib, self.openssl_lib])
        # end if


        if (self._binary_annotations['softvm']):
            src.append(join(xtranslator_obj, 'vm.a'))

            # Issue 154:
            # The linker should be changed from clang to clang++ (or from gcc to g++),
            # as the SoftVM-related object files now contain C++ code.
            if   frontend.endswith('gcc'):
                frontend = frontend[:-2] + '++'

            elif frontend.endswith('clang'):
                frontend = frontend + '++'

            # end if

            dot.append(xtranslator_obj)
        # end if

        dst = join(self._output, output_folder)

        binary, _ = self._outfilenames()

        binary = join(dst, binary)

        tool = Linker(program = frontend,
                      options = self._config.src2bin.options
                              + self._config.src2bin.LINK.options
                              + options
                              + ['-g',
                                 '-ldl',
                                 '-lm',
                                 '-mfloat-abi=softfp',
                                 '-msoft-float',
                                 '-mfpu=neon',
                                 '-Wl,-Map,%s.map' % (binary,)],
                      outputs = (dst, ''))

        yield tool.tasks(src, binary)

        # ----------------------------------------------------------------------
        self._updateDot('BLP03_LINK', dot, output_folder)
    # end def task_BLP03_LINK

    # ==========================================================================
    def task_BLP03_migrate_profile(self):
        # runtime profiles
        profile_folder = self._folders['BLP00']['out_sp'] + self._folders['BLP00']['suffix']  # BC02_SP

        cbin, _ = self._outfilenames()

        src_profile = join(self._output, profile_folder, 'profiles', 'profiling_data.' + cbin + '.self_profiling.plaintext')

        if(not (self._config.bin2bin.BLP04['runtime_profiles'] and isfile(src_profile))):
            return

        # translate the BC02 profile so it is compatible with BC04 (the instruction addresses have changed)
        dst = join(self._output, self._folders['BLP00']['out_migrate'] + self._folders['BLP00']['suffix'])
        dst_profile = join(dst, 'profiling_data.' + cbin + '.self_profiling.plaintext')

        tool = ProfileTranslator(options =    ['-p', src_profile]
                                            + ['-q', dst_profile]
                                            + ['-m', join(self._output, 'BC02', self._config.src2bin.LINK.binary + '.map')]
                                            + ['-n', join(self._output, 'BC04', self._config.src2bin.LINK.binary + '.map')],
                                 outputs = (dst, ''))
        yield tool.tasks(src_profile, dst_profile)
    # end def task_BLP03_migrate_profile


    # ==========================================================================
    def task_BLP04(self):
        '''
        BC04 + D01 (+ BC08 + BC03 + BLC02) --> obfuscation --> BC05

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_BLP04 = self._config.bin2bin.excluded \
                        or self._config.bin2bin.BLP04.excluded

    # end def task_BLP04

    # ==========================================================================
    def task_BLP04_OBFUSCATE(self):
        '''
        BC04 + D01 (+ BC08 + BC03 + BLC02 (+ BC02_SP/profiles)) --> obfuscation --> BC05

        #WARNING:  update task_BLP04_DYN_02 accordingly

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if (self._skip_BLP04):
            return
        # end if

        # input and output folders
        annotations_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']  # D01
        object_folder = self._folders['COMPILE_C']['out'] + self._folders['COMPILE_C']['suffix']  # BC08
        xtranslator_folder = self._folders['BLP02']['out'] + self._folders['BLP02']['suffix']  # BC03
        linker_folder = self._folders['BLP03']['out'] + self._folders['BLP03']['suffix']  # BC04
        extractor_folder = self._folders['BLP01']['out'] + self._folders['BLP01']['suffix']  # BLC02
        output_folder = self._folders['BLP04']['out'] + self._folders['BLP04']['suffix']  # BC05

        # ----------------------------------------------------------------------
        cbin, dbin = self._outfilenames()

        # source
        src = [join(self._output, annotations_folder, 'annotations.json'),
                join(self._output, linker_folder, cbin)]

        # destination
        dst = [join(self._output, output_folder), ]
        if(self._binary_annotations['code_mobility']):
            dst.append(join(self._output, output_folder, 'mobile_blocks'))

        # runtime profiles
        profiles = join(self._output, self._folders['BLP00']['out_migrate'] + self._folders['BLP00']['suffix'], 'profiling_data.' + cbin + '.self_profiling.plaintext')

        if(not (self._config.bin2bin.BLP04['runtime_profiles'] and isfile(profiles))):
            profiles = None
        else:
            src.append(profiles)

        # options
        options = []
        options.append('-CM %s' % ('on' if self._binary_annotations['code_mobility'] else 'off'))
        options.append('-CS %s' % ('on' if self._binary_annotations['call_stack_check'] else 'off'))
        options.append('-CG %s' % ('on' if (self._binary_annotations['guarded_region'] or self._binary_annotations['guard_attestator'] or self._binary_annotations['guard_verifier']) else 'off'))
        options.append('-OBF %s' % ('on' if self._binary_annotations['obfuscations'] else 'off'))
        options.append('-RA %s' % ('on' if (self._binary_annotations['remote_attestation'] or self._binary_annotations['remote_attestation'])else 'off'))
        options.append('-SD %s' % ('on' if self._binary_annotations['anti_debugging'] else 'off'))
        options.append('-SV %s' % ('on' if self._binary_annotations['softvm'] else 'off'))
        options.append('-CFT %s' % ('on' if self._binary_annotations['cf_tagging'] else 'off'))

        if(self._config.bin2bin.BLP04['self-profiling']):
            options.extend(['-SP', 'none'])
        # end if

        # instanciate tool
        tool = DiabloObfuscator(program = self._config.tools.obfuscator,
                                options = self._config.bin2bin.BLP04.options
                                + options ,
                                aid=self._aid,
                                softvm_diversity_seed=self._config.bin2bin.bytecode_diversity_seed,
                                code_mobility_diversity_seed=self._config.bin2bin.code_mobility_diversity_seed,
                                outputs=[(path, '') for path in dst])

        yield tool.tasks(src,
                         join(dst[0], dbin),
                         objdir=join(self._output, object_folder),
                         stubdir=join(self._output, xtranslator_folder),
                         vmdir       = join(dirname(self._config.tools.xtranslator),
                                            'obj', self._config.platform),
                         chunks_file=join(self._output, extractor_folder, 'annotations_chunks.json'),
                         runtime_profiles=profiles)

        # ----------------------------------------------------------------------
        self._updateDot('BLP04_OBFUSCATE', [linker_folder, xtranslator_folder, extractor_folder, object_folder, annotations_folder], output_folder)

        # Generate renewability script for code mobility
        if(self._binary_annotations['code_mobility']):
            block_path = dst[1]

            # instanciate tool
            renewability_tool = RenewableMobileBlocksGenerator(program=self._config.tools.obfuscator,
                                    options=self._config.bin2bin.BLP04.options
                                    + options ,
                                    aid=self._aid,
                                    softvm_diversity_seed=self._config.bin2bin.bytecode_diversity_seed,
                                    code_mobility_diversity_seed=self._config.bin2bin.code_mobility_diversity_seed,
                                    script=self._config.SERVER.P20.script,
                                    ip_addr=self._config.SERVER.ip_address,
                                    block_path=block_path,
                                    outputs=[(path, '') for path in dst])

            yield renewability_tool.tasks(src,
                             join(dst[0], 'generate_blocks_' + dbin + '.sh'),
                             dst_object=join(dst[0], dbin),
                             objdir=join(self._output, object_folder),
                             stubdir=join(self._output, xtranslator_folder),
                             vmdir=join(dirname(self._config.tools.xtranslator),
                                                'obj', self._config.platform),
                             chunks_file=join(self._output, extractor_folder, 'annotations_chunks.json'),
                             runtime_profiles=profiles,)
        # end if
    # end def task_BLP04_OBFUSCATE

    def task_BLP04_DYN(self):
        '''
        BC04 + D01 + BC02_SP/profiles --> obfuscation using runtime profiles --> BC05_DYN

        @return (Task)
        '''
        # Check configuration
        self._skip_BLP04_DYN = self._config.bin2bin.excluded \
                        or self._config.bin2bin.BLP04_DYN.excluded

    # end def task_BLP04_DYN

    # ==========================================================================
    def task_SERVER_P20_SP(self):
        '''
        Server side management - code mobility (early deploy for self-profiling code)

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if self._skip_BLP04_DYN or self._config.SERVER.excluded:
            return
        # end if

        # input and output folders
        input_folder = self._folders['BLP04']['out'] + self._folders['BLP04']['suffix']  # BC05
        output_folder = input_folder  # BC05

        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, 'mobile_blocks')
        dst = join(src, '.p20_sp_done')

        if (not (isdir(src) and self._config.SERVER.P20.script)):
            return
        # end if

        # Create symlinks before yielding task
        self._create_symlinks()

        yield {'title'   : lambda task: task.name.replace(':', '', 1),
               'name'    : '\n   %-20s%s' % ('code mobility (sp)', src),
               'actions' : [LongRunning(' '.join([self._config.SERVER.P20.script,
                                                '-a' , self._aid,
                                                '-p', '20',
                                                '-i', self._config.SERVER.ip_address,
                                                src,
                                                '"[0-9].self_profiling$"',
                                                '&&', 'touch', dst])), ],
               'targets' : [dst, ],
               'file_dep': glob(join(src, 'mobile_dump_*')),
               }

        # ----------------------------------------------------------------------
        self._updateDot('SERVER_P20_SP', input_folder, output_folder)
    # end def task_SERVER_P20_SP


    # ==========================================================================
    def task_SERVER_P80_SP(self):
        '''
        Server side management - remote attestation (early deploy for self-profiling code)

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if self._skip_BLP04_DYN or self._config.SERVER.excluded:
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP07']['out'] + self._folders['SLP07']['suffix']  # BC07
        output_folder = input_folder  # BC07
        binary_folder = self._folders['BLP04']['out'] + self._folders['BLP04']['suffix']  # BC05

        # ----------------------------------------------------------------------
        src = join(self._output, input_folder)
        dst = join(src, '.p80_sp_done')

        _, dbin = self._outfilenames()

        if (not (isdir(src) and self._config.SERVER.P80.script)):
            return
        # end if

        # Create symlinks before yielding task
        self._create_symlinks()

        yield {'title'   : lambda task: task.name.replace(':', '', 1),
               'name'    : '\n   %-20s%s' % ('remote attestation (sp)', src),
               'actions' : [LongRunning(' '.join([self._config.SERVER.P80.script,
                                                '-a' , self._aid,
                                                '-p', '80',
                                                '-e', join(self._output, input_folder),
                                                '-b', join(self._output, binary_folder, dbin),
                                                '&&', 'touch', dst])), ],
               'targets' : [dst, ],
               'file_dep': glob(join(src, '*.o')),
               }

        # ----------------------------------------------------------------------
        self._updateDot('SERVER_P80_SP', input_folder, output_folder)
    # end def task_SERVER_P80_SP

    # ==========================================================================
    def task_BLP04_DYN_01(self):
        '''
        BC05 --> collect runtime profile on target board --> BC05/profiles

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_BLP04_DYN_01 = self._skip_BLP04_DYN \
                        or self._config.bin2bin.BLP04_DYN._01.excluded

        if (self._skip_BLP04_DYN_01):
            return
        # end if

        # input and output folders
        input_folder = self._folders['BLP04']['out'] + self._folders['BLP04']['suffix']  # BC05
        output_folder = input_folder  # BC05

        # ----------------------------------------------------------------------
        cbin, _ = self._outfilenames()

        src = join(self._output, input_folder)

        dst = join(src, 'profiles', '.BLP04_DYN_01done')

        p20_sp_done = join(self._output, self._folders['BLP04']['out'] + self._folders['BLP04']['suffix'], 'mobile_blocks', '.p20_sp_done')
        p80_sp_done = join(self._output, self._folders['SLP07']['out'] + self._folders['SLP07']['suffix'], '.p80_sp_done')

        if (not (isdir(src) and self._config.bin2bin.BLP04_DYN._01.script and isfile(self._config.bin2bin.BLP04_DYN._01.script))):
            return
        # end if

        yield {'title'   : lambda task: task.name.replace(':', '', 1),
               'name'    : '\n   %-20s%s' % ('metrics', src),
               'actions' : [CmdAction(' '.join([self._config.bin2bin.BLP04_DYN._01.script,
                                                self._aid,
                                                src,
                                                '>', join(src, 'BLP04_DYN_01.log'), '2>&1',
                                                '&&', 'touch', dst])),],
               'targets' : [dst,],
               'file_dep': glob(join(src, cbin + '*')),
               }
        # ----------------------------------------------------------------------
        self._updateDot('BLP04_DYN_01', [input_folder, p20_sp_done, p80_sp_done], output_folder)
    # end def _task_BLP04_DYN_01

    # ==========================================================================
    def task_BLP04_DYN_02(self):
        '''
        BC04 + BC05/profiles + D01 (+ BC08 + BC03 + BLC02 --> recompile using execution profile and calculate dynamic metrics--> BC05_DYN

        #WARNING:  update task_BLP04_OBFUSCATE accordingly

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_BLP04_DYN_02 = self._skip_BLP04_DYN \
                        or self._config.bin2bin.BLP04_DYN._02.excluded

        if (self._skip_BLP04_DYN_02):
            return
        # end if

        # input and output folders
        annotations_folder = self._folders['SLP04']['out'] + self._folders['SLP04']['suffix']  # D01
        profile_folder = self._folders['BLP00']['out_migrate'] + self._folders['BLP00']['suffix']
        object_folder = self._folders['COMPILE_C']['out'] + self._folders['COMPILE_C']['suffix']  # BC08
        xtranslator_folder = self._folders['BLP02']['out'] + self._folders['BLP02']['suffix']  # BC03
        linker_folder = self._folders['BLP03']['out'] + self._folders['BLP03']['suffix']  # BC04
        extractor_folder = self._folders['BLP01']['out'] + self._folders['BLP01']['suffix']  # BLC02
        obfuscator_folder = self._folders['BLP04']['out'] + self._folders['BLP04']['suffix']  # BC05
        output_folder = self._folders['BLP04_DYN']['out'] + self._folders['BLP04_DYN']['suffix']  # BC05_DYN

        # ----------------------------------------------------------------------
        cbin, dbin = self._outfilenames()

        # source
        src = [join(self._output, annotations_folder, 'annotations.json'),
                join(self._output, linker_folder, cbin), ]

        # destination
        dst = [join(self._output, output_folder), ]
        if(self._binary_annotations['code_mobility']):
            dst.append(join(self._output, output_folder, 'mobile_blocks'))

        # runtime profiles
        profiles = join(self._output, profile_folder, 'profiling_data.' + cbin + '.self_profiling.plaintext')
        if(not (self._config.bin2bin.BLP04['runtime_profiles'] and isfile(profiles))):
            profiles = None
        else:
            src.append(profiles)

        # runtime profiles
        profiles_obf = join(self._output, obfuscator_folder, 'profiles', 'profiling_data.' + cbin + '.self_profiling.plaintext')
        if(not (self._config.bin2bin.BLP04['runtime_profiles'] and isfile(profiles_obf))):
            profiles_obf = None
        else:
            src.append(profiles_obf)


        # options
        options = []
        options.append('-CM %s' % ('on' if self._binary_annotations['code_mobility'] else 'off'))
        options.append('-CS %s' % ('on' if self._binary_annotations['call_stack_check'] else 'off'))
        options.append('-CG %s' % ('on' if (self._binary_annotations['guarded_region'] or self._binary_annotations['guard_attestator'] or self._binary_annotations['guard_verifier']) else 'off'))
        options.append('-OBF %s' % ('on' if self._binary_annotations['obfuscations'] else 'off'))
        options.append('-RA %s' % ('on' if (self._binary_annotations['remote_attestation'] or self._binary_annotations['remote_attestation'])else 'off'))
        options.append('-SD %s' % ('on' if self._binary_annotations['anti_debugging'] else 'off'))
        options.append('-SV %s' % ('on' if self._binary_annotations['softvm'] else 'off'))
        options.append('-CFT %s' % ('on' if self._binary_annotations['cf_tagging'] else 'off'))

        # instanciate tool
        tool = DiabloObfuscator(program=self._config.tools.obfuscator,
                                options=self._config.bin2bin.BLP04.options
                                + options,
                                aid=self._aid,
                                softvm_diversity_seed=self._config.bin2bin.bytecode_diversity_seed,
                                code_mobility_diversity_seed=self._config.bin2bin.code_mobility_diversity_seed,
                                outputs=[(path, '') for path in dst])

        yield tool.tasks(src,
                         join(dst[0], dbin),
                         objdir=join(self._output, object_folder),
                         stubdir=join(self._output, xtranslator_folder),
                         vmdir=join(dirname(self._config.tools.xtranslator),
                                            'obj', self._config.platform),
                         chunks_file=join(self._output, extractor_folder, 'annotations_chunks.json'),
                         runtime_profiles=profiles,
                         runtime_profiles_obf=profiles_obf)

        # ----------------------------------------------------------------------
        self._updateDot('task_BLP04_DYN_02', [obfuscator_folder, xtranslator_folder, linker_folder, extractor_folder, object_folder, annotations_folder, profile_folder], output_folder)
    # end def task_BLP04_DYN_02

    # ==========================================================================
    def task_CREATE_SYMLINKS(self):
        '''
        Creates symlinks to the cached folders
        '''
        self._create_symlinks()
    #end def task_CREATE_SYMLINKS

    # ==========================================================================
    def task_SERVER_P10(self):
        '''
        Server side management - code splitting

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if self._config.SERVER.excluded:
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP06']['server'] + self._folders['SLP06']['suffix']  # SCS01
        output_folder = input_folder  # SCS01

        # ----------------------------------------------------------------------
        src = join(self._output, input_folder)
        dst = join(src, '.p10done')

        if (not (isdir(src) and self._config.SERVER.P10.script)):
            return
        # end if

        yield {'title'   : lambda task: task.name.replace(':', '', 1),
               'name'    : '\n   %-20s%s' % ('code splitting', src),
               'actions' : [LongRunning(' '.join([self._config.SERVER.P10.script,
                                                '-a' , self._aid,
                                                '-p', '10',
                                                '-i', self._config.SERVER.ip_address,
                                                self._output,
                                                '&&', 'touch', dst])),],
               'targets' : [dst,],
               'file_dep': glob(join(src, '*.c')),
               }

        # ----------------------------------------------------------------------
        self._updateDot('SERVER_P10', input_folder, output_folder)
    # end def task_SERVER_P10


    # ==========================================================================
    def task_SERVER_P20(self):
        '''
        Server side management - code mobility

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if self._config.SERVER.excluded:
            return
        # end if

        # input and output folders
        input_folder = self._folders['BLP04']['out'] + self._folders['BLP04']['suffix']  # BC05
        output_folder = input_folder  # BC05

        # ----------------------------------------------------------------------
        src = join(self._output, input_folder, 'mobile_blocks')
        dst = join(src, '.p20done')

        if (not (isdir(src) and self._config.SERVER.P20.script)):
            return
        # end if

        yield {'title'   : lambda task: task.name.replace(':', '', 1),
               'name'    : '\n   %-20s%s' % ('code mobility', src),
               'actions' : [LongRunning(' '.join([self._config.SERVER.P20.script,
                                                '-a' , self._aid,
                                                '-p', '20',
                                                '-i', self._config.SERVER.ip_address,
                                                src,
                                                '"[0-9]$"',
                                                '&&', 'touch', dst])),],
               'targets' : [dst,],
               'file_dep': glob(join(src, 'mobile_dump_*')),
               }

        # ----------------------------------------------------------------------
        self._updateDot('SERVER_P20', input_folder, output_folder)
    # end def task_SERVER_P20


    # ==========================================================================
    def task_SERVER_P80(self):
        '''
        Server side management - remote attestation

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if self._config.SERVER.excluded:
            return
        # end if

        # input and output folders
        input_folder = self._folders['SLP07']['out'] + self._folders['SLP07']['suffix']  # BC07
        output_folder = input_folder  # BC07
        binary_folder = self._folders['BLP04']['out'] + self._folders['BLP04']['suffix']  # BC05

        # ----------------------------------------------------------------------
        src = join(self._output, input_folder)
        dst = join(src, '.p80done')

        _, dbin = self._outfilenames()

        if (not (isdir(src) and self._config.SERVER.P80.script)):
            return
        # end if

        yield {'title'   : lambda task: task.name.replace(':', '', 1),
               'name'    : '\n   %-20s%s' % ('remote attestation', src),
               'actions' : [LongRunning(' '.join([self._config.SERVER.P80.script,
                                                '-a' , self._aid,
                                                '-p', '80',
                                                '-e', join(self._output, input_folder),
                                                '-b', join(self._output, binary_folder, dbin),
                                                '&&', 'touch', dst])),],
               'targets' : [dst,],
               'file_dep': glob(join(src, '*.o')),
               }

        # ----------------------------------------------------------------------
        self._updateDot('SERVER_P80', input_folder, output_folder)
    # end def task_SERVER_P80

    # ==========================================================================
    def task_SERVER_RENEWABILITY_CREATE(self):
        '''
        Server side management -  renewability - register application

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if self._config.SERVER.excluded or self._config.SERVER.RENEWABILITY.excluded:
            return
        # end if

        # ----------------------------------------------------------------------
        src = join(self._output, 'AID.txt')  # Depend on the AID file
        dst = join(self._output, '.server_renewability_create')

        if (not (self._config.SERVER.RENEWABILITY.new_application_script
                 and isfile(self._config.SERVER.RENEWABILITY.new_application_script))):
            return
        # end if


        # instanciate tool
        tool = RenewabilityCreate(program=self._config.SERVER.RENEWABILITY.new_application_script,
                                options=['-a', self._aid],
                                outputs=(dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SERVER_RENEWABILITY_CREATE', src, dst)
    # end def task_SERVER_P80

    # ==========================================================================
    def task_SERVER_RENEWABILITY_POLICY(self):
        '''
        Server side management -  renewability - set policy

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        if self._config.SERVER.excluded or self._config.SERVER.RENEWABILITY.excluded:
            return
        # end if

        # ----------------------------------------------------------------------
        src = join(self._output, 'AID.txt')  # Depend on the AID file
        dst = join(self._output, '.server_renewability_policy')

        if (not (self._config.SERVER.RENEWABILITY.set_policy_script
                 and isfile(self._config.SERVER.RENEWABILITY.set_policy_script))):
            return
        # end if


        # instanciate tool
        tool = RenewabilityPolicy(program=self._config.SERVER.RENEWABILITY.set_policy_script,
                                options=['-a', self._aid,
                                         '-d', self._config.SERVER.RENEWABILITY.revision_duration,
                                         '-m', '1' if self._config.SERVER.RENEWABILITY.timeout_mandatory else '0',
                                         '-r', join(self._output, 'BC05', 'generate_blocks_' + self._config.src2bin.LINK.binary + '.sh') ],
                                outputs=(dst, ''))

        yield tool.tasks(src)

        # ----------------------------------------------------------------------
        self._updateDot('SERVER_RENEWABILITY_POLICY', src, dst)
    # end def task_SERVER_P80

    # ==========================================================================
    def task_POST(self):
        '''
        Post processing

        @return (Task)
        '''
        if (self._config.POST.args):
            yield {'title'   : lambda task: task.name.replace(':', '', 1),
                   'name'    : '\n   %s' % (self._config.POST.brief,),
                   'actions' : [CmdAction(' '.join(toList(self._config.POST.args))),],
                   # No explicit target, only dependencies
                   'uptodate': [check_timestamp_unchanged(f)
                                for f in iglob(join(self._output, '*', '*.*'))]
                   }
        # end if
    # end def task_POST

    # ==========================================================================
    def task_M01(self):
        '''
        Gather metrics

        @return (Task)
        '''
        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_M01 = self._config.METRICS.excluded

    # end def task_M01


    # ==========================================================================
    def task_M01_COLLECT(self):
        '''
        Gather static metrics

        @return (Task)
        '''

        # Check configuration
        # ----------------------------------------------------------------------
        self._skip_M01_01 = self._config.METRICS.excluded

        if (self._skip_M01_01):
            return
        # end if

        # metrics files --> M01
        # ----------------------------------------------------------------------

        suffixes = dict()
        for key, values in self._folders.items():
            for key2, value2 in values.items():
                if key2 != 'suffix':
                    suffixes[value2] = values['suffix']

        identifier = suffixes['M01']  # TODO use identifier from JSON file

        # Copy the annotations and patch file

        src = [self._config.src2src.SLP01.annotations_patch, self._config.src2src.SLP01.external_annotations]
        dst = join(self._output, 'M01', identifier[1:])
        tool = Copier(outputs=(dst, ''))
        yield tool.tasks([s for s in src if s])

        # Copy the metrics
        for key in  self._config.METRICS.files:
            keys = key.split(r'/', 1) + ['']
            key1, key2 = keys[0:2]

            values = self._config.METRICS.files[key]
            folder = join(key1 + suffixes[key1], key2)

            src = []
            for value in values:
                src.append(join(self._output, folder, value))


            if(src):
                dst = join(self._output, 'M01', identifier[1:], key)

                tool = Copier(outputs=(dst, ''))

                yield tool.tasks(src)

        # ------------------------------------------------------------------
        self._updateDot('M01_STATIC', self._config.METRICS.files.keys(), 'M01')
    # end def task_M01_COLLECT

    def processDot(self):
        '''
        Generate ACTC processing graph
        '''
        lines = list()
        lines.append('digraph G {')
        lines.append('fontname=courier;')
        lines.append('fontsize=14;')
        lines.append('labelloc="t"; label="CFG: %s (%s)\\lAID: %s \\n ";'
                     % (self._module, strftime('%F %T'), self._aid))
        lines.append('node [fontname=courier, fontsize=10, color=blue, shape=folder];')
        lines.append('edge [fontsize=10, color=firebrick];')

        def dotify(msg):
            '''
            Format dot label

            @param msg [in] (str) text
            @return (str)
            '''
            return msg.replace('.', '_').replace('/', '_').replace('-', '_')
        # end def dotify

        nodes = list()
        def declareNodes(folders):
            '''
            Node definition

            @param folders [in] (list) SC02..BC05
            '''
            for folder in folders:

                if (not folder):
                    folder = getcwd()
                # end if

                if (folder in nodes):
                    continue
                # end if

                # client_server_splitter
                if ('libraries' in folder):
                    path = self._config.tools.client_server_splitter
                else:
                    path = self._output
                # end if

                path    = join(path, folder)
                modules = ['',]

                for pattern in ('*', '*/*'):

                    if (modules[-1] != ''):
                        modules.append('')
                    # end if

                    modules.extend(sorted([module.replace(path + sep, '')
                                           for module in iglob(join(path, pattern))
                                           if isfile(module)]))
                # end for

                try:
                    while (modules[-1] == ''):
                        modules.pop()
                    # end while
                except IndexError:
                    continue
                # end if

                nodes.append(folder)
                lines.append('%s [label="%s\\r%s\\l"];'
                             % (dotify(folder),
                                folder,
                                '\\l'.join(modules)))
            # end for
        # end def updateNodes

        for task in self._dotTasks:

            declareNodes(task['srcs'])
            declareNodes(task['dsts'])

            for src in task['srcs']:

                if (src not in nodes):
                    continue
                # end if

                for dst in task['dsts']:
                    if (dst not in nodes):
                        continue
                    # end if

                    lines.append('%s -> %s [label=" %s"];'
                                 % (dotify(src),
                                    dotify(dst),
                                    task['name']))
                # end for
            # end for
        # end for
        lines.append('}')

        with open(join(self._output, self._module + '.dot'), 'w') as fo:
            fo.write('\n'.join(lines))
        # end with

        call(['dot', '-Tpng', '-o', self._module + '.png', self._module + '.dot'],
             cwd = self._output)

    # end def processDot

    def _create_symlinks(self):
        '''
        Creates symlinks to the cached folders
        '''
        suffixes = dict()
        for _, values in self._folders.items():
            for key2, value2 in values.items():
                if key2 != 'suffix':
                    suffixes[value2] = values['suffix']
                    src = join(self._output, value2 + values['suffix'])
                    src_relative = value2 + values['suffix']
                    dst = join(self._output, value2)

                    # create or update the symlink
                    if((not isdir(dst) or islink(dst)) and isdir(src)):
                        if(islink(dst)):
                            remove(dst)
                        symlink(src_relative, dst)
    # end def _create_symlinks(self):

    def _updateDot(self, task, src, dst):
        '''
        @param task [in] (str)       name
        @param src  [in] (str, list) input folder(s)
        @param dst  [in] (str, list) output folder(s)
        '''
        self._dotTasks.append({'name': task,
                               'srcs': toList(src),
                               'dsts': toList(dst)})
    # end def _dot

    def _outfilenames(self):
        # a.out|liba.so --> c.out|libc.so
        if self._config.src2bin.LINK.binary.endswith(('a.out', 'liba.so')):
            cbin = self._config.src2bin.LINK.binary.replace('a.', 'c.')
            dbin = self._config.src2bin.LINK.binary.replace('a.', 'd.')
        else:
            cbin = self._config.src2bin.LINK.binary
            dbin = self._config.src2bin.LINK.binary
        #end if

        return cbin, dbin


# end class Actc

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
