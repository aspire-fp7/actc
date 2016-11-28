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
''' @package  actc.config

@brief   Configuration

@author  Ronan Le Gallic, Jeroen Van Cleemput

@date    2014/10/07
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from json                       import loads
from os                         import chdir
from os                         import getenv
from os.path                    import abspath
from os.path                    import dirname
from os.path                    import isfile
from pprint                     import pformat
import re

from actc.consts                import APP_VERSION
from actc.tools.annotation      import READ_ANNOT
from actc.tools.data            import DATA_OBFUSCATE
from actc.tools.diablo          import DIABLO_EXTRACTOR
from actc.tools.diablo          import DIABLO_OBFUSCATOR
from actc.tools.diablo          import DIABLO_SELFPROFILING
from actc.tools.codesurfer      import CSURF
from actc.tools.compiler        import FRONTEND
from actc.tools.remote          import ATTESTATOR_SELECTOR
from actc.tools.remote          import ANTI_CLONING
from actc.tools.remote          import REACTION_UNIT
from actc.tools.remote          import DCL
from actc.tools.remote          import CFT
from actc.tools.splitter        import CLIENT_SERVER_SPLITTER
from actc.tools.wbc             import ANNOTATION_READER
from actc.tools.wbc             import CONFIG
from actc.tools.wbc             import CONVERT_PRAGMAS
from actc.tools.wbc             import WBC
from actc.tools.wbc             import WBTA
from actc.tools.wbc             import WBTA_LICENSE
from actc.tools.xtranslator     import XTRANSLATOR
from actc.tools.codeguard       import CODEGUARD
from actc.tools.renewability    import RENEWABILITY
from actc.tools.renewability    import RENEWABILITY_CREATE_SCRIPT
from actc.tools.renewability    import RENEWABILITY_POLICY_SCRIPT
from actc.tools.renewability    import RENEWABILITY_REVISION_DURATION
from actc.tools.renewability    import RENEWABILITY_TIMEOUT_MANDATORY

CODE_MOBILITY  = '/opt/code_mobility'
ACCL           = '/opt/ACCL'
ASCL           = '/opt/ASCL'
ANTI_DEBUGGING = '/opt/anti_debugging'

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

class AttrDict(dict):
    '''
    A dictionary with attribute-style access.

    It maps attribute access to the real dictionary.
    '''
    def __init__(self, mapping):
        '''
        Constructor

        @param mapping [in] (dict) key-value pairs
        '''
        super(AttrDict, self).__init__(mapping)
    # end def __init__

    def __setitem__(self, key, value):
        '''
        Implement assignment to self[key]

        @param key   [in] (str)  in self
        @param value [in] (item) to assign

        @return (item)
        '''
        return super(AttrDict, self).__setitem__(key, value)
    # end def __setitem__

    def __getitem__(self, key):
        '''
        Implement evaluation of self[key]

        @param key [in] (str)  in self

        @return (item)
        '''
        value = super(AttrDict, self).__getitem__(key)
        return AttrDict(value) if isinstance(value, dict) else value
    # end def __getitem__

    __getattr__ = __getitem__
    __setattr__ = __setitem__

# end class AttrDict


class Config(AttrDict):
    '''
    Configuration
    '''

    def __init__(self, path = None):
        '''
        Constructor

        @param path [in] (str) name
        '''
        # path = <path>: read/update config ignoring undefined steps --> excluded = True
        # path = None  : write default config with all steps         --> excluded = False
        super(Config, self).__init__(self._getDefaults(excluded = (path is not None)))

        self._path   = self._load(path, expand = True)
        self._indent = 8
    # end def __init__

    path = property(lambda self: self._path)

    def __repr__(self):
        '''
        Compute the "official" string representation of self

        @return (str)
        '''
        return pformat(dict(self))
    # end def __repr__

    @staticmethod
    def _getDefaults(excluded = False):
        '''
        Get default values

        @option excluded [in] (bool) step

        @return (dict)
        '''
        return {
          'platform' : '?',

          'tools':   {
              # libraries
              'third_party':            '/opt/3rd_party',
              # src2src
              'annotation_reader':      ANNOTATION_READER,
              'config':                 CONFIG,
              'wbta':                   WBTA,
              'wbta_license':           WBTA_LICENSE,
              'convert_pragmas':        CONVERT_PRAGMAS,
              'wbc':                    WBC,
              'read_annot':             READ_ANNOT,
              'data_obfuscate':         DATA_OBFUSCATE,
              'client_server_splitter': CLIENT_SERVER_SPLITTER,
              'csurf':                  CSURF,
              'codeguard':              CODEGUARD,
              'anti_cloning':           ANTI_CLONING,
              'attestator_selector':    ATTESTATOR_SELECTOR,
              'reaction_unit':          REACTION_UNIT,
              'dcl':                    DCL,
              'cft':                    CFT,
              # src2bin
              'frontend':               FRONTEND,
              # bin2bin
              'extractor':              DIABLO_EXTRACTOR,
              'xtranslator':            XTRANSLATOR,
              'code_mobility':          CODE_MOBILITY,
              'accl':                   ACCL,
              'ascl':                   ASCL,
              'anti_debugging':         ANTI_DEBUGGING,
              'obfuscator':             DIABLO_OBFUSCATOR,
              'obfuscator_sp':          DIABLO_SELFPROFILING,
              'renewability':           RENEWABILITY,
              },

          'src2src': {
              'excluded': excluded,

              'SLP01': {
                  'excluded':               excluded,
                  'traverse':               False,
                  'annotations_patch':      '',
                  'external_annotations':   '',
                  'source':                 [],
                  },

              'SLP02': {
                  'excluded': excluded,
                  },

              'SLP03': {
                  'excluded'            : excluded,
                  'traverse'            : False,
                  'renewability_script' : True,
                  'seed'                : 'none',

                  '_01': {
                      'excluded': excluded,
                      },

                  '_02': {
                      'excluded': excluded,
                      },

                  '_03': {
                      'excluded': excluded,
                      },

                  '_04': {
                      'excluded': excluded,
                      },

                  '_05': {
                      'excluded': excluded,
                      'options' : ["-size 2000MB"],
                      },
                  },

              # annotation_extractor
              'SLP04': {
                  'excluded': excluded,
                  'options' : [],
                  'external': [],
                  },

              'SLP05': {
                  'excluded': excluded,
                  'traverse': False,

                  # source code analysis
                  '_01': {
                      'excluded': excluded,
                      'options' : [],
                      },
                  # data_obfuscator
                  '_02': {
                      'excluded': excluded,
                      'options' : [],
                      },
                  },

              # client server code splitting
              'SLP06': {
                  'excluded': excluded,
                  'traverse': False,

                  # Process
                  '_01': {
                      'excluded': excluded,
                      'options' : [],
                      },

                  # Csurf
                  '_02': {
                      'excluded': excluded,
                      },

                  # Code_transformation
                  '_03': {
                      'excluded': excluded,
                      },
                  },

              # code guard
              'SLP08': {
                  'excluded': excluded,
                  'traverse': False,
                  'options' : [],
                  },

              # remote attestation
              'SLP07': {
                  'excluded': excluded,
                  'options' : [],
                  },

              # anti-cloning
              'SLP09': {
                  'excluded': excluded,
                  'traverse': False,
                  'options' : [],
                  },

              # reaction unit
              'SLP10': {
                  'excluded': excluded,
                  'traverse': False,
                  'options' : [],
                  },

              # diversified crypto library
              'SLP11': {
                  'excluded': excluded,
                  'traverse': True,
                  'options' : [],
                  },

              # control flow tagging
              'SLP12': {
                  'excluded': excluded,
                  'traverse': False,
                  'options' : [],
                  },
              },

          'src2bin': {
              'excluded': excluded,
              'options' : [],

              'PREPROCESS': {
                  'options': [],
                  },

              'COMPILE' : {
                  'options'    : [],
                  'options_c'  : [],
                  'options_cpp': [],
                  },

              'COMPILE_ACCL' : {
                  'protocol' : '',
                  'endpoint' : '',
                  'port'     : '',
                  'file_path': '',
                  },

              'LINK'    : {
                  'options' : [],
                  'binary'  : '',
                  },
              },

          'bin2bin': {
              'excluded': excluded,
              'bytecode_diversity_seed'      : 0,  # should be an int or 'RANDOM'
              'code_mobility_diversity_seed' : 0,  # should be an int or 'RANDOM'

              #vanilla self-profiling
              'BLP00' : {
                  'excluded' : excluded,

                  #generate vanilla self-profiling binary
                  '_01' : {
                      'excluded' : excluded,
                      'options'  : [],
                      },
                  #collect execution profile on target board
                  '_02' : {
                      'excluded'    : excluded,
                      'script'      : '',
                      },
                  #recompile using execution profile and calculate dynamic metrics
                  '_03' : {
                      'excluded'    : excluded,
                      'options'  : [],
                      },
                  },

              # diablo-extractor
              'BLP01': {
                  'excluded': excluded,
                  'traverse': True,
                  'options' : []
                  },

              # x-translator
              'BLP02': {
                  'excluded': True,
                  'options' : []
                  },

              'BLP03': {
                  'excluded': True,
                  'options' : []
                  },

              # diablo-obfuscator
              'BLP04': {
                  'excluded'        : excluded,
                  'options'         : [],
                  'self-profiling'  : False,
                  'runtime_profiles': False,
                  'anti_debugging'  : True,
                  'obfuscations'    : True,
                  'call_stack_check': True,
                  'softvm'          : True,
                  'code_mobility'   : True,
                  },

              # Generate dynamic metrics using diablo obfuscator
              'BLP04_DYN': {
                  'excluded': excluded,
                  # collect execution profile on target board
                  '_01' : {
                      'excluded'    : excluded,
                      'options'     : [],
                      'script'      : ''
                      },
                  # recompile using execution profile and calculate dynamic metrics
                  '_02' : {
                      'excluded'    : excluded,
                      'options'     : []
                      },
                  },
              },

          'SERVER': {
              'excluded' : False,
              'ip_address': '',

              # code splitting
              'P10'   : {'script' : ''},
              # code mobility
              'P20'   : {'script' : '/opt/code_mobility/deploy_application.sh"'},
              # remote attestation
              'P80'   : {'script' : '/opt/RA/deploy/deploy.sh'},
              # renewability
              'RENEWABILITY' : {
                  "excluded"              : False,
                  "new_application_script": RENEWABILITY_CREATE_SCRIPT,
                  "set_policy_script"     : RENEWABILITY_POLICY_SCRIPT,
                  "revision_duration"     : RENEWABILITY_REVISION_DURATION,
                  "timeout_mandatory"     : RENEWABILITY_TIMEOUT_MANDATORY,
                  },
              },

          'POST' : {
              'brief': '',
              'args' : '',
              },

          'METRICS' : {
              'excluded': False,

              'runcode' : {
                  'excluded' : False,
                  'script' : '',
                  },

              'files' : {
                      'BC02_SP'         : [ '*.stat_complexity_info' ],
                      'BC02_SP/profiles': [ '*.plaintext' ],
                      'BC02_DYN'        : [ '*.dynamic_complexity_info' ],
                      'BC05'            : [ '*.stat_complexity_info', '*.stat_regions_complexity_info' ],
                      'BC05/profiles'   : [ '*.plaintext' ],
                      'BC05_DYN'        : [ '*.dynamic_complexity_info' ],
                      },
              },

          }
    # end def _getDefaults

    _RE_COMMENT = re.compile(r'^\s*(//|#)')
    _RE_ENV_VAR = re.compile(r'\${(.+?)}')

    def _load(self, path, expand = False):
        '''
        Load configuration file

        @param  path   [in] (str) name
        @option expand [in] (bool) environment variables

        @return (str) abspath
        '''
        if (path is None):
            return
        # end if

        path = abspath(path)

        if (not isfile(path)):
            raise ValueError('file not found: %s' % (path,))
        # end if

        with open(path, 'r') as fo:
            lines = fo.readlines()
        # end with

        #Load configuration file version
        self._version = lines[0].split()[2]

        # Skip comments: // comment
        # Expand environment variables: ${VARIABLE} --> VALUE
        lines = [self._RE_ENV_VAR.sub(lambda mo: getenv(mo.group(1), '') if expand else mo.group(0), line)
                 for line in lines
                 if not self._RE_COMMENT.match(line)]

        # Deserialize data
        self._update(self, loads(''.join(lines)))


        # Platform?
        if self.platform not in ('linux', 'android'):
            print('=== Warning: undefined platform: %-22s ===' % (self.platform))
            print('===          "linux" will be used by default            ===')
            print('===          please udapte your configuration file      ===')

            self._update(self, {'platform' : 'linux'})
        # end if

        # Binary?
        if (not self.src2bin.LINK.binary):
            for option in ' '.join(self.src2bin.LINK.options).split():
                if (option == '-shared'):
                    self._update(self, {'src2bin' : {'LINK' : { 'binary' : 'liba.so'}}})
                    break
                # end if
            else:
                self._update(self, {'src2bin' : {'LINK' : { 'binary' : 'a.out'}}})
            # end for
        # end if

        # Working path is config path
        chdir(dirname(path))

        return path
    # end def _load


    @staticmethod
    def _update(current, other):
        '''
        Recursively update dictionnary

        @param current [in] (dict) values
        @param other   [in] (dict) values

        @return (dict)
        '''
        for key, value in other.iteritems():

            if key not in current:
                print('Warning: Deprecated parameter: %s' % (key,))
                continue
            # end if

            if isinstance(value, dict):
                current[key] = Config._update(current[key], value)
            else:
                current[key] = value
            # end if

        # end for

        return current
    # end def _update

    def _item2json(self, item, sort = False):
        '''
        Convert item into json

        @param  item [in] (bool, list, str) to convert
        @option sort [in] (bool)            sorted item list

        @return (str)
        '''
        if isinstance(item, bool):
            return 'true' if item else 'false'
        # end if

        if isinstance(item, list):
            separator = ',\n' + ' ' * self._indent

            item = sorted(item) if sort else item

            return '[%s]' % (separator.join([self._item2json(i)
                                             for i in item]),)
        # end if

        if isinstance(item, dict):
            separator = ',\n' + ' ' * self._indent

            return '{%s}' % (separator.join(['%s: %s' % (self._item2json(k),
                                                        self._item2json(item[k]))
                                             for k in sorted(item.keys())]),)
        # end if


        return '"%s"' % (str(item))
    # end def _item2json


    def generate(self, path):
        '''
        Generate Configuration file

        @param path [in] (str) name
        '''
        lines = list()

        lines.append('''\
