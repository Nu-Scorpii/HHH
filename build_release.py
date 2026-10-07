"""Build a single-file deployment from the readable, canonical source files."""

from pathlib import Path
import zipfile

ENTRYPOINT = '''import sys
if len(sys.argv) > 1 and sys.argv[1] == "backup":
    del sys.argv[1]
    from backup import main
else:
    from ua_bot.__main__ import main
main()
'''


def build(root=None, destination=None):
    root = Path(root or Path(__file__).resolve().parent)
    destination = Path(destination or root/'bot.pyz')
    sources = sorted((root/'ua_bot').glob('*.py')) + [root/'backup.py']
    for source in sources:
        compile(source.read_text(encoding='utf-8'),str(source),'exec')
    handbook = root/'docs'/'PLAYER_HANDBOOK.md'
    if not handbook.is_file():
        raise ValueError('The player handbook is missing from the source project.')
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        archive.writestr('__main__.py',ENTRYPOINT)
        for source in sources:
            archive.write(source,source.relative_to(root).as_posix())
        archive.write(handbook,'ua_bot/PLAYER_HANDBOOK.md')
    return destination


if __name__ == '__main__':
    artifact = build()
    print(f'Built {artifact.name}; {artifact.stat().st_size:,} bytes. Upload it with Dockerfile, requirements.txt, and railway.toml.')
