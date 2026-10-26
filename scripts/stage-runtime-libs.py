"""Stage CPython's extra shared libraries and their Debian package records.

Distroless cc already supplies libc, libstdc++, OpenSSL, zlib and libzstd.
Interactive readline/curses/uuid helper libraries are not used by serving.
"""
import shutil
import subprocess
from pathlib import Path


def stage(output):
    records = output / 'var/lib/dpkg/status.d'
    records.mkdir(parents=True, exist_ok=True)
    for package in ('libbz2-1.0', 'libdb5.3t64', 'libffi8', 'liblzma5', 'libsqlite3-0'):
        listing = subprocess.check_output(['dpkg-query', '-L', package], text=True).splitlines()
        libraries = [Path(name) for name in listing if '.so' in Path(name).name and Path(name).is_file()]
        if not libraries:
            raise RuntimeError(f'No runtime libraries found for {package}')
        for source in libraries:
            # Debian 13 uses merged-/usr; avoid replacing Distroless's /lib symlink.
            relative = source.relative_to('/')
            if relative.parts[0] == 'lib':
                relative = Path('usr') / relative
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination, follow_symlinks=True)
        copyright_file = Path('/usr/share/doc') / package / 'copyright'
        if copyright_file.is_file():
            destination = output / copyright_file.relative_to('/')
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(copyright_file, destination)
        # Preserve full control records; copying binaries without inventory would
        # hide OS advisories from scanners instead of resolving their cause.
        (records / package).write_text(subprocess.check_output(
            ['dpkg-query', '--status', package], text=True) + '\n', encoding='utf-8')


if __name__ == '__main__':
    stage(Path('/runtime-root'))
