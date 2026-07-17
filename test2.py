from runner import *
from config import *
import json, re

corpus = load_corpus()
tasks = load_tasks()
exhibits = load_exhibits()
ladder = json.load(open(LADDER_PATH))
tasks_map = {t['id']: t for t in tasks}

task = tasks[0]
level = ladder['levels'][0]

relevant_ids = task.get('relevant_cases', [])
if level['corpus_filter'] == 'relevant':
    filtered_corpus = {'cases': [c for c in corpus['cases'] if c['id'] in relevant_ids]}
else:
    filtered_corpus = corpus

gt = load_ground_truth()
gt_task = gt.get(task['id'], {})
relevant_ex = gt_task.get('relevant_exhibits', [])
if level['exhibit_filter'] == 'relevant':
    filtered_exhibits = {'exhibits': [e for e in exhibits['exhibits'] if e['id'] in relevant_ex]}
else:
    filtered_exhibits = exhibits

all_ids = [c['id'] for c in filtered_corpus['cases']]
corpus_ctx = build_corpus_context(filtered_corpus, {'relevant_cases': all_ids})
exhibit_ctx = build_exhibit_context(filtered_exhibits)
parties_ctx = build_parties_context(task, level)
elements_ctx = task.get('required_elements', '')
sumf_ctx = task.get('sumf', '')
defense_ctx = task.get('defense_positions', '')

for label, tmpl in [('base_prompt', task['base_prompt']), ('instruct_prompt', task['instruct_prompt'])]:
    p = tmpl
    p = p.replace('[CORPUS]', corpus_ctx)
    p = p.replace('[EXHIBIT POOL]', exhibit_ctx)
    p = p.replace('[REQUIRED ELEMENTS]', elements_ctx)
    p = p.replace('[SUMF]', sumf_ctx)
    p = p.replace('[DEFENSE POSITIONS]', defense_ctx)
    p = p.replace('[PARTIES]', parties_ctx)
    remaining = re.findall(r'\[[A-Z ]+\]', p)
    if remaining:
        print(f'WARNING {label}: unresolved placeholders: {remaining}')
    else:
        print(f'OK {label}: no unresolved placeholders')
    print(f'   {len(p)} chars, ~{len(p.split())} words')
    print(f'   First 200: {p[:200]}')
    print()

print('Test 2 done.')
