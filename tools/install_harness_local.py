"""Update the existing named Harness package from a reviewed local npm archive."""
import argparse,json,tarfile,hashlib
from pathlib import Path,PurePosixPath
from datetime import datetime


def install(archive,target):
    target=Path(target).resolve();root=Path(__file__).resolve().parents[1]
    if target.name!='dsh-autocad-tcvn' or target.parent.name!='@phamtung17':raise ValueError('Unexpected package target')
    if json.loads((target/'package.json').read_text(encoding='utf-8'))['name']!='@phamtung17/dsh-autocad-tcvn':raise ValueError('Target identity mismatch')
    backup=root/'output'/'harness_backups_v15'/datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True,exist_ok=False)
    copied=[]
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar.getmembers():
            if member.isdir():continue
            if not member.isfile():raise ValueError('Only regular archive files allowed')
            rel=PurePosixPath(member.name)
            if rel.parts[0]!='package' or '..' in rel.parts:raise ValueError('Unsafe npm archive path')
            rel=Path(*rel.parts[1:]);path=(target/rel).resolve()
            if not path.is_relative_to(target):raise ValueError('Unsafe installation path')
            if path.exists():
                saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(path.read_bytes())
            data=tar.extractfile(member).read();path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_name(path.name+'.v15-update');temp.write_bytes(data);temp.replace(path)
            if hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(data).digest():raise ValueError('Copy verification failed')
            copied.append(str(rel))
    report={'status':'LOCAL_PACKAGE_UPDATED_RESTART_REQUIRED','target':str(target),'backup':str(backup),'files':copied,'version':json.loads((target/'package.json').read_text(encoding='utf-8'))['version']}
    (backup/'INSTALL_REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('target');a=p.parse_args();install(a.archive,a.target)
