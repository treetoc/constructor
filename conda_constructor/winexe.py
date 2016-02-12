from __future__ import print_function, division, absolute_import

import os
import sys
import shutil
import tempfile
from os.path import abspath, dirname, join
from subprocess import check_call

from conda_constructor.utils import preprocess
import conda_constructor.common as common


THIS_DIR = dirname(__file__)
NSIS_DIR = join(THIS_DIR, 'nsis')
MAKENSIS_EXE = join(sys.prefix, 'NSIS', 'makensis.exe')


def str_esc(s):
    for a, b in [('$', '$$'), ('"', '$\\"'), ('\n', '$\\n'), ('\t', '$\\t')]:
        s = s.replace(a, b)
    return '"%s"' % s


def read_nsi_tmpl():
    path = join(NSIS_DIR, 'main.nsi.tmpl')
    print('Reading: %s' % path)
    with open(path) as fi:
        return fi.read()


def make_nsi(info, dir_path):
    "Creates the tmp/main.nsi from the template file"
    data = read_nsi_tmpl()
    name = info['name']
    dists0 = common.DISTS[0][:-8]
    py_name, py_version, unused_build = dists0.rsplit('-', 2)
    if py_name != 'python':
        sys.exit("Error: a Python package needs to be part of the "
                 "specifications")

    arch = int(info['platform'].split('-')[1])
    license_path = abspath(info.get('license_file',
                                    join(NSIS_DIR, 'license.txt')))

    data = preprocess(data, common.ns_info(info))
    data = data.replace('__NAME__', str_esc(name))
    data = data.replace('__VERSION__', '1.0.0')
    data = data.replace('__ARCH__', str_esc('%d-bit' % arch))
    data = data.replace('__PY_VER__', py_version[:3])
    data = data.replace('__PYVERSION__', str_esc(py_version))
    data = data.replace('__PYVERSION_JUSTDIGITS__',
                        str_esc(''.join(py_version.split('.'))))
    data = data.replace('__OUTFILE__', str_esc(info['_outpath']))
    data = data.replace('__HEADERIMAGE__',
                        str_esc(join(NSIS_DIR, 'header.bmp')))
    data = data.replace('__WELCOMEIMAGE__',
                        str_esc(join(NSIS_DIR, 'installer.bmp')))
    data = data.replace('__ICONFILE__',
                        str_esc(join(NSIS_DIR, 'logo.ico')))
    data = data.replace('__LICENSEFILE__', str_esc(license_path))

    # these are unescaped (and unquoted)
    data = data.replace('@NAME@', name)
    data = data.replace('@NSIS_DIR@', NSIS_DIR)
    data = data.replace('@VCREDIST_DIR@', join(sys.prefix, 'VCREDIST'))
    data = data.replace('@BITS@', str(arch))
    data = data.replace('@XDD@', {32: 'x86', 64: 'x64'}[arch])

    pkg_commands = []
    for fn in common.DISTS:
        path = join(common.REPO_DIR, fn)
        pkg_commands.append('# --> %s <--' % fn)
        pkg_commands.append('File %s' % str_esc(path))
        pkg_commands.append('untgz::extract "-d" "$INSTDIR" '
                            '"-zbz2" "$INSTDIR\pkgs\%s"' % fn)
        pkg_commands.append('ExecWait \'"$INSTDIR\pythonw.exe" '
                            '"$INSTDIR\Lib\_nsis.py" postpkg\'')
        pkg_commands.append('')
    data = data.replace('@PKG_COMMANDS@', '\n    '.join(pkg_commands))

    nsi_path = join(dir_path, 'main.nsi')
    with open(nsi_path, 'w') as fo:
        fo.write(data)
    # Copy all the NSIS header files (*.nsh)
    for fn in os.listdir(NSIS_DIR):
        if fn.endswith('.nsh'):
            shutil.copy(join(NSIS_DIR, fn),
                        join(dir_path, fn))

    print('Created %s file' % nsi_path)
    return nsi_path


def create(info):
    tmp_dir = tempfile.mkdtemp()
    nsi = make_nsi(info, tmp_dir)
    args = [MAKENSIS_EXE, '/V2', nsi]
    print('Calling: %s' % args)
    check_call(args)
    shutil.rmtree(tmp_dir)