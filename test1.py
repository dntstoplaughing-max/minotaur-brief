import json

files = ['corpus.json','prompts/tasks.json','prompts/context_ladder.json','prompts/ground_truth.json','prompts/exhibit_pool.json']
for f in files:
    json.load(open(f, encoding='utf-8'))
    print(f'  OK: {f}')

from config import *
print(f'  BASE_MODEL: {BASE_MODEL}')
print(f'  INSTRUCT_MODEL: {INSTRUCT_MODEL}')
print(f'  TEMPERATURE: {TEMPERATURE}')
print(f'  RUNS_PER_CONDITION: {RUNS_PER_CONDITION}')

from runner import load_corpus, load_tasks, load_exhibits, load_ground_truth
tasks = load_tasks()
corpus = load_corpus()
exhibits = load_exhibits()
gt = load_ground_truth()
print(f'  Tasks: {len(tasks)}')
print('  Cases:', len(corpus['cases']))
print('  Statutes:', len(corpus['statutes']))
print('  Exhibits:', len(exhibits['exhibits']))
print('  Ground truth keys:', list(gt.keys()))

ladder = json.load(open(LADDER_PATH))
for lvl in ladder['levels']:
    print('  Level', lvl['name'], 'max_tokens='+str(lvl.get('max_tokens',4096)), 'corpus='+lvl['corpus_filter'], 'exhibits='+lvl['exhibit_filter'], 'cross='+str(lvl.get('cross_count',False)))

print('\nAll imports OK.')
