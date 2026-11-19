"""Requirement-only lexical shortcut diagnostic; not a joint evidence baseline."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.evidence_pairing import LABELS, strict_json
from scripts.evidence_bench import examples, load_cases


def tokens(text):
    return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())


def fit(rows):
    """Only requirement text and training labels enter this diagnostic."""
    counts = {label: Counter() for label in LABELS}
    priors = Counter()
    by_requirement = defaultdict(Counter)
    for text, label in rows:
        if label not in LABELS:
            raise ValueError('Invalid label')
        counts[label].update(tokens(text))
        priors[label] += 1
        by_requirement[' '.join(tokens(text))][label] += 1
    if not priors:
        raise ValueError('Empty training input')
    vocabulary = set().union(*(set(c) for c in counts.values()))
    return counts, priors, vocabulary, by_requirement


def predict(model, text):
    counts, priors, vocabulary, _ = model
    observed = Counter(t for t in tokens(text) if t in vocabulary)
    total = sum(priors.values())
    scores = {}
    for label in LABELS:
        score = math.log((priors[label] + 1) / (total + len(LABELS)))
        denominator = sum(counts[label].values()) + len(vocabulary)
        for token, n in observed.items():
            score += n * math.log((counts[label][token] + 1) / denominator)
        scores[label] = score
    return max(LABELS, key=lambda label: scores[label])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training', required=True, type=Path)
    parser.add_argument('--benchmark', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use fresh output directory')
    start = time.perf_counter()
    rows = []
    for line in args.training.read_text(encoding='utf8').splitlines():
        row = strict_json(line)
        user = strict_json(row['messages'][1]['content'])
        answer = strict_json(row['messages'][2]['content'])
        rows.append((user['requirement'], answer['label']))
    model = fit(rows)
    selected = examples(load_cases(args.benchmark), 'development')
    if not selected:
        raise ValueError('Empty development split')
    majority = max(LABELS, key=lambda label: model[1][label])
    predictions = []
    for case, requirement, _facts_unused, gold in selected:
        predictions.append({'case': case, 'requirement_id': requirement['id'],
            'gold_label': gold['label'], 'predicted_label': predict(model, requirement['text']),
            'majority_label': majority})
    grouped = model[3]
    ambiguous = {text: counts for text, counts in grouped.items() if len(counts) > 1}
    report = {'task': 'requirement-only label shortcut diagnostic',
        'scope': 'synthetic training and reused development only; not independent test',
        'uses_evidence': False, 'joint_evidence_score': None,
        'training_rows': len(rows), 'unique_normalized_requirements': len(grouped),
        'requirements_with_multiple_gold_labels': len(ambiguous),
        'rows_in_ambiguous_requirements': sum(sum(c.values()) for c in ambiguous.values()),
        'training_requirement_lookup_label_ceiling': sum(max(c.values()) for c in grouped.values()) / len(rows),
        'development_n': len(predictions),
        'development_label_accuracy': sum(r['predicted_label'] == r['gold_label'] for r in predictions) / len(predictions),
        'majority_label_accuracy': sum(r['majority_label'] == r['gold_label'] for r in predictions) / len(predictions),
        'method': 'multinomial naive Bayes, unigram Unicode words, Laplace alpha1; no tuning',
        'training_sha256': hashlib.sha256(args.training.read_bytes()).hexdigest(),
        'benchmark_sha256': hashlib.sha256(args.benchmark.read_bytes()).hexdigest(),
        'elapsed_ms': (time.perf_counter() - start) * 1000,
        'limitation': 'A low lexical score does not exclude semantic or other shortcuts.'}
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / 'predictions.jsonl').open('w', encoding='utf8') as stream:
        for row in predictions:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
