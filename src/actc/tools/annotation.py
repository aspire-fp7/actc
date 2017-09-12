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
''' @package  actc.tools.annotation

@brief   annotation extraction

@author  Ronan Le Gallic, Jeroen Van Cleemput

@date    2014/10/28
'''
# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------
from glob                       import glob
from json                       import dump
from json                       import load
from os.path                    import abspath
from os.path                    import basename
from os.path                    import dirname
from os.path                    import join
from os.path                    import isfile


from actc.tools                 import AbstractBasicCmdTool
from actc.tools                 import AbstractCmdTool
from actc.tools                 import AbstractPythonTool
from actc.tools                 import toList

from actc.tools.utils           import make_hash

from doit.action                import CmdAction

import fileinput
import re
import sys


# ------------------------------------------------------------------------------
# implementation
# ------------------------------------------------------------------------------

READ_ANNOT = '/opt/annotation_extractor/readAnnot.sh'

class AnnotationExtractor(AbstractBasicCmdTool):
    '''
    annotation extraction
    '''

    def __init__(self, program = None,
                       options = None,
                       outputs = None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(AnnotationExtractor, self).__init__(program = program,
                                                  options = options,
                                                  outputs = outputs)
    # end def __init__

    _ACTION = 'extract annot'

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
        args.append(task.targets[0])

        # /!\ Hack: replace '_' by ' '
        args.append("&& sed -i 's/\\(\"[[:lower:]]*\\)_\\([[:lower:]]*\"\\)\s*:/\\1 \\2:/g'")
        args.append(task.targets[0])

        return ' '.join(args)
    # end def _cmd

# end class AnnotationExtractor

class AnnotationMerger(AbstractPythonTool):
    '''
    Merger annotation files
    '''

    _ACTION = 'merge'

    def _python(self, task):
        '''
        @copydoc actc.tools.AbstractPythonTool._python
        '''
        annotations = list()

        for annotation in list(task.file_dep):

            with open(annotation, 'r') as fo:
                annotations.extend(load(fo))
            # end with
        # end for

        with open(task.targets[0], 'w') as fo:
            dump(annotations, fo,
                 indent     = 2,
                 separators = (',', ': '),
                 sort_keys  = True)
        # end with

    # end def _python

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractTool.tasks
        '''
        # Create Folders
        yield super(AnnotationMerger, self).tasks(*args, **kwargs)

        src = list()

        for arg in toList(args[0]):
            src.extend(glob(abspath(arg)))
        # end for

        dst = toList(args[1])

        yield {'name'    : self._name(self._ACTION, src, '\ninto', dst),
               'title'   : self._title,
               'actions' : [self._python,],
               'targets' : dst,
               'file_dep': src,
               }

    # end def tasks

# end class AnnotationMerger

class AnnotationPatcher(AbstractCmdTool):
    '''
    Replace security requirement annotations  with unique ID placeholders using an ADSS patch file
    '''
    def __init__(self, program=None,
                       options=None,
                       outputs=None):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool.__init__
        '''
        super(AnnotationPatcher, self).__init__(program=program,
                                                  options=options,
                                                  outputs=outputs)

    _ACTION = "patching"

    def _cmd(self, task):
        '''
        @copydoc actc.tools.AbstractBasicCmdTool._cmd
        '''

        # Apply patch file
        args = list(['patch', ])
        # args.append('-p0')
        args.append('<')
        args.append(list(task.file_dep)[0])

        # Creat target file dependency
        args.extend(['&&', 'touch', task.targets[0]])

        #Hack execute in target folder
        args.insert(0, 'cd %s &&' % dirname(list(task.file_dep)[0]))

        return ' '.join(args)
    # end def _cmd

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''

        dst, _ = self._outputs[0]
        patch_file = abspath(toList(args[0])[0])

        yield {'name'    : self._name(self._ACTION, patch_file),
               'title'   : self._title,
               'actions' : [CmdAction(self._cmd), ],
               'targets' : [dst, ],
               'file_dep': [patch_file, ],
               'task_dep': ['_createfolder_' + dst]
               }

    # end def tasks
# end class AnnotationPatcher

# Matching strings for annotations, use with % <content>
_RE_ATTRIBUTE_MATCH = r'__attribute__\s*\(\s*\(\s*ASPIRE\s*\(\s*".*%s.*"\s*\)\s*\)\s*\)'
_RE_PRAGMA_MATCH = r'_Pragma\s*\(\s*"\s*ASPIRE\s* begin\s*.* %s\s*.*"\s*\)'
_RE_PRE_PRAGMA_MATCH = r'#pragma\s* ASPIRE\s* begin\s*.* %s.*'

# Replacement strings for annotations, use with % <content>
ATTRIBUTE_REPLACE = '__attribute__((ASPIRE("%s")))'
PRAGMA_REPLACE = '_Pragma("ASPIRE begin %s")'
PRE_PRAGMA_REPLACE = '#pragma ASPIRE begin %s'

class AnnotationRewriter(AbstractPythonTool):
    '''
    Replace security requirement annotations (see D5.01) with some "concrete annotations"
    '''
    _ACTION = "annotate"

    def _python(self, task, filter, keep_placeholders, replace_all, preprocessed):
        '''
        @copydoc actc.tools.AbstractPythonTool._python
        '''

        # Load annotations from json file
        annotations_file = list(task.file_dep)[0]

        # Filter annotations based on protection filter
        annotations = filterAnnotations(annotations_file, annotation_filter=filter, filtered_only=not replace_all)

        # Check which annotations have been changed since previous run (and get line number and line hash metadata)
        applied_annotations = task.targets[0]
        updated_annotations = getUpdatedAnnotations(annotations, applied_annotations)

#         print 'updated annotations'
#         print annotations

        # Replace placeholders with annotation content for the updated annotations (inefficiently)
        for annotation in updated_annotations:

            source_file = join(dirname(applied_annotations), basename(annotation['file name']))
            if(preprocessed):
                source_file += '.i'
            annotation_id = annotation['id']

            protections = annotation['filtered'].values() if annotation['filtered'] else []
            if(keep_placeholders or not protections):
                protections.append('protection(placeHolder, id(%s))' % annotation_id)
            content = ", ".join(protections)

            print('Rewriting annotation %s in file %s with %s\n' % (annotation_id, source_file, content))
            # Look for these:
            # __attribute__((ASPIRE("placeHolder(0)")))
            # _Pragma("ASPIRE begin placeHolder(2)")


            replace_by_content = False
            # Replace by line Hash in applied_annotations file
            if(annotation.has_key('line_number') and annotation.has_key('line_hash') and annotation.has_key('content')):
                print 'replace by content match'
#                 print str(annotation)
                placeholder = re.escape(annotation['content'])
                replace_by_content = True
            # Replace by matching against placeholder protection
            else:
                print 'replace by placeholder ID match'
                placeholder = (r'protection\s*\(\s*placeHolder\s*,\s*id\s*\(\s*' + str(annotation_id) + r'\s*\)\s*\)')
            # end if
            attribute_match_r = re.compile(_RE_ATTRIBUTE_MATCH % placeholder)
            attribute_replace = ATTRIBUTE_REPLACE % content
            pragma_match_r = re.compile(_RE_PRAGMA_MATCH % placeholder)
            pragma_replace = PRAGMA_REPLACE % content
            pre_pragma_match_r = re.compile(_RE_PRE_PRAGMA_MATCH % placeholder)
            pre_pragma_replace = PRE_PRAGMA_REPLACE % content

            # #pragma ASPIRE begin protection(prot90,parameter2), protection(prot15,parameter2), placeHolder(3)
            # _Pragma("ASPIRE begin protection(prot90,parameter2), protection(prot15,parameter2), placeHolder(3)")

            # STDOUT redirected to file, magic!
            print 'source_file', source_file
            replaced = 0
            for line in fileinput.input(source_file, inplace=True):

                # Check content of the line if not replacing by ID
                if(replace_by_content):
                    assert annotation.has_key('line_number') and annotation.has_key('line_hash') and annotation.has_key('content')
                    if(annotation['line_number'] != fileinput.lineno()  # Works for cached sources
                       or annotation['line_hash'] != hash(line)
                       or annotation['content'] not in line):
                        print line,
                        continue

                (r1, r2, r3) = (0, 0, 0)

                # Match and replace
                line, r1 = re.subn(attribute_match_r, attribute_replace, line)
                if(preprocessed):
                    line, r2 = re.subn(pre_pragma_match_r, pre_pragma_replace, line)
                else:
                    line, r3 = re.subn(pragma_match_r, pragma_replace, line)
                # end if


                assert (r1 + r2 + r3  in (0, 1))
                if(r1 + r2 + r3 == 1):
                    # Update metadata
                    annotation['line_number'] = fileinput.lineno()
                    annotation['line_hash'] = hash(line)
                    annotation['content'] = content

                    replaced += 1

                print line,
            # end for

            # Check that the replacement succeeded
            if(replaced != 1):
                sys.stderr.write('WARNING, annotation rewriting failed! (replacement count=%d)\n' % replaced)
                sys.stderr.write(str(annotation))
                sys.exit(1)
            # end if

        # end for

        # Create target file containing  applied annotations
        with open(applied_annotations, 'w+') as fo:
            dump([a for a in annotations if 'filtered' in a and a['filtered']], fo,
                 indent=2,
                 separators=(',', ': '),
                 sort_keys=True)
        # end with
    # end def _python

    def tasks(self, *args, **kwargs):
        '''
        @copydoc actc.tools.AbstractCmdTool.tasks
        '''

        dst, _ = self._outputs[0]
        annotations_file = abspath(toList(args[0])[0])

        yield {'name'    : self._name(self._ACTION, annotations_file),
               'title'   : self._title,
               'actions' : [self._python, ],
               'params'  : [{'name'   : 'filter',
                             'short'  : None,
                             'default': kwargs.get('filter', None),
                             },
                             {'name'   : 'keep_placeholders',
                             'short'  : None,
                             'default': kwargs.get('keep_placeholders', False),
                             },
                             {'name'   : 'replace_all',
                             'short'  : None,
                             'default': kwargs.get('replace_all', False),
                             },
                             {'name'   : 'preprocessed',
                             'short'  : None,
                             'default': kwargs.get('preprocessed', False),
                             },
                            ],
               'targets' : [dst, ],
               'file_dep': [annotations_file, ],
               }
    #  end def tasks
# end class AnnotationRewriter

# def findPragmas(source_file):
#     expr = nestedExpr('(', ')')
#     with open(source_file, 'r') as sf:
#
#         # filter on pragma
#         lines = (line for line in sf if r'#pragma ASPIRE begin' in line)
#         for line in lines:
#             print 'parsing: ' + line.strip()
#             print expr.parseString('(' + line.strip() + ')')
#
# #end def findPragmas

def getUpdatedAnnotations(candidate_annotations, applied_annotations):
    # First run, return all candidates
    if(not isfile(applied_annotations)):
        return candidate_annotations
    # end if

#     print 'candidate annotations'
#     print candidate_annotations
    # return annotations that have been changed since previous run
    annotations = []
    with open(applied_annotations,'r') as af:
        # load applied annotations and index by ID
        temp = load(af)
        applied_annotations_list = dict()
        for a in temp:
            applied_annotations_list[a['id']] = a
        # end for


        candidate_id_list = []
        # Add modified and new annotations to the list
        for a in candidate_annotations:
            
            #keep track of candidate annotation ids
            annotation_id = a['id']
            candidate_id_list.append(annotation_id)

            # check filtered annotation content if applied in previous run
            if annotation_id in applied_annotations_list.keys():
                aa = applied_annotations_list[annotation_id]

                # Update metadata
                a['content'] = aa['content']
                a['line_number'] = aa['line_number']
                a['line_hash'] = aa['line_hash']

                # Add to list if content changed
                if a['filtered'] != aa['filtered']:
                    print 'Updating annotation: ' + str(aa['filtered']) + ' --> ' + str(a['filtered'])
                    annotations.append(a)
            # If not applied in previous run, add filtered annotation content if it has filtered content
            else:
                if a['filtered']:
                    print 'New annotation: ' + str(a['filtered'])
                    annotations.append(a)
            # end if
        # end for

        # Remove annotation content from applied annotations that are not in the candidate list, add to list if applied annotations was not empty
        for a in applied_annotations_list.values():
            if(a['id'] not in candidate_id_list and a['filtered']):
                print 'Clearing annotation: ' + str(a['filtered'])
                a['content'] = a['content']
                a['filtered'] = dict()
                annotations.append(a)
            # end if
        # end for
    #end with
    return annotations
#end def getUpdatedAnnotations

def filterAnnotations(annotation_file, source_file=None, annotation_filter=None, filtered_only=False):
    annotations = []

    # load annotations file
    with open(annotation_file, 'r') as af:
        annotations.extend(load(af))

    # filter on source file
    annotations = [a for a in annotations if (not source_file or ('file name' in a and a['file name'] == source_file))]

    # filter on protection technique
    for annotation in annotations:
        annotation['filtered'] = {}
        for p, a in ((p, a) for (p, a) in parseAnnotationContent(annotation['annotation content']) if (not annotation_filter) or (p in annotation_filter)):
            if(annotation['filtered'].has_key(p)):
                annotation['filtered'][p] += ', ' + a
            else:
                annotation['filtered'][p] = a
            # end if
        # end for
    # end for

    if filtered_only:
        # return only the filtered annotations
        return [a for a in annotations if 'filtered' in a and a['filtered']]
    else:
        return annotations
# end def filterAnnotations

# '#define DOBFS __attribute__((ASPIRE("protection(xor,mask(constant(35)))")))'

_RE_PROTECTION_TECHNIQUE = r'protection\s*\((.*?)\s*(?=\(|\)|,)'
_RE_PROTECTION_ANNOTATION = r'protection\s*\(.*?(?=,\s*protection|$)'
def parseAnnotationContent(annotation_content):
    ret = re.compile(_RE_PROTECTION_TECHNIQUE)
    rea = re.compile(_RE_PROTECTION_ANNOTATION)

    rv = []
    annotations = rea.findall(annotation_content)
    for annotation in annotations:
        technique = ret.match(annotation).group(1)
        annotation = matchBrackets(annotation)
        rv.append((technique, annotation))
    # end for

    return rv
# end def parseAnnotationContent

def matchBrackets(string):
    """Remove characters after final closed bracket"""
    count = 0
    for i, c in enumerate(string):
        if c == '(':
            count +=1
        elif c == ')':
            count -=1
            if count == 0:
                return string[0:i + 1]
            # end if
        #end if
    #end for
    return string
#end def matchBrackets

def updateFolders(task_folders, annotations_file, annotations_list):
    if(not annotations_file or not isfile(annotations_file)):
        return
    # end if

    annotations_hash = ""
    for task, folders in task_folders.items():
#             # Filter annotations based on protection filter
        filter = annotations_list.get(task) if annotations_list.get(task) else ['DUMMY']
        annotations = filterAnnotations(annotations_file, annotation_filter=filter, filtered_only=True)

        if annotations:
            annotations_hash = str(hash((annotations_hash, make_hash(annotations)))).encode('hex')
#         print task, (len(annotations)) , annotations_hash

        suffix = ('-' + annotations_hash) if annotations_hash else ''

        task_folders[task].update({'suffix' : suffix})

    # end for

# end def updateFolders

def generateExternalAnnotations(source_file, start_id, patch_file, json_file):
    """ Generate External annotations json file and replace annotations by placeholders in the source file"""
    placeholder = 'protection(placeHolder, id(%s))'
    attribute_match_r = re.compile(_RE_ATTRIBUTE_MATCH % '.*')
    attribute_replace = ATTRIBUTE_REPLACE % placeholder
    pragma_match_r = re.compile(_RE_PRAGMA_MATCH % '.*')
    pragma_replace = PRAGMA_REPLACE % placeholder

    annotation_id = start_id

    replace_annotations = []

    # STDOUT redirected to file, magic!
    for line in fileinput.input(source_file, inplace=True):

        # Replace attribute or annotation with placeholders
        new_line, r1 = re.subn(attribute_match_r, attribute_replace % (annotation_id), line)
        new_line, r2 = re.subn(pragma_match_r, pragma_replace % (annotation_id), new_line)

        # If replacement happend store annotation in replace_annotations
        if(r1 + r2 == 1):
            sys.stderr.write(line)
            sys.stderr.write(new_line)

            annotations = parseAnnotationContent(line)

            # Create annotation entry for json file
            entry = dict()
            entry['file name'] = source_file
            entry['id'] = annotation_id
            entry['annotation content'] = ', '.join([a[1] for a in annotations])
            sys.stderr.write(str(entry))
            replace_annotations.append(entry)

            sys.stderr.write('\n')

            annotation_id += 1
        # end if

        # output to file
        print new_line,
    # end for

    # write annotations to patch file
    with open(json_file, 'w') as fo:
        dump(replace_annotations, fo,
                indent=2,
                separators=(',', ': '),
                sort_keys=True)
    # end with

    return replace_annotations, annotation_id
# end def generateExternalAnnotations

# ------------------------------------------------------------------------------
# END OF FILE
# ------------------------------------------------------------------------------