// ACTC %(VERSION)s
//
// Note:
// - "excluded": true/false [false]
//   if true, step is excluded from toolchain --> no output folder is created
//   use this field to start toolchain from any step
//
// - "traverse": true/false [false]
//   if true, input files are copied to output folder without any change
//
{
''' % {'VERSION': APP_VERSION})

        # pylint:disable=W0212

        # ----------------------------------------------------------------------
        self._indent = 32

        lines.append('''\
  // Target platforms:
  // - linux [default]
  // - android
  "platform" :                %(PLATFORM)s,
''' % {'PLATFORM' : self._item2json(self.platform)})

        lines.append('''\
  // Tools
  "tools": {
    // libraries
    "third_party":            %(THIRD_PARTY)s,
    // src2src
    "annotation_reader":      %(ANNOTATION_READER)s,
    "config":                 %(CONFIG)s,
    "wbta":                   %(WBTA)s,
    "convert_pragmas":        %(CONVERT_PRAGMAS)s,
    "wbc":                    %(WBC)s,
    "read_annot":             %(READ_ANNOT)s,
    "data_obfuscate":         %(DATA_OBFUSCATE)s,
    "client_server_splitter": %(CLIENT_SERVER_SPLITTER)s,
    "csurf":                  %(CSURF)s,
    "codeguard":              %(CODEGUARD)s,
    "anti_cloning":           %(ANTI_CLONING)s,
    "attestator_selector":    %(ATTESTATOR_SELECTOR)s,
    "reaction_unit":          %(REACTION_UNIT)s,
    "dcl":                    %(DCL)s,
    "cft":                    %(CFT)s,
    // src2bin
    "frontend":               %(FRONTEND)s,
    // bin2bin
    "extractor":              %(EXTRACTOR)s,
    "xtranslator":            %(XTRANSLATOR)s,
    "code_mobility":          %(CODE_MOBILITY)s,
    "accl":                   %(ACCL)s,
    "ascl":                   %(ASCL)s,
    "anti_debugging":         %(ANTI_DEBUGGING)s,
    "obfuscator":             %(OBFUSCATOR)s,
    "obfuscator_sp":          %(OBFUSCATOR_SP)s,
    "renewability":           %(RENEWABILITY)s
  },
''' % {'THIRD_PARTY':            self._item2json(self.tools.third_party),
       'ANNOTATION_READER':      self._item2json(self.tools.annotation_reader),
       'CONFIG':                 self._item2json(self.tools.config),
       'WBTA':                   self._item2json(self.tools.wbta),
       'CONVERT_PRAGMAS':        self._item2json(self.tools.convert_pragmas),
       'WBC':                    self._item2json(self.tools.wbc),
       'READ_ANNOT':             self._item2json(self.tools.read_annot),
       'DATA_OBFUSCATE':         self._item2json(self.tools.data_obfuscate),
       'CLIENT_SERVER_SPLITTER': self._item2json(self.tools.client_server_splitter),
       'CSURF':                  self._item2json(self.tools.csurf),
       'CODEGUARD':              self._item2json(self.tools.codeguard),
       'ANTI_CLONING':           self._item2json(self.tools.anti_cloning),
       'ATTESTATOR_SELECTOR':    self._item2json(self.tools.attestator_selector),
       'REACTION_UNIT':          self._item2json(self.tools.reaction_unit),
       'DCL':                    self._item2json(self.tools.dcl),
       'CFT':                    self._item2json(self.tools.cft),
       'FRONTEND':               self._item2json(self.tools.frontend),
       'EXTRACTOR':              self._item2json(self.tools.extractor),
       'CODE_MOBILITY':          self._item2json(self.tools.code_mobility),
       'ACCL':                   self._item2json(self.tools.accl),
       'ASCL':                   self._item2json(self.tools.ascl),
       'ANTI_DEBUGGING':         self._item2json(self.tools.anti_debugging),
       'XTRANSLATOR':            self._item2json(self.tools.xtranslator),
       'OBFUSCATOR':             self._item2json(self.tools.obfuscator),
       'OBFUSCATOR_SP':          self._item2json(self.tools.obfuscator_sp),
       'RENEWABILITY':          self._item2json(self.tools.renewability),
       })

        # ----------------------------------------------------------------------
        self._indent = 19

        lines.append('''\
  // Source-level Tool chain
  "src2src": {
    "excluded": %(EXCLUDED)s,
''' % {'EXCLUDED': self._item2json(self.src2src.excluded),
       })

        lines.append('''\
    // Source code annotation
    "SLP01": {
      "excluded":               %(EXCLUDED)s,
      "traverse":               %(TRAVERSE)s,
      "annotations_patch":      %(ANNOTATIONS_PATCH)s,
      "external_annotations":   %(EXTERNAL_ANNOTATIONS)s,
      "source"  :               %(SOURCE)s
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP01.excluded),
       'TRAVERSE': self._item2json(self.src2src.SLP01.traverse),
       'ANNOTATIONS_PATCH': self._item2json(self.src2src.SLP01.annotations_patch),
       'EXTERNAL_ANNOTATIONS': self._item2json(self.src2src.SLP01.external_annotations),
       'SOURCE'  : self._item2json(self.src2src.SLP01.source, sort = True),
       })

        lines.append('''\
    // white-box crypto
    "SLP03": {
      "excluded": %(EXCLUDED)s,
      "traverse": %(TRAVERSE)s,
      "renewability_script": %(SCRIPT)s,
      // WBC seed (random, aid, none)
      "seed": %(SEED)s,
 ''' % {'EXCLUDED': self._item2json(self.src2src.SLP03.excluded),
        'TRAVERSE': self._item2json(self.src2src.SLP03.traverse),
        'SCRIPT': self._item2json(self.src2src.SLP03.renewability_script),
        'SEED'  : self._item2json(self.src2src.SLP03.seed),
        })

        lines.append('''\
      // WBC annotation extraction tool
      "_01": {
        "excluded": %(EXCLUDED)s
      },
 ''' % {'EXCLUDED': self._item2json(self.src2src.SLP03._01.excluded),
        })

        lines.append('''\
      // White-Box Tool python
      "_02": {
        "excluded": %(EXCLUDED)s
      },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP03._02.excluded),
       })

        lines.append('''\
      // WBC header inclusion
      "_03": {
        "excluded": %(EXCLUDED)s
      },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP03._03.excluded),
       })

        lines.append('''\
      // preprocessor
      "_04": {
        "excluded": %(EXCLUDED)s
      },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP03._04.excluded),
       })

        lines.append('''\
      // WBC source rewriting tool
      "_05": {
        "excluded": %(EXCLUDED)s,
        "options":  %(OPTIONS)s
      }
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP03._05.excluded),
       'OPTIONS':  self._item2json(self.src2src.SLP03._05.options),
       })

        lines.append('''\
    // preprocessor
    "SLP02": {
      "excluded": %(EXCLUDED)s
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP02.excluded),
       })

        lines.append('''\
    // data hiding
    "SLP05": {
      "excluded": %(EXCLUDED)s,
      "traverse": %(TRAVERSE)s,
''' % {'EXCLUDED': self._item2json(self.src2src.SLP05.excluded),
       'TRAVERSE': self._item2json(self.src2src.SLP05.traverse),
       })

        lines.append('''\
      // source code analysis
      "_01": {
        "excluded": %(EXCLUDED)s,
        "options" : %(OPTIONS)s
      },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP05._01.excluded),
       'OPTIONS' : self._item2json(self.src2src.SLP05._01.options, sort = True),
       })

        lines.append('''\
      // data obfuscation
      "_02": {
        "excluded": %(EXCLUDED)s,
        "options" : %(OPTIONS)s
      }
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP05._02.excluded),
       'OPTIONS' : self._item2json(self.src2src.SLP05._02.options, sort = True),
       })

        lines.append('''\
    // client server clode splitting
    "SLP06": {
      "excluded": %(EXCLUDED)s,
      "traverse": %(TRAVERSE)s,
    ''' % {'EXCLUDED': self._item2json(self.src2src.SLP06.excluded),
           'TRAVERSE': self._item2json(self.src2src.SLP06.traverse),
           })

        lines.append('''\
      // Process
      "_01": {
        "excluded": %(EXCLUDED)s,
        "options" : %(OPTIONS)s
      },
    ''' % {'EXCLUDED': self._item2json(self.src2src.SLP06._01.excluded),
           'OPTIONS' : self._item2json(self.src2src.SLP06._01.options, sort = True),
           })

        lines.append('''\
      // CSurf
      "_02": {
        "excluded": %(EXCLUDED)s
      },
    ''' % {'EXCLUDED': self._item2json(self.src2src.SLP06._02.excluded),
           })

        lines.append('''\
      // Code transformation
      "_03": {
        "excluded": %(EXCLUDED)s
      }
    },
    ''' % {'EXCLUDED': self._item2json(self.src2src.SLP06._03.excluded),
           })

        lines.append('''\
    // annotation extraction + external annotation file(s)
    "SLP04": {
      "excluded": %(EXCLUDED)s,
      "options" : %(OPTIONS)s,
      "external": %(EXTERNAL)s
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP04.excluded),
       'OPTIONS' : self._item2json(self.src2src.SLP04.options,  sort = True),
       'EXTERNAL': self._item2json(self.src2src.SLP04.external, sort = True),
       })

        lines.append('''\
    // code guard
    "SLP08": {
      "excluded": %(EXCLUDED)s,
      "traverse": %(TRAVERSE)s,
      "options" : %(OPTIONS)s
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP08.excluded),
       'TRAVERSE': self._item2json(self.src2src.SLP08.traverse),
       'OPTIONS' : self._item2json(self.src2src.SLP08.options, sort = True)
       })

        lines.append('''\
    // anti-cloning
    "SLP09": {
      "excluded": %(EXCLUDED)s,
      "traverse": %(TRAVERSE)s,
      "options" : %(OPTIONS)s
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP09.excluded),
       'TRAVERSE': self._item2json(self.src2src.SLP09.traverse),
       'OPTIONS' : self._item2json(self.src2src.SLP09.options, sort = True)
       })

        lines.append('''\
    // remote attestation
    "SLP07": {
      "excluded": %(EXCLUDED)s,
      "options" : %(OPTIONS)s
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP07.excluded),
       'OPTIONS' : self._item2json(self.src2src.SLP07.options, sort = True)
       })

        lines.append('''\
    // reaction unit
    "SLP10": {
      "excluded": %(EXCLUDED)s,
      "traverse": %(TRAVERSE)s,
      "options" : %(OPTIONS)s
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP10.excluded),
       'TRAVERSE': self._item2json(self.src2src.SLP10.traverse),
       'OPTIONS' : self._item2json(self.src2src.SLP10.options, sort=True)
       })

        lines.append('''\
    // diversified crypto library
    // only applicable for ANDROID platform
    "SLP11": {
      "excluded": %(EXCLUDED)s,
      "traverse": %(TRAVERSE)s,
      "options" : %(OPTIONS)s
    },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP11.excluded),
       'TRAVERSE': self._item2json(self.src2src.SLP11.traverse),
       'OPTIONS' : self._item2json(self.src2src.SLP11.options, sort=True)
       })

        lines.append('''\
    // control flow tagging
    "SLP12": {
      "excluded": %(EXCLUDED)s,
      "traverse": %(TRAVERSE)s,
      "options" : %(OPTIONS)s
    }
  },
