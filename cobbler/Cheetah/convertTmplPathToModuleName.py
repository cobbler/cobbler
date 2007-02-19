import os.path
import string

l = ['_'] * 256
for c in string.digits + string.letters:
    l[ord(c)] = c
_pathNameTransChars = string.join(l, '')
del l, c

def convertTmplPathToModuleName(tmplPath,
                                _pathNameTransChars=_pathNameTransChars,
                                splitdrive=os.path.splitdrive,
                                translate=string.translate,
                                ):
    return translate(splitdrive(tmplPath)[1], _pathNameTransChars)
