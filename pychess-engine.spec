# -*- mode: python -*-
import os
import platform

a = Analysis(['lib/pychess/Players/PyChess.py'],
             pathex=[],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)

home = os.path.expanduser("~")
name = "pychess-engine"

if platform.system() == "Windows":
    modules = ("_hashlib", "_ssl", "bz2", "select", "unicodedata", "pyexpat")
    excludes = [(module, "'c:\\python27\\DLLs\\%s.pyd" % module, 'EXTENSION') for module in modules]
    name += ".exe"
else:
    excludes = [(module, None, None) for module in ("libcrypto.so.1.0.0", "libssl.so.1.0.0")]
    
data = [('pychess_book.bin', "%s/pychess/pychess_book.bin" % home, 'DATA')]

exe = EXE(pyz,
          a.scripts,
          a.binaries - excludes + data,
          a.zipfiles,
          a.datas,
          [('u', None, 'OPTION')],
          name=name,
          debug=False,
          strip=None,
          upx=True,
          console=False,
          noconsole=True)
