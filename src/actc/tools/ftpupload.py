#!/usr/bin/env python
# Copyright (c) 2015 Gemalto S.A.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Gemalto S.A., nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL GEMALTO S.A. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
''' @package  actc.ftpupload

'''

from ftplib             import FTP
from os                 import listdir
from os                 import name
from os.path            import isfile
from os.path            import sep

class FTPUpload(object):
    '''
    Uploads files on an FTP server.
    '''

    def __init__(self, config):
        '''
        Constructor
        '''
        self._config = config
    # end def __init__

    def issue(self, errorMessage):
        '''
        ?
        '''
        print("\n========================================================================")
        print("===   An error occurred while trying to upload files on FTP server   ===")
        print(errorMessage)
        print("========================================================================")
    # end def issue

    def changeWorkingDirectory(self, server, applicationID):
        '''
        ?
        '''
        try:
            server.cwd(str(applicationID))
        except:
            try:
                server.mkd(str(applicationID))
                server.cwd(str(applicationID))
            except:
                return False
            # end try
        # end try
        return True
    # end def changeWorkingDirectory

    def listFilesInDirectory(self, localPath):
        '''
        ?
        '''
        resultList = []
        try:
            #resultList = [ aFile for aFile in listdir(localPath) if isfile(sep.join((localPath, str(file)))) ]
            for file in listdir(localPath):
                if isfile(sep.join((localPath, str(file)))):
                    resultList.append(file)
                # end if
            # end for
            return resultList
        except:
            pass
        # end try
        return resultList
    # end listFilesInDirectory

    def filteredListFilesInDirectory(self, localPath, prefix):
        '''
        ?
        '''
        resultList = []
        try:
            for file in listdir(localPath):
                if file.startswith(prefix) and isfile(sep.join((localPath, str(file)))):
                    resultList.append(file)
                # end if
            # end for
            return resultList
        except:
            return resultList
        # end try
    # end def filteredListFilesInDirectory

    def uploadFiles(self, server, remoteDirectory, buildPath, localDirectory, prefix=''):
        '''
        ?
        '''
        localPath =  sep.join((buildPath,localDirectory))
        if len(prefix) != 0:
            fileList = self.filteredListFilesInDirectory(localPath, prefix)
            if not fileList:
                self.issue("No file to upload found in {0} with prefix {1} \nwhile specified in the configuration file.".format(localPath, prefix))
                return
            # end if
        else:
            fileList = self.listFilesInDirectory(localPath)
            if not fileList:
                self.issue("No file to upload found in {0} while specified \nin the configuration file.".format(localPath))
                return
            # end if
        # end if

        #copying
        # cd protectionId directory
        try:
            server.cwd(str(remoteDirectory))
        except:
            server.mkd(str(remoteDirectory))
            server.cwd(str(remoteDirectory))
        # end try

        for aFile in fileList:
            inputFile = open(sep.join((localPath, aFile)), 'rb')
            status = server.storbinary('STOR '+ aFile, inputFile)
            inputFile.close()
        # end for

        # cd ..
        server.cwd("..")
    # end def uploadFiles

    def upload(self, buildPath, module):
        '''
        ?
        '''

        # Assuming in uploadFiles method that build machine and server are running the same os...
        # with the same path separator.
        # Typically, it won't work if build machine is running windows because most
        # probably the server will run linux, let's quit.
        if name == 'nt':
            self.issue("Build machine is windows, while some flavour of Linux expected. The files upload step cannot work as-is. \n Contact the support for adaptation.")
            return

        try:
            newConnection = FTP(self._config.FTP_server_address, self._config.user, self._config.password)
        except:
            self.issue("Cannot establish the connection with the FTP server. \n       Check the server address, the user and the password. \n       server address= {0}, user= {1}, pw= {2}\n       Port is the default 21 value".format(self._config.FTP_server_address, self._config.user, self._config.password))
            return
        # end try

        if not self.changeWorkingDirectory(newConnection, module):
            self.issue("Cannot change the remote directory (cwd) or create it, check the ftp user rigths.")
            return
        # end if

        for key,value in self._config.local_directories.items():
            localDirectory = value
            try:
                if len(dict(self._config[value])["subdirectory"]) != 0:
                    localDirectory = sep.join((value, self._config[value]["subdirectory"]))
                # end if
            except:
                #No subdirectory specified in config file, nothing to do, carry on
                pass
            # end try

            try:
                remoteDirectory = self._config["protections_id"][key]
            except:
                self.issue("Cannot retrieve the protection id value for the {0} protection. Check the configuration file.".format(key))
                continue
            # end try

            try:
                filePrefix = dict(self._config[value])["prefix"]
                if len(filePrefix) != 0:
                    self.uploadFiles(newConnection, remoteDirectory, buildPath, localDirectory, filePrefix)
                else:
                    self.uploadFiles(newConnection, remoteDirectory, buildPath, localDirectory)
                # end if
            except:
                self.uploadFiles(newConnection, remoteDirectory, buildPath, localDirectory)
            # end try
        # end for

        try:
            newConnection.quit()
        except:
            pass
        # end try

    # end def upload

# end class FTPUpload