''' % {'EXCLUDED': self._item2json(self.src2src.SLP12.excluded),
       'TRAVERSE': self._item2json(self.src2src.SLP12.traverse),
       'OPTIONS' : self._item2json(self.src2src.SLP12.options, sort=True)
       })

        # ----------------------------------------------------------------------
        self._indent = 22

        lines.append('''\
  // Assembler, Compiler, Linker
  "src2bin": {
  "excluded": %(EXCLUDED)s,
    // Common options for all tools
    "options"      : %(OPTIONS)s,
''' % {'EXCLUDED': self._item2json(self.src2bin.excluded),
       'OPTIONS' : self._item2json(self.src2bin.options, sort = True),
       })

        lines.append('''\
    "PREPROCESS": {
      // -I <dir>
      // -isystem <dir>
      // -include <file>
      // -D<macro[=defn]>
      "options"    : %(OPTIONS)s
    },
''' % {'OPTIONS' : self._item2json(self.src2bin.PREPROCESS.options, sort = True),
       })

        lines.append('''\
    // .c, .cpp
    "COMPILE": {
      "options"    : %(OPTIONS)s,
      "options_c"  : %(OPTIONS_C)s,
      "options_cpp": %(OPTIONS_CPP)s
    },
''' % {'OPTIONS'    : self._item2json(self.src2bin.COMPILE.options, sort = True),
       'OPTIONS_C'  : self._item2json(self.src2bin.COMPILE.options_c, sort = True),
       'OPTIONS_CPP': self._item2json(self.src2bin.COMPILE.options_cpp, sort = True),
       })

        lines.append('''\
    // accl.c
    "COMPILE_ACCL": {
      "protocol"    : %(PROTOCOL)s,
      "endpoint"    : %(ENDPOINT)s,
      "port"        : %(PORT)s,
      "file_path"   : %(PATH)s
    },
''' % {'PROTOCOL'    : self._item2json(self.src2bin.COMPILE_ACCL.protocol),
       'ENDPOINT'  : self._item2json(self.src2bin.COMPILE_ACCL.endpoint),
       'PORT': self._item2json(self.src2bin.COMPILE_ACCL.port),
       'PATH': self._item2json(self.src2bin.COMPILE_ACCL.file_path),
       })

        lines.append('''\
    // Linker
    "LINK": {
      "options"    : %(OPTIONS)s,
      // basename of linked file
      //   if empty, default value computed from options:
      //   "liba.so" if "-shared" else "a.out"
      "binary"     : %(BINARY)s
    }
  },
