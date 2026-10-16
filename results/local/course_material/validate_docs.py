from pathlib import Path
import json, re, hashlib, sys
from collections import Counter
from pypdf import PdfReader
root = Path(r'D:\VuLapTrinh2\RecSysEdu')
source_dir = Path(r'D:\TÀI LIỆU HỌC\Hệ gợi ý')
errors = []
md_files = [root/'README.md', root/'CONTRIBUTING.md']
for folder in ('docs', 'tasks', 'results'):
    md_files += [p for p in (root/folder).rglob('*.md') if 'local' not in p.relative_to(root/folder).parts]
link_count = 0
for p in md_files:
    body = p.read_text(encoding='utf-8-sig')
    for match in re.finditer(r'(?<!!)\[[^\]]+\]\(([^\s)]+)\)', body):
        target = match.group(1).strip('<>')
        if re.match(r'^[a-z]+://', target) or target.startswith('#'):
            continue
        target = target.split('#',1)[0]
        if not target:
            continue
        link_count += 1
        if not (p.parent/target).exists():
            errors.append(f'missing link: {p.relative_to(root)} -> {target}')
manifest = json.loads((root/'docs/reference/course_material_manifest.json').read_text(encoding='utf-8'))
page_sum = visual_sum = 0
for item in manifest['sources']:
    p = source_dir/item['filename']
    if not p.exists():
        errors.append('missing PDF: '+item['filename']); continue
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    pages = len(PdfReader(p).pages)
    page_sum += pages
    if sha != item['sha256'] or pages != item['pages']:
        errors.append('PDF hash/pages mismatch: '+item['code'])
    used = set()
    for part in item['used_pdf_pages'].split(','):
        bounds = [int(n) for n in part.split('-')]
        used.update(range(bounds[0], bounds[-1]+1))
    visual = item['visually_checked_pdf_pages']
    visual_sum += len(visual)
    if not used or min(used)<1 or max(used)>pages or any(n not in used for n in visual):
        errors.append('invalid PDF page reference: '+item['code'])
if len(manifest['sources']) != 11 or page_sum != manifest['total_pages'] or page_sum != 367 or visual_sum != 9:
    errors.append('source counts mismatch')
schedule = (root/'tasks/six_week_schedule.md').read_text(encoding='utf-8')
days = re.findall(r'^\| (D\d\d) \|', schedule, re.M)
if days != [f'D{i:02d}' for i in range(1,31)]:
    errors.append('D01-D30 missing/duplicate/out of order')
plan = (root/'tasks/plan.md').read_text(encoding='utf-8')
tasks = re.findall(r'^## (M\d+(?:[ab])?)\b', plan, re.M)
expected_tasks = ['M0','M1','M2','M3','M4','M5','M6','M7','M8','M9a','M9b','M10','M11','M12']
if tasks != expected_tasks:
    errors.append('M-task set mismatch: '+repr(tasks))
counts = Counter()
raw = root/'data/raw/course.json'
with raw.open(encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        course = json.loads(line)
        counts['courses'] += 1
        for field in ('name','about'):
            value = course.get(field)
            counts[field+'_type_'+type(value).__name__] += 1
            if isinstance(value,str) and value.strip():
                counts[field+'_nonempty'] += 1
                if re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]',value): counts[field+'_cjk'] += 1
        if course.get('field'): counts['field_nonempty'] += 1
expected_counts = {'courses':3781,'name_nonempty':3781,'about_nonempty':3692,'name_cjk':3398,'about_cjk':3227,'field_nonempty':547,'about_type_str':3779,'about_type_NoneType':2}
for key, value in expected_counts.items():
    if counts[key] != value: errors.append(f'metadata count mismatch: {key}: {counts[key]} != {value}')
metadata = {'checked_on':'2026-10-09','source':'data/raw/course.json','source_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'method':'JSON Lines scan; nonempty = string.strip() is nonempty; field_nonempty = nonempty raw field; CJK = U+3400-4DBF/U+4E00-9FFF/U+F900-FAFF. Coverage is not semantic quality.','counts':dict(counts)}
if not errors:
    (root/'results/course_metadata_audit.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
result = {'status':'PASS' if not errors else 'FAIL','markdown_files':len(md_files),'internal_file_links':link_count,'pdf_sources':len(manifest['sources']),'source_pages':page_sum,'visually_checked_pages':visual_sum,'schedule_days':len(days),'tasks':len(tasks),'metadata_verified':dict(counts),'errors':errors}
(root/'results/local/course_material/docs_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(bool(errors))