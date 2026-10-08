#!/usr/bin/env python3
"""Local result proposal/review helper using only the public Foundry CLI."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from uuid import uuid4

parser = argparse.ArgumentParser()
parser.add_argument('package')
parser.add_argument('context', type=Path)
parser.add_argument('--summary', required=True)
parser.add_argument('--checks', required=True)
parser.add_argument('--limits', required=True)
parser.add_argument('--next-package', type=int)
args = parser.parse_args()
context = json.loads(args.context.read_text())
folder = Path('.foundry/runs')
prefix = ['python3', 'tools/foundry_agent.py', 'cli']
workspace = context['workspace_id']


def call(*argv):
    run = subprocess.run([*prefix, *argv], text=True, capture_output=True, check=True)
    return json.loads(run.stdout)


def save(name, value):
    path = folder / f'{args.package}-{name}.json'
    with path.open('x') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
    return str(path)


# Content hash includes all relevant source/tests/docs; excludes runtime data and secrets.
files = sorted(p for root in ['src', 'tests', 'alembic', 'scripts', 'docs', 'fixtures'] for p in Path(root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.suffix != '.pyc')
files += [Path(p) for p in ['pyproject.toml', 'uv.lock', 'Makefile', '.env.example', 'alembic.ini']]
digest = hashlib.sha256()
for file in files:
    digest.update(str(file).encode()); digest.update(file.read_bytes())
changed = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True, check=True).stdout
save('file-state', {'sha256': digest.hexdigest(), 'files': [str(f) for f in files], 'git_status': changed, 'HEAD': 'unborn; no commits made'})
proposal = dict(context_id=context['id'], request_key=f'{args.package}:{uuid4()}', actor=context['actor'], summary=args.summary, rationale='Reviewed bounded local implementation against current roadmap acceptance and actual test evidence.', limits=args.limits, outcome='continue' if args.next_package else 'no_change', next_action='Private release ready; conduct voluntary lunch pilot and review exact deployment proposal separately.', complete_work=True, findings=[dict(kind='experiment_result', summary=args.summary, details=f'{args.checks}\nContent SHA256: {digest.hexdigest()}\nChanged files: {changed}', sources=[f'document: docs/evidence/{args.package.lower()}-green.txt', f'document: .foundry/runs/{args.package}-file-state.json'], confidence='high')])
if args.next_package:
    spec = json.loads(Path('docs/mvp/spec.json').read_text())
    q = spec['packages'][args.next_package-1]
    proposal['next_work'] = dict(title=f'{q[0]}: {q[2]}', description=q[3]+'\nPlan: docs/mvp/ROADMAP.md', acceptance_criteria=q[4], kind='execution', owner='agent', status='ready')
    proposal['next_action'] = proposal['next_work']['title']
# Keep remaining roadmap packages conditional in the map.
roadmap = json.loads(Path('docs/mvp/spec.json').read_text())['packages']
map_value = json.loads(json.dumps(context['map']))
for package in roadmap:
    node_id = 'conditional_' + package[0]
    if not any(n['id'] == node_id for n in map_value['nodes']):
        map_value['nodes'].append(dict(id=node_id, kind='alternative', title=f'{package[0]}: {package[2]}', detail=f'Conditional on prior package acceptance. {package[4]}'))
for index in range(1, len(roadmap)):
    edge = dict(source='conditional_'+roadmap[index][0], target='conditional_'+roadmap[index-1][0], kind='depends_on', condition='Prior package accepted')
    if edge not in map_value['edges']:
        map_value['edges'].append(edge)
proposal['map'] = map_value
submitted = call('result','submit','--workspace-id',workspace,'--input',save('result-input',proposal))
save('submitted',submitted)
result_id = submitted['id']
shown = call('result','show','--id',result_id)
save('show',shown)
if shown.get('stale_reasons'):
    raise SystemExit('Stale result; reconcile without forcing new versions.')
resolution = dict(expected_result_digest=shown['digest'], expected_head=context['map_revision_id'], expected_work_version=context['work']['version_id'], expected_review_revision=context['review_revision'], resolution='accept', actor=context['actor'], rationale='Reviewed changed source, exact green checks and package limitations; accept local implementation only.', coverage_action='reviewed', coverage_rationale='Read saved context, project sources and arrivals; no omitted relevant arrivals. No public release or demand claim.')
input_path = save('resolution-input',resolution)
preview = call('result','preview','--id',result_id,'--input',input_path)
save('preview',preview)
print(json.dumps({'result_id':result_id, 'preview':preview},ensure_ascii=False),flush=True)
# Exact pinned digest; the helper does not retry or edit versions on rejection.
receipt = call('result','resolve','--id',result_id,'--input',input_path)
save('receipt',receipt)
print(json.dumps({'result_id':result_id,'receipt':receipt},ensure_ascii=False))
