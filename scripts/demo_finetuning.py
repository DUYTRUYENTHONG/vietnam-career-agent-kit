"""Explicit tiny real-model training smoke using FICTIONAL reviewed examples only."""
import argparse
from copy import deepcopy
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.local_finetuning import train
from core.learning import export_reviewed
from scripts.demo_wording import seed, fictional_review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True, help='New empty fictional workspace')
    parser.add_argument('--model-directory', required=True)
    args = parser.parse_args()
    work, model = seed(Path(args.data_dir))
    work.import_wording(1, model)
    work.review_wording(1, fictional_review(work.wording_packet(1).data))
    packet = work.wording_packet(1).data
    job, _ = work.job_document(1)
    other = deepcopy(job)
    other.update(platform_job_id=job['platform_job_id']+'-second', req_id=job['req_id']+'-second',
                 url=job['url']+'/second')
    work.import_job(other)
    work.assess(2, {'schema_version': '1.0', 'rows': packet['assessment']['rows']})
    model = deepcopy(model); model['job_id'] = 2
    for section in model['sections']:
        for group in section['groups']:
            for statement in group['statements']:
                if 'F1' in statement['source_fact_ids']:
                    statement.update(text='Used SQL to query a fictional sales dataset.',
                                     transformation='faithful_paraphrase')
    work.import_wording(2, model)
    work.review_wording(2, fictional_review(work.wording_packet(2).data))
    export_reviewed(work, [1, 2], 'datasets/fictional')
    result = train(work, 'datasets/fictional', args.model_directory, 'training/smoke',
                   target_modules=['q_proj', 'v_proj'], epochs=1, max_length=2048)
    print('FICTIONAL smoke completed; this is not candidate-model quality evidence.')
    print({'training_ms': result['training_ms'], 'baseline': result['baseline'],
           'adapter': result['epochs_evaluation'][-1]})
    from adapters.local_qwen import generate
    generated = generate(args.model_directory, [
        {'role': 'system', 'content': 'Return JSON only. Never invent candidate facts.'},
        {'role': 'user', 'content': 'Fictional fact: Used SQL to query a fictional sales dataset. Return one faithful CV bullet as JSON.'}],
        adapter_directory=work.inside('training/smoke/adapter'), max_new_tokens=64)
    work.inside('training/smoke/inference-smoke.json').write_text(
        json.dumps(generated, indent=2, ensure_ascii=False), encoding='utf8')
    print({key: generated[key] for key in ('input_tokens', 'output_tokens', 'generation_ms', 'review_required')})


if __name__ == '__main__':
    main()