''' % {'OPTIONS' : self._item2json(self.src2bin.LINK.options, sort = True),
       'BINARY'  : self._item2json(self.src2bin.LINK.binary
                                   if self.src2bin.LINK.binary not in ('a.out', 'liba.so')
                                   else ''),
       })

        # ----------------------------------------------------------------------
        self._indent = 19

        lines.append('''\
  // Binary Rewriting Tool Chain
  "bin2bin": {
    "excluded": %(EXCLUDED)s,
''' % {'EXCLUDED': self._item2json(self.bin2bin.excluded),
       })

        lines.append('''\
    // bytecode diversity seed, integer or RANDOM
    "bytecode_diversity_seed"     : %(VM_SEED)s,
    "code_mobility_diversity_seed": %(CM_SEED)s,
''' % {'VM_SEED': self._item2json(self.bin2bin.bytecode_diversity_seed),
       'CM_SEED': self._item2json(self.bin2bin.code_mobility_diversity_seed),
       })

        lines.append('''\
    // vanilla self-profiling
    "BLP00": {
      "excluded": %(EXCLUDED)s,
    
''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP00.excluded)
       })

        lines.append('''\
      // generate vanilla self-profiling binary
      "_01": {
        "excluded": %(EXCLUDED)s,
        "options" : %(OPTIONS)s
      },
    ''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP00._01.excluded),
           'OPTIONS' : self._item2json(self.bin2bin.BLP00._01.options, sort = True),
           })

        lines.append('''\
      // collect execution profile on target board
      "_02": {
        "excluded": %(EXCLUDED)s,
        "script" : %(SCRIPT)s
      },
    ''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP00._02.excluded),
           'SCRIPT'  : self._item2json(self.bin2bin.BLP00._02.script),
           })

        lines.append('''\
      // recompile using execution profile and calculate dynamic metrics
      "_03": {
        "excluded": %(EXCLUDED)s,
        "options" : %(OPTIONS)s
      }
    },
    ''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP00._03.excluded),
           'OPTIONS' : self._item2json(self.bin2bin.BLP00._03.options, sort = True),
           })

        lines.append('''\
    // Native Code Extraction
    "BLP01": {
      "excluded": %(EXCLUDED)s,
      "traverse": %(TRAVERSE)s,
      "options" : %(OPTIONS)s
    },
''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP01.excluded),
       'TRAVERSE': self._item2json(self.bin2bin.BLP01.traverse),
       'OPTIONS' : self._item2json(self.bin2bin.BLP01.options, sort = True),
       })

        lines.append('''\
    // Bytecode Generation
    "BLP02": {
      "excluded": %(EXCLUDED)s,
      "options" : %(OPTIONS)s
    },
''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP02.excluded),
       'OPTIONS' : self._item2json(self.bin2bin.BLP02.options, sort = True),
       })

        lines.append('''\
    // Code Integration
    "BLP03": {
      "excluded": %(EXCLUDED)s,
      "options" : %(OPTIONS)s
    },
''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP03.excluded),
       'OPTIONS' : self._item2json(self.bin2bin.BLP03.options, sort = True),
       })

        lines.append('''\
    // Binary Code Control Flow Obfuscation
    "BLP04": {
      "excluded"        : %(EXCLUDED)s,
      "options"         : %(OPTIONS)s,
      "self-profiling"  : %(SP)s,
      "runtime_profiles": %(RP)s,
      "anti_debugging"  : %(AD)s,
      "obfuscations"    : %(OBF)s,
      "call_stack_check": %(CS)s,
      "softvm"          : %(SV)s,
      "code_mobility"   : %(CM)s
    },
''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP04.excluded),
       'OPTIONS' : self._item2json(self.bin2bin.BLP04.options, sort = True),
       'SP'      : self._item2json(self.bin2bin.BLP04['self-profiling']),
       'RP'      : self._item2json(self.bin2bin.BLP04['runtime_profiles']),
       'AD'      : self._item2json(self.bin2bin.BLP04['anti_debugging']),
       'OBF'     : self._item2json(self.bin2bin.BLP04['obfuscations']),
       'CS'      : self._item2json(self.bin2bin.BLP04['call_stack_check']),
       'SV'      : self._item2json(self.bin2bin.BLP04['softvm']),
       'CM'      : self._item2json(self.bin2bin.BLP04['code_mobility']),
       })

        lines.append('''\
    // Generate dynamic metrics using diablo obfuscator
    "BLP04_DYN": {
      "excluded": %(EXCLUDED)s,
''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP04_DYN.excluded),
       })
        lines.append('''\
      // collect execution profile on target board
      "_01": {
        "excluded": %(EXCLUDED)s,
        "options" : %(OPTIONS)s,
        "script" : %(SCRIPT)s
      },
    ''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP04_DYN._01.excluded),
           'OPTIONS' : self._item2json(self.bin2bin.BLP04_DYN._01.options, sort = True),
           'SCRIPT'  : self._item2json(self.bin2bin.BLP04_DYN._01.script),
           })

        lines.append('''\
      // recompile using execution profile and calculate dynamic metrics
      "_02": {
        "excluded": %(EXCLUDED)s,
        "options" : %(OPTIONS)s
      }
    }
  },
    ''' % {'EXCLUDED': self._item2json(self.bin2bin.BLP04_DYN._02.excluded),
           'OPTIONS' : self._item2json(self.bin2bin.BLP04_DYN._02.options, sort=True),
           })

        # ----------------------------------------------------------------------
        self._indent = 27

        lines.append('''\
  // Server side management
  "SERVER": {
    "excluded"   : %(EXCLUDED)s,
    "ip_address" : %(IP_ADDRESS)s,
''' % {'EXCLUDED': self._item2json(self.SERVER.excluded),
       'IP_ADDRESS': self._item2json(self.SERVER.ip_address)})

        lines.append('''\
    // Code Splitting
    "P10": {
      "script": %(SCRIPT)s},
''' % {'SCRIPT': self._item2json(self.SERVER.P10.script)})

        lines.append('''\
    // Code Mobility
    "P20": {
      "script": %(SCRIPT)s},
''' % {'SCRIPT': self._item2json(self.SERVER.P20.script)})

        lines.append('''\
    // Remote Attestation
    "P80": {
      "script": %(SCRIPT)s},
''' % {'SCRIPT': self._item2json(self.SERVER.P80.script)})

        lines.append('''\
    // Renewability
    "RENEWABILITY": {
      "excluded"              : %(EXCLUDED)s,
      "new_application_script": %(APP_SCRIPT)s,
      "set_policy_script"     : %(POL_SCRIPT)s,
      "revision_duration"     : %(DURATION)s,
      "timeout_mandatory"     : %(MANDATORY)s
    }
  },
