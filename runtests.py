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
#     * Neither the name of the Nagravision S.A., nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL NAGRAVISION S.A., BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------
''' @package runtests

@brief   ACTC tests

@author  Ronan Le Gallic

@date    2014/10/13
'''
# ------------------------------------------------------------------------------
# import
# ------------------------------------------------------------------------------
from argparse                   import ArgumentParser
from unittest.loader            import TestLoader
from unittest.runner            import TextTestRunner


# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

class Main(object):
    '''
    ACTC Test Runner
    '''

    def __init__(self):
        '''
        Constructor
        '''
        parser = ArgumentParser(epilog = 'ACTC Test Runner')

        parser.add_argument('-c', '--coverage',
                            action = 'store_true',
                            help   = 'activate code coverage measurement')

        args = parser.parse_args()

        if (args.coverage):
            from coverage import coverage

            cov = coverage(include = 'src/*',
                           omit    = '*/test/*.py')

            # actc.cli
            cov.exclude('Exception')
            cov.exclude('parser.error')

            # actc.dodo
            cov.exclude('NotImplementedError')

            cov.start()
        # end if

        TextTestRunner(verbosity = 2).run(TestLoader().discover('src'))

        if (args.coverage):
            cov.stop()
            cov.html_report(directory = 'coverage',
                            title     = 'ACTC code coverage')

            print('See coverage/index.html report')
        # end if
    # end def __init__
# end class Main

if __name__ == '__main__':
    Main()
# end if

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
