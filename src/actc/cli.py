#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2014-2016 Nagravision S.A., Ghent University
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
''' @package  actc.cli

@brief   Command Line Interface

@author  Ronan Le Gallic, Jeroen Van Cleemput

@date    2014/10/06
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from argparse           import ArgumentParser
from argparse           import RawDescriptionHelpFormatter
from os.path            import basename
from os.path            import realpath
from os.path            import dirname
from os.path            import join
from random             import randint
import sys

from actc.core          import Actc
from actc.config        import Config
from actc.consts        import APP_BRIEF
from actc.consts        import APP_VERSION
from actc.consts        import CFG_NAME
from actc.consts        import CFG_JOBS

# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

class Main(Actc):
    '''
    Command Line Interface
    '''

    def __init__(self):
        '''
        Constructor
        '''

        parser = ArgumentParser(description     = APP_BRIEF,
                                formatter_class = RawDescriptionHelpFormatter,
                                epilog          = '''

ACTC v %s
''' % (APP_VERSION,))


        parser.add_argument('--version',
                            action  = 'version',
                            version = APP_VERSION)

        group = parser.add_argument_group('Build')

        group.add_argument('-j', '--jobs',
                           metavar = 'N',
                           type    = int,
                           default = CFG_JOBS,
                           help    = 'allow 1..N jobs at once [%(default)s]')

        group.add_argument('-d', '--debug',
                           action  = 'store_true',
                           default = False,
                           help    = 'print debugging informations')

        group.add_argument('-p', '--process',
                           action  = 'store_true',
                           default = False,
                           help    = 'generate processing graph')

        group.add_argument('-v', '--verbose',
                           action  = 'store_true',
                           default = False,
                           help    = 'print everything from a task')

        group.add_argument('-a', '--aid',
                           action='store_true',
                           default=False,
                           help='only generate the application id (AID) ')

        group = parser.add_argument_group('Configuration')

        group.add_argument('-f', '--file',
                           metavar = 'configName',
                           action  = 'store',
                           type    = str,
                           default = CFG_NAME,
                           nargs   = 1,
                           help    = 'read configName [%(default)s]')

        group.add_argument('-g', '--generate',
                           metavar = 'configName',
                           action  = 'store',
                           type    = str,
                           nargs   = '?',
                           const   = CFG_NAME,
                           help    = 'generate a template configuration file [%(const)s]')

        group.add_argument('-u', '--update',
                           metavar = 'configName',
                           action  = 'store',
                           type    = str,
                           nargs   = '?',
                           const   = CFG_NAME,
                           help    = 'update old configuration file [%(const)s]')


        parser.add_argument('cmd',
                            type    = str,
                            choices = ['build', 'clean'],
                            default = 'build',
                            nargs   = '?',
                            help    = 'ACTC commands [%(default)s]')

        args = parser.parse_args()

        #try:
        if args.generate is not None:
            Config().generate(args.generate)
            parser.exit(message="Configuration file '%s' created\n" % (basename(args.generate),))
            sys.exit(0)
        # end if

        if args.update is not None:
            Config().update(args.update)
            parser.exit(message="Configuration file '%s' updated\n" % (basename(args.update),))
            sys.exit(0)
        # end if

        super(Main, self).__init__(args.file[0] if isinstance(args.file, list) else args.file,
                                    debug=args.debug, verbose=args.verbose)

        if args.aid:
            print('%s' % self._aid);
            sys.exit(0)
        # end if

        if args.cmd == 'build':

            # Config version?
            if APP_VERSION != self._config._version:
                print('=== Warning: Incompatible configuration file version: %s ===' % (self._config._version))
                print('Update to version %s using \'%s -u %s\'' % (APP_VERSION,
                                                                    dirname(realpath(__file__)) + '.py',
                                                                    self._config._path))
                cont = raw_input("Continue? (y/N): ")
                if(cont != 'y'):
                    sys.exit(1)

            # Config server ip check
            if(not (self._config.SERVER.ip_address or self._config.SERVER.excluded)):
                print('=== Config error: SERVER.ip_address  empty ===')
                sys.exit(1)

            # Config bytecode diversity seed check
            if((not self._config.bin2bin.excluded) and
                not (str.isdigit(str(self._config.bin2bin.bytecode_diversity_seed))
                    or self._config.bin2bin.bytecode_diversity_seed in 'RANDOM')
                ):
                print('=== Config error: bin2bin.bytecode_diversity_seed  empty, should be an int or \'RANDOM\' ===')
                sys.exit(1)

            # Generate random seed
            if(self._config.bin2bin.bytecode_diversity_seed in 'RANDOM'):
                new_seed = randint(-2 ** 31, 2 ** 31 - 1)
                self._config._update(self._config, {'bin2bin' : {'bytecode_diversity_seed' : str(new_seed)}})
                print '=========================================================================='
                print '= WARNING, random bytecode diversity seed used                           ='
                print '= Generated new bytecode diversity seed: %25d       =' % new_seed
                print '=========================================================================='
            # end if

            with open(join(self._output, 'bytecode_diversity_seed.txt'), 'w') as fo:
                fo.write(self._config.bin2bin.bytecode_diversity_seed)
            # end with

            # Config code_mobility diversity seed check
            if((not self._config.bin2bin.excluded) and
                not (str.isdigit(str(self._config.bin2bin.code_mobility_diversity_seed))
                    or self._config.bin2bin.code_mobility_diversity_seed in 'RANDOM')
                ):
                print('=== Config error: bin2bin.code_mobility_diversity_seed  empty, should be an int or \'RANDOM\' ===')
                sys.exit(1)

            # Generate random seed
            if(self._config.bin2bin.code_mobility_diversity_seed in 'RANDOM'):
                new_seed = randint(-2 ** 31, 2 ** 31 - 1)
                self._config._update(self._config, {'bin2bin' : {'code_mobility_diversity_seed' : str(new_seed)}})
                print '=========================================================================='
                print '= WARNING, random code mobility diversity seed used                           ='
                print '= Generated new code mobility diversity seed: %25d       =' % new_seed
                print '=========================================================================='
            # end if

            with open(join(self._output, 'code_mobility_diversity_seed.txt'), 'w') as fo:
                fo.write(self._config.bin2bin.code_mobility_diversity_seed)
            # end with

            self.build(jobs=args.jobs)

            if (args.process):
                try:
                    self.processDot()
                except OSError:
                    parser.exit(message='actc.py: failed: generate process graph (missing "dot" tool?)\n',
                                status=1)
                # end try
            # end if

        elif args.cmd == 'clean':
            self.clean()

        else:
            parser.error('Unknown command: %s' % (args.cmd,))
        # end if

        #except Exception as err:  # pylint:disable=W0703
        #    parser.error(err.message)
        # end try

    # end def __init__


# end class Main

if __name__ == '__main__':
    Main()
# end if

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
