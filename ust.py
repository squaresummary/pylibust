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

import chardet
import re


__all__ = ['ustNote','ustFile']

# --------------------
# The implement of note class and file class.
# 对音符类和文件类的实现。
class ustNote:
    """
    This class is a simple encapsulation of a dict, which stores the attributes
    of a UST file's note.
    这个类是对字典的简单封装。字典中存有UST文件的音符的属性。
    """

    def __init__(self, attributeDict: dict, verify=True):
        if verify:
            _attributeCheck(attributeDict)
        self._attribute = attributeDict

    def __getitem__(self, key: str):
        return self._attribute[key]

    def __setitem__(self, key: str, value):
        self._attribute[key] = value

    def __delitem__(self, key: str):
        del self._attribute[key]

    def __iter__(self):
        """
        By making object iterable, Instance support to use `in` to confirm
        whether a attribute exists or not.
        通过使对象可迭代，实例支持使用`in`来确定一个属性是否存在。
        """
        return (key for key in self._attribute)

    def __bool__(self):
        """
        This method returns whether a note is a rest or not.
        A rest will return False.
        这个方法用来判定一个音符是否是休止符。休止符返回False。
        """
        return self._attribute['Lyric'] not in ['', ' ', 'r', 'R']

    def __len__(self):
        return self._attribute['Length']

    def __repr__(self):
        strList = ['{}={}'.format(key, value) for key, value in self._attribute.items()]
        return '\n'.join(strList)

    def items(self):
        return self._attribute.items()


class ustFile:
    """
    This class is a simple encapsulation of list, which stores the note object.
    这个类是对列表的简单封装，储存音符对象。
    """

    def __init__(self, noteIter: iter, versionTuple=None, settingDict=None, verify=True):
        if versionTuple is None:
            versionTuple = ('UST Version1.2', 'Charset=UTF-8')
        if not isinstance(versionTuple, tuple):
            raise TypeError('The version needs a tuple, but a {}.'.format(type(versionTuple)))
        self._versionTuple = versionTuple
        if settingDict is None:
            settingDict = {'UstVersion': 1.2}
        if not isinstance(settingDict, dict):
            raise TypeError('The setting needs a dict, but a {}.'.format(type(settingDict)))
        self._settingDict = settingDict
        if verify:
            self._noteList = []
            for note in noteIter:
                if isinstance(note, ustNote):
                    self._noteList += [note]
                else:
                    self._noteList += [ustNote(note)]
        else:
            self._noteList = list(noteIter)

    @classmethod
    def open(cls, path: str):
        notes, version, setting = _parser(path)
        return cls(notes, version, setting)

    def save(self, path: str):
        _saver(self, path)

    def __getitem__(self, idx: int):
        """
        `idx` is short of the word `index` and those in following code
         have the same meaning.
        `idx`是`index`的缩写，后文同义。
        """
        return self._noteList[idx]

    def __setitem__(self, idx: int, value):
        self._noteList[idx] = value

    def __delitem__(self, idx: int):
        del self._noteList[idx]

    def __add__(self, other):
        if not isinstance(other, ustFile):
            raise TypeError('A ustFile is only able to add with a ustFile')
        return self._noteList + other

    def __iadd__(self, other):
        if not isinstance(other, ustFile):
            raise TypeError('A ustFile is only able to add with a ustFile')
        self._noteList += other

    def __iter__(self):
        return (i for i in self._noteList)

    def __repr__(self):
        fileContentList = ['[#VERSION]'] + list(self._versionTuple)
        fileContentList += ['[#SETTING]'] + ['{}={}'.format(key, value) for key, value in self._settingDict.items()]
        for number, note in enumerate(self._noteList):
            fileContentList += ['[#{:0>4d}]'.format(number)] + ['{}={}'.format(key, value) for key, value in note.items()]
        return '\n'.join(fileContentList)

    def __len__(self):
        return sum((len(note) for note in self._noteList))

    def quantize(self, standard: int):
        """
        This method will quantize notes. In other words, it will
        align the length of note to the integral multiple of the
        standard length given.
        这个方法将会量化音符。即将音符长度对齐到给定的标准长度的整数倍。
        """
        for note in self._noteList:
            note['Length'] = (round(note['Length']/standard))*standard
            if note['Length'] < 0:
                del note

    def range(self):
        """
        This method will return a tuple containing the pitches
        of the highest note and the lowest one. You can subtract
        them in order to get chromatic range.
        这个方法会返回最高音符和最低音符的音高组成的元组。二者相减可得音域。
        """
        pitches = [note['NoteNum'] for note in self._noteList if note]
        return (max(pitches),min(pitches))

    def insert(self, idx, other):
        if not isinstance(other, ustNote):
            other = ustNote(other)
        self._noteList.insert(idx, other)

    def insertMany(self, idx, other):
        for note in other:
            if not isinstance(note, ustNote):
                note = ustNote(note)
            self._noteList.insert(idx,note)

    def append(self, other):
        if not isinstance(other, ustNote):
            other = ustNote(other)
        self._noteList.append(other)

    def extend(self,other):
        for note in other:
            if not isinstance(note, ustNote):
                note = ustNote(note)
            self._noteList.append(note)


