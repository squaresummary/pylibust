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

__all__ = ['ustNote', 'ustFile', 'attributeSeq', 'envelopeSeq', 'PBSSeq']

# 以下部分用于实现类型标注以增强代码的可维护性和可读性。
# 如果你对此不甚了解，请参见 https://docs.python.org/zh-cn/3/library/typing.html。
# The section below is used to implement type hint in order to make code
# readable and maintainable. If you have no idea about it, please see
# https://docs.python.org/zh-cn/3/library/typing.html.
from typing import Any, Iterable, Mapping, NewType, Sequence, Tuple, Dict

ustNoteType = NewType('ustNoteType', Mapping[str, Any])
ustFileType = NewType('ustFileType', Sequence[ustNoteType])

# --------------------
# The implement of note class and file class.
# 对音符类和文件类的实现。
class ustNote:
    """
    This class is a thin wrapper of a dict, which stores the attributes
    of a UST file's note.
    这个类是对字典的简单封装。字典中存有UST文件的音符的属性。
    """

    def __init__(self, attributeDict: Dict[str, Any], verify : bool = True):
        if verify:
            _attributeCheck(attributeDict)
        self._attribute = attributeDict

    def __getitem__(self, key: str):
        return self._attribute[key]

    def __setitem__(self, key: str, value: Any):
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
    This class is a thin wrapper of list, which stores the note object.
    这个类是对列表的简单封装，储存音符对象。
    """

    def __init__(self, noteIter: Iterable[ustNoteType],
                versionTuple: Tuple[str, ...] = None,
                settingDict: Dict[str, Any] = None,
                verify: bool = True):
        if versionTuple is None or versionTuple == ():
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

    @property
    def setting(self):
        return self._settingDict

    def setSetting(self, key: str, value: Any):
        self._settingDict[key] = value

    def save(self, path: str):
        _saver(self, path)

    def __getitem__(self, idx: int):
        """
        `idx` is short of the word `index` and those in following code
         have the same meaning.
        `idx`是`index`的缩写，后文同义。
        """
        return self._noteList[idx]

    def __setitem__(self, idx: int, value: Any):
        self._noteList[idx] = value

    def __delitem__(self, idx: int):
        del self._noteList[idx]

    def __add__(self, other: ustFileType):
        if not isinstance(other, ustFile):
            raise TypeError('A ustFile is only able to add with a ustFile')
        return self._noteList + other

    def __iadd__(self, other: ustFileType):
        if not isinstance(other, ustFile):
            raise TypeError('A ustFile is only able to add with a ustFile')
        self._noteList += other

    def __iter__(self):
        return (i for i in self._noteList)

    def __repr__(self):
        fileContentList = ['[#VERSION]'] + list(self._versionTuple)
        fileContentList += ['[#SETTING]'] + ['{}={}'.format(key, value) for key, value in self._settingDict.items()]
        for number, note in enumerate(self._noteList):
            fileContentList += ['[#{:0>4d}]'.format(number)] + ['{}={}'.format(key, str(value)) for key, value in
                                                                note.items()]
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
            note['Length'] = (round(note['Length'] / standard)) * standard
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
        return (max(pitches), min(pitches))

    def insert(self, idx: int, other: ustNoteType):
        if not isinstance(other, ustNote):
            other = ustNote(other)
        self._noteList.insert(idx, other)

    def insertMany(self, idx: int, other: Iterable[ustNoteType]):
        for note in other:
            if not isinstance(note, ustNote):
                note = ustNote(note)
            self._noteList.insert(idx, note)

    def append(self, other: ustNoteType):
        if not isinstance(other, ustNote):
            other = ustNote(other)
        self._noteList.append(other)

    def extend(self, other: ustNoteType):
        for note in other:
            if not isinstance(note, ustNote):
                note = ustNote(note)
            self._noteList.append(note)


# --------------------
# Classes used to store the attribute which is sequence in ust note.
# 用于存储ust音符属性中的序列的类。
class attributeSeq(list):
    """
    This class stores common sequence attribute.
    这个类存储通常的序列属性。
    """

    def __init__(self,attributeStr: str):
        attributeList = attributeStr.split(',')
        for item in attributeList:
            if item == '':
                self.append(0)
            else:
                self.append(eval(item))

    def __str__(self):
        return ','.join(str(item) for item in self)


class envelopeSeq(attributeSeq):
    """
    This class stores damn envelope. Evil `%`!
    这个类存储该死的包络线。飴屋加的`%`真是可恶。
    """

    def __init__(self, envelope: str):
        envelopeList = envelope.split(',')
        for item in envelopeList:
            if item == '%':
                self.append(item)
            else:
                self.append(eval(item))


class PBSSeq(attributeSeq):
    """
    This class stores the time and pitch offset between the
    beginning of the note and first control point. Damn `;`.
    这个类存储第一个控制点与音符开头的时间和音高偏移量。该死的`;`。
    """

    def __init__(self,PBS: str):
        PBSList = PBS.split(';')
        for item in PBSList:
            if item == '':
                self.append(0)
            else:
                self.append(eval(item))
        
        if len(self) > 2:
            raise ValueError('The PBS only need 2 parameters, but {}'.format(len(self)))
    
    def __str__(self):
        return ';'.join(str(item) for item in self)


# --------------------
# Attribute check. If one attribute's value has incorrect type, it
# will raise a error.
# 属性检查，属性值类型不正确将报错。
def _attributeCheck(recDict):
    # 检查必要的音符属性（长度、音阶、歌词）
    if not all([
        isinstance(recDict['Length'], (int, float)),
        isinstance(recDict['Lyric'], str),
        isinstance(recDict['NoteNum'], int)
    ]):
        raise TypeError('The length and pitch of note must be a number, the lyric must be a string.')

    # 检查其他可选音符属性
    if 'Overlap' in recDict:
        if not isinstance(recDict['Overlap'], (int, float)):
            raise TypeError('Overlap must be a number.')
    if 'PreUtterance' in recDict:
        if not isinstance(recDict['PreUtterance'], (int, float)):
            raise TypeError('PreUtterance must be a number.')
    if 'StartPoint' in recDict:
        if not isinstance(recDict['StartPoint'], (int, float)):
            raise TypeError('StartPoint must be a number.')
    if 'Tempo' in recDict:
        if not isinstance(recDict['Tempo'], (int, float)):
            raise TypeError('Tempo must be a number.')
    if 'Modulation' in recDict:
        if not isinstance(recDict['Modulation'], (int, float)):
            raise TypeError('Modulation must be a number.')
    if 'Intensity' in recDict:
        if not isinstance(recDict['Intensity'], (int, float)):
            raise TypeError('Intensity must be a number.')
    if 'Flags' in recDict:
        if not isinstance(recDict['Flags'], str):
            raise TypeError('Flags must be a string.')

    # 检查包络线属性
    if 'Envelope' in recDict:
        if not isinstance(recDict['Envelope'], envelopeSeq):
            raise TypeError('Envelope must be an envelopeSeq object.')
    if '@overlap' in recDict:
        if not isinstance(recDict['@overlap'], (int, float)):
            raise TypeError('Envelope Overlap must be a number.')
    if '@preuttr' in recDict:
        if not isinstance(recDict['@preuttr'], (int, float)):
            raise TypeError('Envelope PreUtterance must be a number.')
    if '@stpoint' in recDict:
        if not isinstance(recDict['@stpoint'], (int, float)):
            raise TypeError('Envelope StartPoint must be a number.')

    # 检查其他可选音高属性
    if 'PBType' in recDict:
        if not isinstance(recDict['PBType'], int):
            raise TypeError('The interval between two control points in mode 1 must be a integer.')
    if 'PBStart' in recDict:
        if not isinstance(recDict['PBStart'], int):
            raise TypeError('The StartPoint of control points in mode 1 must be a integer.')
    if 'PitchBend' in recDict:
        if not isinstance(recDict['PitchBend'], attributeSeq):
            raise TypeError('The list of the control points` Y-axis coordinates in mode 1 must be attributeSeq object.')
    if 'PBW' in recDict:
        if not isinstance(recDict['PBW'], attributeSeq):
            raise TypeError('The list of the control points` X-axis coordinates in mode 2 must be attributeSeq object.')
    if 'PBY' in recDict:
        if not isinstance(recDict['PBY'], attributeSeq):
            raise TypeError('The list of the control points` Y-axis coordinates in mode 2 must be attributeSeq object.')
    if 'PBS' in recDict:
        if not isinstance(recDict['PBS'], PBSSeq):
            raise TypeError('The time and pitch offset between the beginning of the note and first control point' +
                            'in mode 2 must be PBSSeq object.')
    if 'VBR' in recDict:
        if not isinstance(recDict['VBR'], attributeSeq):
            raise TypeError('The parameters list of auto vibrato must be attributeSeq object.')


# --------------------
# Read ust file
# 读取ust文件
def _parser(path: str):
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
            # 根据记录状态存储音符 忽略空行
            if row.strip()[0:2] != '[#' and row.strip() != '':
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
            
            # 当音轨结束时记录最后一个音符
            if row.strip() == '[#TRACKEND]':
                notes += [dict(singleNote)]
                singleNote.clear()

            # 根据读入内容更改记录状态
            if row.strip() == '[#VERSION]':
                verRecord, setRecord, noteRecord = True, False, False
            if row.strip() == '[#SETTING]':
                verRecord, setRecord, noteRecord = False, True, False
            if re.match('\[#\w{4}]', row.strip()):
                verRecord, setRecord, noteRecord = False, False, True
                noteCount += 1

    # 以下语句进一步将[#SETTING]块的内容转换为字典并处理部分属性的类型
    settingDict = dict(setting)
    if 'Tempo' in settingDict:
        settingDict['Tempo'] = eval(settingDict['Tempo'])
        # 因为ust中经常有Tempo达到500000.00的情况，所以过大的Tempo将会被强行设定为120
        if settingDict['Tempo'] > 300:
            settingDict = 120
    if 'Tracks' in settingDict:
        settingDict['Tracks'] = eval(settingDict['Tracks'])
    if 'Mode2' in settingDict:
        settingDict['Mode2'] = eval(settingDict['Mode2'])

    # 以下语句进一步处理各个音符属性的类型
    for note in notes:
        # 建立存储属性与对应策略的字典
        strategyDict = {
            # 必选属性 长度和音高
            'Length': eval,
            'NoteNum': eval,
            # 其他可选音符属性
            'Overlap': eval,
            'PreUtterance': eval,
            'StartPoint': eval,
            'Tempo': eval,
            'Modulation': eval,
            'Intensity': eval,
            # 其他可选包络线属性
            'Envelope': envelopeSeq,
            '@overlap': eval,
            '@preuttr': eval,
            '@stpoint': eval,
            # 其他可选音高控制属性(Mode1)
            'PBType': eval,
            'PBStart': eval,
            'PitchBend': attributeSeq,
            # 其他可选音高控制属性(Mode2)
            'PBW': attributeSeq,
            'PBY': attributeSeq,
            'PBS': PBSSeq,
            'VBR': attributeSeq,
        }
        # 根据对应的属性选择策略 跳过值为空的和键未知的属性 为免报错值为空的键值对将会被记录下来删除
        invaildAttributeList =[]
        for attribute in note:
            if note[attribute] != '':
                policy = strategyDict.get(attribute)
                if policy != None:
                    note[attribute] = policy(note[attribute])
            else:
                invaildAttributeList += [attribute]
        for attribute in invaildAttributeList:
            del note[attribute]
        invaildAttributeList.clear()

    return notes, tuple(version), dict(setting)


# --------------------
# Save ust file
# 存储ust文件
def _saver(ustObj, path: str):
    with open(path, 'xt', encoding='utf8') as file:
        file.write(str(ustObj))