''' % {'EXCLUDED': self._item2json(self.SERVER.RENEWABILITY.excluded),
       'APP_SCRIPT': self._item2json(self.SERVER.RENEWABILITY.new_application_script),
       'POL_SCRIPT': self._item2json(self.SERVER.RENEWABILITY.set_policy_script),
       'DURATION': self._item2json(self.SERVER.RENEWABILITY.revision_duration),
       'MANDATORY': self._item2json(self.SERVER.RENEWABILITY.timeout_mandatory)})

        lines.append('''\
  // Metric collection
  "METRICS": {
    "excluded" : %(EXCLUDED)s,
    "files"    : {
        "BC02_SP"          : %(BC02_SP)s,
        "BC02_SP/profiles" : %(BC02_SP/profiles)s,
        "BC02_DYN"         : %(BC02_DYN)s,
        "BC05"             : %(BC05)s,
        "BC05/profiles"    : %(BC05/profiles)s,
        "BC05_DYN"         : %(BC05_DYN)s
    }
  },
''' % {'EXCLUDED'           : self._item2json(self.METRICS.excluded),
       'BC02_SP'            : self._item2json(self.METRICS.files.BC02_SP),
       'BC02_SP/profiles'   : self._item2json(self.METRICS.files['BC02_SP/profiles']),
       'BC02_DYN'           : self._item2json(self.METRICS.files.BC02_DYN),
       'BC05'               : self._item2json(self.METRICS.files.BC05),
       'BC05/profiles'      : self._item2json(self.METRICS.files['BC05/profiles']),
       'BC05_DYN'           : self._item2json(self.METRICS.files.BC05_DYN),
       })

        lines.append('''\
  // Post-processing
  "POST": {
    // Short description in ACTC trace
    "brief": %(BRIEF)s,
    // Command line arguments
    "args" : %(ARGS)s
  }
}
''' % {'BRIEF': self._item2json(self.POST.brief),
       'ARGS' : self._item2json(self.POST.args),
       })
        with open(path, 'w') as fo:
            fo.write('\n'.join(lines))
        # end with

    # end def generate

    def update(self, path):
        '''
        Update old configuration

        @param path [in] (str) name
        '''
        self._load(path)
        self.generate(path)
    # end def update

# end class Config

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