# --------------------
# Attribute check. If one attribute's value has incorrect type, it
# will raise a error.
# 属性检查，属性值类型不正确将报错。
def _attributeCheck(recDict):
    if not all([
        isinstance(recDict['Length'], (int, float)),
        isinstance(recDict['Lyric'], str),
        isinstance(recDict['NoteNum'], int)
    ]):
        raise TypeError('The length and pitch of note must be a number, the lyric must be a string.')
    if 'Envelope' in recDict:
        # TODO: 检查对应值的格式
        pass


# --------------------
# Read ust file
# 读取ust文件
def _parser(path):
    # 以下变量用于存储读入的数据
    notes = []
    singleNote = []
    version = []
    setting = []

    # 以下变量存储记录的状态
    verRecord, setRecord, noteRecord = False, False, False
    noteCount, RecPos = 0, 0

    # 以下语句用于探测文件编码
    with open(path, 'rb') as file:
        fileContent = file.read()
        encodingDict = chardet.detect(fileContent)

    # 以下语句逐行读入ust文件并解析
    with open(path, 'rt', encoding=encodingDict['encoding']) as file:
        for row in file:
            # 根据记录状态存储音符
            if not row.strip()[0:2] == '[#':
                if verRecord:
                    version += [row.strip()]
                if setRecord:
                    setting += [tuple((i.strip() for i in row.split('=')))]
                # noteCount 和 RecPos 分别是指示读取和存储位置的指针
                # 当 noteCount大于RecPos时说明有新的音符读入，将会把旧的音符打包为字典保存
                # 第一次大于时，没有旧的音符，不会保存
                if noteCount > RecPos:
                    RecPos += 1
                    if singleNote:
                        notes += [dict(singleNote)]
                        singleNote.clear()
                if noteRecord:
                    singleNote += [tuple((i.strip() for i in row.split('=')))]

            # 根据读入内容更改记录状态
            if row.strip() == '[#VERSION]':
                verRecord, setRecord, noteRecord = True, False, False
            if row.strip() == '[#SETTING]':
                verRecord, setRecord, noteRecord = False, True, False
            if re.match('\[#\w{4}\]',row.strip()):
                verRecord, setRecord, noteRecord = False, False, True
                noteCount += 1

    # 以下语句进一步处理各个属性的类型
    for note in notes:
        # 每个音符必须存在长度和音阶两个属性
        note['Length'] = eval(note['Length'])
        note['NoteNum'] = eval(note['NoteNum'])
        # 其他可选音符属性
        if 'Overlap' in note:
            note['Overlap'] = eval(note['Overlap']) if note['Overlap'] != '' else ''
        if 'PreUtterance' in note:
            note['PreUtterance'] = eval(note['PreUtterance']) if note['PreUtterance'] != '' else ''
        if 'StartPoint' in note:
            note['StartPoint'] = eval(note['StartPoint']) if note['StartPoint'] != '' else ''
        if 'Tempo' in note:
            note['Tempo'] = eval(note['Tempo']) if note['Tempo'] != '' else ''
        if 'Modulation' in note:
            note['Modulation'] = eval(note['Modulation']) if note['Modulation'] != '' else ''
        if 'Intensity' in note:
            note['Intensity'] = eval(note['Intensity']) if note['Intensity'] != '' else ''
        # 其他可选包络线属性
        if '@overlap' in note:
            note['@overlap'] = eval(note['@overlap']) if note['@overlap'] != '' else ''
        if '@preuttr' in note:
            note['@preuttr'] = eval(note['@preuttr']) if note['@preuttr'] != '' else ''
        if '@stpoint' in note:
            note['@stpoint'] = eval(note['@stpoint']) if note['@stpoint'] != '' else ''
        # 其他可选音高控制属性
        if 'PBType' in note:
            note['PBType'] = eval(note['PBType']) if note['PBType'] != '' else ''
        if 'PBStart' in note:
            note['PBStart'] = eval(note['PBStart']) if note['PBStart'] != '' else ''
        # TODO: 解析其他属性

    return notes, tuple(version), dict(setting)


# --------------------
# Save ust file
# 存储ust文件
def _saver(ustObj, path):
    with open(path, 'xt', encoding='utf8') as file:
        file.write(str(ustObj))
