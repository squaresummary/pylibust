# pylibust

用于解析和编辑UTAU的ust文件的python模块

A python module for parsing or writing ust file created by UTAU

## 依赖（dependency）

* chardet

## 用法（HOWTO）

打开文件

```python
import pylibust


ustFileObj =  pylibust.ustFile.open('[the path of your UST file]')
```

创建音符
```python
ustNoteObj = pylibust.ustFile({'Length':480,'Lyric':R,'NoteNum':63})
```

创建文件
```python
ustFileObj = pylibust.ustFile([UstNoteObj1,UstNoteObj2,...])
```

保存文件
```python
ustFileObj.save('[the path you want to save your UST file]')
```

## 许可证（Lisence）
Apache License, Version 2.0
