"""Validate frontmatter and discovery roots using DSH filesystem provider rules."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]

def discover(root):
    entries={}
    for folder in (root/'skills',root/'skills'/'disciplines'):
        for child in folder.iterdir():
            file=child/'SKILL.md' if child.is_dir() else child if child.suffix=='.md' else None
            if not file or not file.is_file():continue
            text=file.read_text(encoding='utf-8')
            if not text.startswith('---\n') or '\n---\n' not in text[4:]:
                raise RuntimeError(f'Invalid frontmatter: {file}')
            head=text.split('---',2)[1]
            name=re.search(r'^name:\s*([^\n]+)',head,re.M)
            desc=re.search(r'^description:\s*([^\n]+)',head,re.M)
            if not name or not desc:raise RuntimeError(f'Missing required metadata: {file}')
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name.group(1)):
                raise RuntimeError(f'Skill name must use kebab-case: {name.group(1)}')
            if name.group(1) in entries:raise RuntimeError(f'Duplicate skill: {name.group(1)}')
            entries[name.group(1)]=str(file.relative_to(root))
    if len(entries)!=10:raise RuntimeError(f'Expected 10 skills, discovered {len(entries)}')
    return entries

if __name__=='__main__':
    import json
    print(json.dumps({'status':'ROOT_STRUCTURE_CHECKED_ONLY','skills':discover(ROOT),
    'note':'Actual DSH discovery and tool loader still need a live DSH run.'},ensure_ascii=False,indent=2))
