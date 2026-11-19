"""Bounded development-only experiment decisions, not an autonomous optimizer."""
from .contracts import object_fields, strings, text
from .tailor_benchmark import ARMS, binding, require


def validate_plan(plan):
    object_fields(plan, {'schema_version', 'development_cohort_sha256',
        'test_cohort_sha256', 'development_groups', 'test_groups', 'starting_variant_sha256',
        'allowed_levers', 'max_rounds', 'max_free_seconds', 'prior_free_seconds',
        'cumulative_cap_seconds', 'stop_after_non_improving'}, set(), 'hill-climb plan')
    require(plan['schema_version'] == '1.0', 'Unsupported hill-climb plan')
    for key in ('development_cohort_sha256', 'test_cohort_sha256', 'starting_variant_sha256'):
        value = plan[key]
        require(isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value),
                'Expected bound SHA256: '+key)
    require(plan['development_cohort_sha256'] != plan['test_cohort_sha256'],
            'Development and test cannot be the same frozen benchmark')
    dev = strings(plan['development_groups'], 'development source families')
    test = strings(plan['test_groups'], 'test source families')
    require(dev and test and not set(dev) & set(test), 'Keep development and test families disjoint')
    levers = strings(plan['allowed_levers'], 'allowed levers')
    require(len(levers) == 1 and set(levers) <= {'prompt', 'training'},
            'Freeze one lever family: prompt or training')
    for key in ('max_rounds', 'max_free_seconds', 'cumulative_cap_seconds', 'stop_after_non_improving'):
        require(type(plan[key]) is int and plan[key] > 0, 'Expected positive integer '+key)
    require(plan['max_rounds'] <= 10, 'Limit study to at most ten preregistered rounds')
    require(type(plan['prior_free_seconds']) in (int, float) and
            0 <= plan['prior_free_seconds'] <= plan['cumulative_cap_seconds'], 'Invalid prior usage')
    require(plan['prior_free_seconds'] + plan['max_free_seconds'] <= plan['cumulative_cap_seconds'],
            'New budget exceeds cumulative free-compute cap')
    return plan


