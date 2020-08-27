# -*- coding:utf-8 -*-
"""
Copyright (c) 2020, squaresum

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from typing import Iterable
from .ust import ustNote, ustFile, attributeSeq, envelopeSeq, PBSSeq


# --------------------
# The functions converting other format to ustFile object.
# 将其他格式转换为ust文件对象的函数
def nn2ust(nnIter: Iterable[str]) -> ustFile:
    nnIter = iter(nnIter)

    # 解析nn文件的首行。此行记录工程的元数据，如全局曲速或节拍等。
    header = next(nnIter).strip().split()
    ustHeader = {'Tempo': float(header[0])}

    # 读取而不解析nn文件的第二行。第二行记录nn文件中包含的音符数量。
    next(nnIter)

    # 解析nn文件剩余的行。剩余的行中包含nn文件中所有的音符。
    ustNoteList = []
    for row in nnIter:
        nnNote = row.strip().split()
        nnPitchList = list(map(int, nnNote[12].split(',')))
        nnPitchList = [(50 - pitch) / 10 for pitch in nnPitchList]
        ustNoteList += [ustNote({
            'Lyric': nnNote[0],
            'Length': int(nnNote[3]) * 60,
            'NoteNum': 83 - int(nnNote[4]),
            'VBR': attributeSeq([int(nnNote[8]), int(nnNote[10]), int(nnNote[9]), 0, 0, 0, 0, 0]),
            'PBW': attributeSeq(int(nnNote[3]) * 60 / len(nnPitchList) for i in range(len(nnPitchList))),
            'PBY': attributeSeq(nnPitchList),
            'PBS': PBSSeq([0, 0])
        })]

    return ustFile(ustNoteList, settingDict=ustHeader)


# --------------------
# The functions converting ustFile object to other format.
# 将ust文件对象转换为其他格式的函数
def ust2utaufile(ustFileObj: ustFile):
    """
    In order to avoid making wheel repeatedly, this function allows you to convert a pylibust.ustFile
    object to a utaufile.Ustfile object and whereby you can use the functions in utaufile library.
    为避免重复造轮子，这个函数可以将pylibust.ustFile对象转换为utaufile.Ustfile对象。籍此您可以使用utaufile库中的功能。
    """
    import utaufile
    UstnoteList = []
    for note in ustFileObj:
        noteDict = {key: value for key, value in note.items()}
        length = noteDict.pop('Length')
        notenum = noteDict.pop('NoteNum')
        lyric = noteDict.pop('Lyric')
        UstnoteObj = utaufile.Ustnote(
            length=length,
            lyric=lyric,
            notenum=notenum,
            properties=noteDict
        )
        UstnoteList += [UstnoteObj]
    return utaufile.Ustfile(properties=ustFileObj.setting ,note=UstnoteList)
