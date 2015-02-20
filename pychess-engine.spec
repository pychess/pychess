# -*- mode: python -*-
import os

home = os.path.expanduser("~")

a = Analysis(['lib/pychess/Players/PyChess.py'],
             pathex=[],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)

excludes = [] #(module, None, None) for module in ("libcrypto.so.1.0.0", "libssl.so.1.0.0")]
data = [('pychess_book.bin', '%s/pychess/pychess_book.bin' % home, 'DATA')]

exe = EXE(pyz,
          a.scripts,
          a.binaries - excludes + data,
          a.zipfiles,
          a.datas,
          [('u', None, 'OPTION')],
          name='pychess-engine',
          debug=False,
          strip=None,
          upx=True,
          console=True )