def record_round(plan, history, proposal, report):
    """Assess one captured dev comparison. Never executes or changes the winner's source."""
    validate_plan(plan)
    require(isinstance(history, list) and len(history) < plan['max_rounds'], 'Round budget exhausted')
    # Stored rounds bind the plan; edits/reordering cannot silently reset usage or parents.
    parent = plan['starting_variant_sha256']; spent = 0; flat = 0
    for index, old in enumerate(history, 1):
        require(old.get('plan_sha256') == binding(plan) and old.get('round') == index,
                'History belongs to another plan or is reordered')
        require(old.get('parent_variant_sha256') == parent, 'History parent chain changed')
        require(type(old.get('free_seconds')) in (int, float) and 0 < old['free_seconds'] <= plan['max_free_seconds'],
                'History has invalid spent time')
        spent += old['free_seconds']
        require(spent <= plan['max_free_seconds'] and
                old.get('cumulative_free_seconds') == plan['prior_free_seconds']+spent,
                'History spent time was changed or exceeded the budget')
        require(old.get('decision') in {'keep_candidate_for_final_test', 'reject_regression',
                'inconclusive_keep_parent'}, 'Unknown history decision')
        if old['decision'] == 'keep_candidate_for_final_test':
            parent = old['variant_sha256']; flat = 0
        else:
            flat += 1
    require(flat < plan['stop_after_non_improving'], 'Non-improvement stop reached')
    object_fields(proposal, {'parent_variant_sha256', 'variant_sha256', 'lever',
        'hypothesis', 'changed_files', 'free_seconds'}, set(), 'round proposal')
    require(proposal['parent_variant_sha256'] == parent, 'Compare against current development winner')
    text(proposal['variant_sha256'], 'candidate variant binding')
    require(len(proposal['variant_sha256']) == 64 and
            all(c in '0123456789abcdef' for c in proposal['variant_sha256']) and
            proposal['variant_sha256'] != parent, 'Bind a genuinely changed candidate')
    require(proposal['lever'] in plan['allowed_levers'], 'Change one allowed lever per round')
    text(proposal['hypothesis'], 'failure-based hypothesis')
    require(strings(proposal['changed_files'], 'reviewable changed files'), 'Capture a focused diff')
    seconds = proposal['free_seconds']
    require(type(seconds) in (int, float) and 0 < seconds <= plan['max_free_seconds']-spent,
            'Invalid observed time or exhausted free budget')
    require(report.get('kind') == 'tailor_benchmark_comparison' and
            report.get('cohort_sha256') == plan['development_cohort_sha256'],
            'Hill-climb may consume only the frozen development benchmark, never the test set')
    require(report.get('all_outputs_human_reviewed') is True, 'Complete human development reviews required')
    require(report.get('comparison') == proposal['lever'], 'Report and single changed lever differ')
    expected = ARMS if proposal['lever'] == 'training' else ARMS[:2]
    require(set(report.get('arms', {})) == set(expected), 'Expected matched comparison conditions')
    if proposal['lever'] == 'prompt':
        require(proposal['variant_sha256'] == report['candidate_system_sha256'] and
                parent == report['baseline_system_sha256'], 'Prompt parent/candidate binding differs')
    else:
        require(not history, 'Fresh base training comparison is one round; never silently resume a prior adapter')
        require(proposal['variant_sha256'] == report['candidate_adapter_sha256'], 'Adapter binding differs')
    candidate = report['arms'][report['candidate_condition']]
    baseline = report['arms'][expected[0] if proposal['lever'] == 'prompt' else 'base_evidence']
    safe = (candidate['invalid_or_missing'] == 0 and candidate['factuality_failures'] == 0 and
            candidate['scope_failures'] == 0 and candidate['qualifier_failures'] == 0 and
            candidate['passed'] >= baseline['passed'])
    ci = report.get('paired_cluster_bootstrap_95_interval')
    gain = report['primary_quality_delta']
    keep = safe and gain >= 0.25 and ci is not None and ci[0] > 0
    decision = ('keep_candidate_for_final_test' if keep else
                'reject_regression' if not safe or gain < 0 else 'inconclusive_keep_parent')
    return {'schema_version': '1.0', 'round': len(history)+1, 'plan_sha256': binding(plan),
        'parent_variant_sha256': parent, 'variant_sha256': proposal['variant_sha256'],
        'lever': proposal['lever'], 'hypothesis': proposal['hypothesis'],
        'changed_files': proposal['changed_files'], 'free_seconds': seconds,
        'cumulative_free_seconds': plan['prior_free_seconds']+spent+seconds,
        'report_sha256': binding(report), 'decision': decision,
        'observed_development_delta': gain, 'test_consumed': False,
        'promotion_performed': False, 'application_authority': False}


def final_test(plan, history, report):
    """Return a final test report; caller must save once using exclusive creation."""
    validate_plan(plan)
    require(history and all(r['plan_sha256'] == binding(plan) for r in history), 'No bound development history')
    require(report.get('cohort_sha256') == plan['test_cohort_sha256'], 'Wrong final benchmark')
    accepted = [r for r in history if r['decision'] == 'keep_candidate_for_final_test']
    require(accepted, 'No development winner qualified for a final test')
    identity = (report['candidate_system_sha256'] if plan['allowed_levers'] == ['prompt']
                else report['candidate_adapter_sha256'])
    require(identity == accepted[-1]['variant_sha256'], 'Final test uses a different selected candidate')
    return {'schema_version': '1.0', 'kind': 'hillclimb_final_test',
        'plan_sha256': binding(plan), 'selected_variant_sha256': accepted[-1]['variant_sha256'],
        'test_report_sha256': binding(report),
        'candidate_experiment_gate_met': report['candidate_experiment_gate_met'],
        'test_consumed': True, 'model_promoted': False, 'application_authority': False,
        'note': 'Once inspected, this test is exposed. Another tuning round requires a new prospective test cohort.'}
