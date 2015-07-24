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
    console = False
    data = [('pychess_book.bin', "..\\pychess\\pychess_book.bin", 'DATA')]

else:
    modules = ("_codecs_cn", "_codecs_hk", "_codecs_iso2022", "_codecs_jp", "_codecs_kr", "_codecs_tw",
               "_multibytecodecs", "_ssl", "audioop", "bz2", "unicodedata")
    excludes = [(module, "/usr/lib/python2.7/lib-dynload/%s.so" % module, 'EXTENSION') for module in modules]

    libs = ("libcrypto.so.1.0.0", "libssl.so.1.0.0")
    excludes += [(lib, "/usr/lib/%s" % lib, "BINARY") for lib in libs]
    console = True
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
          console=console,
          noconsole=True)
