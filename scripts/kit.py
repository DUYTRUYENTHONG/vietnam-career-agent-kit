#!/usr/bin/env python3
"""Local CLI. All operation results use the versioned outcome envelope."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
from typing import Sequence

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.contracts import ContractError, Outcome
from core.ledger import ACTIONS, ConcurrentWrite, Kit, PackageError
from core.runtime import diagnose
from core.workflow import Preparation, WorkflowError
from core.manifests import Campaign
from core.execution import Executor


class Parser(argparse.ArgumentParser):
    def error(self,message):
        raise ContractError(message+'; use --help for the exact command syntax')


def parser() -> Parser:
    root=Parser(description=__doc__)
    root.add_argument('--data-dir',type=Path,help='explicit private directory outside the public clone')
    root.add_argument('--actor',default='local-user')
    commands=root.add_subparsers(dest='command',required=True)
    for name in ('discover-greenhouse','discover-ashby'):
        discover=commands.add_parser(name,help='bounded public board GETs; leads only, no candidate data or submission')
        discover.add_argument('--board',action='append',required=True)
        discover.add_argument('--workers',type=int,default=3)
        discover.add_argument('--include-content',action='store_true',help='include full untrusted descriptions; default returns compact leads')
    doctor=commands.add_parser('doctor',help='read-only runtime diagnosis; no account/browser connection')
    doctor.add_argument('--runtime',choices=['generic','codex','claude','grok'],default='generic')
    commands.add_parser('provider-doctor',help='offline provider configuration; never checks keys remotely')
    web_bench=commands.add_parser('benchmark-web',help='fictional transport benchmark; never calls a provider')
    web_bench.add_argument('--samples',type=int,default=7)
    web_bench.add_argument('--latency-ms',type=int,default=30)
    tiny=commands.add_parser('tinyfish-fetch',help='opt-in public batch fetch of 1-10 URLs; preview by default')
    tiny.add_argument('--plan',type=Path,required=True)
    tiny.add_argument('--live',action='store_true')
    tiny.add_argument('--approve-plan')
    browser=commands.add_parser('tinyfish-browser',help='experimental isolated browser runner; offline preview by default')
    browser.add_argument('--run-id',required=True)
    browser.add_argument('--forms',type=Path,required=True)
    browser.add_argument('--cloud-scope',type=Path,required=True)
    browser.add_argument('--approve-cloud-scope')
    browser.add_argument('--action-timeout-seconds',type=float,default=120)
    browser.add_argument('--live',action='store_true')
    research=commands.add_parser('discover',help='opt-in bounded Firecrawl public research; dry-run by default')
    research.add_argument('--plan',type=Path,required=True)
    mode=research.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--live',action='store_true')
    research.add_argument('--approve-plan',help='exact reviewed public-plan fingerprint; not application approval')
    research.add_argument('--individual',action='store_true',help='individual scrape comparison instead of batch')
    for name in ['research-status','cancel-research','research-report']:
        research_cmd=commands.add_parser(name)
        research_cmd.add_argument('--fingerprint',required=True)
    research_import=commands.add_parser('import-research-jd',help='review normalized claims against captured private evidence')
    research_import.add_argument('--evidence-id',required=True)
    research_import.add_argument('--file',type=Path,required=True)
    route=commands.add_parser('route-task',help='deterministic model/tool plan; no model call or workspace access')
    route.add_argument('--packet',type=Path,required=True)
    performance=commands.add_parser('performance-record',help='import one source-bound per-call usage observation; no model/API call')
    performance.add_argument('--file',type=Path,required=True)
    performance=commands.add_parser('performance-report',help='private per-model timing/token coverage; unknown usage is not zero')
    performance.add_argument('--model-id')
    performance.add_argument('--phase')
    performance.add_argument('--workload-id')
    performance.add_argument('--format',choices=['json','md','csv'],default='json')
    performance.add_argument('--output',help='new snapshot path inside reports/performance/')
    outcome=commands.add_parser('outcome-record',help='record one private recruiter observation bound to a frozen confirmed CV')
    outcome.add_argument('--file',type=Path,required=True)
    outcome=commands.add_parser('outcome-report',help='age-scoped descriptive recruitment outcomes by exact submitted CV; no causal ranking')
    outcome.add_argument('--min-age-days',type=int,default=14)
    outcome.add_argument('--as-of')
    outcome.add_argument('--job-id',type=int,action='append')
    context=commands.add_parser('career-context',help='retrieve cited current confirmed facts; experimental local BM25')
    context.add_argument('--query',required=True)
    context.add_argument('--limit',type=int,default=5)
    context.add_argument('--max-chars',type=int,default=6000)
    context=commands.add_parser('career-email-context',help='prepare an English/Vietnamese email writing brief, never send')
    context.add_argument('--job-id',type=int,required=True)
    context.add_argument('--language',choices=['en','vi'],default='en')
    context.add_argument('--limit',type=int,default=5)
    context=commands.add_parser('career-writing-brief',help='prepare a cited CV/email writing contract without inference')
    context.add_argument('--job-id',type=int,required=True)
    context.add_argument('--kind',choices=['email','cv'],default='email')
    context.add_argument('--language',choices=['en','vi'],default='en')
    context.add_argument('--limit',type=int,default=5)
    context=commands.add_parser('career-check-draft',help='check current draft citations, not semantic truth or approval')
    context.add_argument('--file',type=Path,required=True,help='private JSON with request and draft')
    context=commands.add_parser('career-evaluate',help='evaluate labelled queries and a token-overlap baseline locally')
    context.add_argument('--file',type=Path,required=True)
    learning=commands.add_parser('learning-export',help='export only independently reviewed current CV wording; no training/upload')
    learning.add_argument('--job-id',type=int,action='append',required=True)
    learning.add_argument('--output',required=True,help='new datasets/ subdirectory in the private workspace')
    learning=commands.add_parser('learning-check',help='recheck dataset bytes, evidence, reviews and split consistency')
    learning.add_argument('--directory',required=True)
    for name in ['growth-context','growth-capture']:
        growth=commands.add_parser(name,help='explicit local assessment-gap context or capture; no model call or fact promotion')
        growth.add_argument('--job-id',type=int,action='append',required=True)
    growth=commands.add_parser('growth-plan',help='import a private source-bound learning plan; never changes CV facts')
    growth.add_argument('--file',type=Path,required=True)
    growth=commands.add_parser('growth-review',help='record review of an exact learning plan; no application authority')
    growth.add_argument('--fingerprint',required=True)
    growth.add_argument('--file',type=Path,required=True)
    growth=commands.add_parser('growth-check',help='revalidate a learning plan and current assessment evidence')
    growth.add_argument('--fingerprint',required=True)
    growth=commands.add_parser('growth-evidence',help='record a private learning artifact; never promotes candidate facts')
    growth.add_argument('--fingerprint',required=True)
    growth.add_argument('--action-id',required=True)
    growth.add_argument('--artifact',required=True)
    growth.add_argument('--note',required=True)
    growth=commands.add_parser('growth-export',help='export reviewed learning plans privately; no training or upload')
    growth.add_argument('--fingerprint',action='append',required=True)
    growth.add_argument('--output',required=True)
    growth=commands.add_parser('growth-check-export',help='revalidate a private reviewed learning-plan export')
    growth.add_argument('--directory',required=True)
    init=commands.add_parser('init',help='additive local workspace initialization')
    init.add_argument('--language',choices=['en','vi'],default='en')
    starter=commands.add_parser('start-campaign',help='create private CV intake and a default 100-application goal; no extraction or submission')
    starter.add_argument('--cv',type=Path,required=True)
    starter.add_argument('--target',type=int,default=100)
    starter.add_argument('--language',choices=['en','vi'],default='en')
    for name in ['status','profile','resume','source-registry']:
        commands.add_parser(name)
    cv=commands.add_parser('import-cv',help='copy an explicitly supplied UTF-8 TXT/Markdown CV into private evidence')
    cv.add_argument('--file',type=Path,required=True);cv.add_argument('--source-id',required=True)
    for name in ['import-profile','import-jd']:
        cmd=commands.add_parser(name);cmd.add_argument('--file',type=Path,required=True)
    confirm=commands.add_parser('confirm-profile')
    confirm.add_argument('--fingerprint',required=True);confirm.add_argument('--confirmation',type=Path,required=True)
    for name,flag in [('assess','matrix'),('prepare','plan')]:
        cmd=commands.add_parser(name);cmd.add_argument('--job-id',type=int,required=True)
        cmd.add_argument('--'+flag,type=Path,required=True)
        if name=='assess':cmd.add_argument('--capture-growth',action='store_true',help='capture local learning gaps only after a successful saved assessment')
    handoff=commands.add_parser('handoff');handoff.add_argument('--job-id',type=int,required=True)
    for name in ['import-wording','wording-packet','review-wording']:
        cmd=commands.add_parser(name,help='local opt-in source-bound v2 wording; no model call or disclosure')
        cmd.add_argument('--job-id',type=int,required=True)
        if name!='wording-packet':cmd.add_argument('--file',type=Path,required=True)
        if name=='import-wording':cmd.add_argument('--include-review-packet',action='store_true',help='return the same fresh packet in this CLI call')
    reject_wording=commands.add_parser('reject-wording',help='invalidate factual review and dependent current renders')
    reject_wording.add_argument('--job-id',type=int,required=True);reject_wording.add_argument('--reason',required=True)
    duplicates=commands.add_parser('duplicate-candidates',help='read-only same-employer identity hints; never merges or clears a job')
    duplicates.add_argument('--job-id',type=int,required=True)
    render=commands.add_parser('render',help='local DOCX/PDF conversion and page previews; no external disclosure')
    render.add_argument('--job-id',type=int,required=True);render.add_argument('--soffice',type=Path)
    review=commands.add_parser('review-documents');review.add_argument('--render-id',required=True)
    review.add_argument('--review',type=Path,required=True)
    reject=commands.add_parser('reject-documents');reject.add_argument('--render-id',required=True)
    reject.add_argument('--reason',required=True)
    manifest=commands.add_parser('create-manifest');manifest.add_argument('--plan',type=Path,required=True)
    approve=commands.add_parser('approve-manifest');approve.add_argument('--fingerprint',required=True)
    approve.add_argument('--confirmation',type=Path,required=True)
    check=commands.add_parser('check-manifest');check.add_argument('--fingerprint',required=True)
    check.add_argument('--intent',type=Path)
    revoke_manifest=commands.add_parser('revoke-manifest');revoke_manifest.add_argument('--fingerprint',required=True)
    revoke_manifest.add_argument('--reason',required=True)
    delegation=commands.add_parser('create-authorization',help='prepare an opt-in bounded standing campaign scope')
    delegation.add_argument('--plan',type=Path,required=True)
    for name in ['approve-authorization','check-authorization','revoke-authorization']:
        cmd=commands.add_parser(name);cmd.add_argument('--fingerprint',required=True)
        if name=='approve-authorization':cmd.add_argument('--confirmation',type=Path,required=True)
        if name=='revoke-authorization':cmd.add_argument('--reason',required=True)
    delegated=commands.add_parser('authorize-manifest',help='derive exact reviewed authority within an approved standing scope')
    delegated.add_argument('--fingerprint',required=True);delegated.add_argument('--authorization',required=True)
    start=commands.add_parser('start-execution',help='opt in to an exact approved host-browser scope; does not acquire a browser')
    start.add_argument('--fingerprint',required=True)
    start.add_argument('--bridge-id',required=True)
    start.add_argument('--runtime-minutes',type=int,required=True)
    parallel=commands.add_parser('start-parallel-execution',help='start up to ten isolated host-browser lanes; no browser acquired')
    parallel.add_argument('--fingerprint',required=True)
    parallel.add_argument('--bridge-id',required=True)
    parallel.add_argument('--runtime-minutes',type=int,required=True)
    parallel.add_argument('--workers',type=int,default=10)
    browser_act=commands.add_parser('browser-act-plan',help='offline session/state plan for an issued request; never launches a browser')
    browser_act.add_argument('--run-id',required=True)
    browser_act.add_argument('--request-id',required=True)
    browser_act.add_argument('--browser-id',required=True)
    for name in ['parallel-cleanup','record-parallel-cleanup','parallel-status','next-parallel-action','record-parallel-action','check-parallel-action','recover-parallel-execution','stop-parallel-execution']:
        cmd=commands.add_parser(name);cmd.add_argument('--run-id',required=True)
        if name in {'next-parallel-action','recover-parallel-execution'}:cmd.add_argument('--job-id',type=int,required=True)
        if name in {'record-parallel-action','record-parallel-cleanup'}:cmd.add_argument('--receipt',type=Path,required=True)
        if name=='check-parallel-action':cmd.add_argument('--request-id',required=True)
        if name=='stop-parallel-execution':cmd.add_argument('--reason',required=True)
    launch=commands.add_parser('launch-execution',help='reuse standing authority, start and return the first guarded request')
    launch.add_argument('--fingerprint',required=True);launch.add_argument('--authorization',required=True)
    launch.add_argument('--bridge-id',required=True);launch.add_argument('--runtime-minutes',type=int,required=True)
    for name in ['next-action','execution-status','recover-execution','stop-execution','record-action','advance-execution','check-action','cleanup-execution','record-cleanup']:
        cmd=commands.add_parser(name)
        cmd.add_argument('--run-id',required=True)
        if name=='stop-execution':cmd.add_argument('--reason',required=True)
        if name in {'record-action','advance-execution','record-cleanup'}:cmd.add_argument('--receipt',type=Path,required=True)
        if name=='check-action':cmd.add_argument('--request-id',required=True)
    report=commands.add_parser('report');report.add_argument('--format',choices=['json','md'],default='json')
    report.add_argument('--output',help='relative output path inside the private workspace')
    tracker=commands.add_parser('tracker',help='fast ledger snapshot; does not validate files, approvals or live vacancies')
    tracker.add_argument('--format',choices=['json','md'],default='json')
    tracker.add_argument('--output',help='relative reports/ output path in the private workspace')
    throughput=commands.add_parser('throughput',help='rolling confirmed-fit KPI; no forecast, browser or artifact validation')
    throughput.add_argument('--target',type=int,required=True)
    throughput.add_argument('--window-minutes',type=int,default=60)
    add=commands.add_parser('add-job',help='legacy local job input; use import-jd for versioned preparation')
    add.add_argument('--job',type=Path,required=True)
    for name in ['check-package','check-approval']:
        cmd=commands.add_parser(name);cmd.add_argument('--package',type=Path,required=True)
        cmd.add_argument('--action',choices=sorted(ACTIONS))
    record=commands.add_parser('record-approval',help='legacy local bookkeeping, no batch execution')
    record.add_argument('--package',type=Path,required=True);record.add_argument('--confirmation',type=Path,required=True)
    record.add_argument('--reviewed',action='store_true',required=True)
    revoke=commands.add_parser('invalidate');revoke.add_argument('--approval-id',type=int,required=True)
    revoke.add_argument('--reason',required=True)
    return root


def load_input(path: Path) -> dict:
    if path.stat().st_size>2_000_000:
        raise ContractError('JSON input exceeds 2 MB; use a relevant structured document')
    value=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value,dict):raise ContractError('JSON input must be an object')
    return value


def execute(args) -> Outcome:
    command=args.command
    if command in {'discover-greenhouse','discover-ashby'}:
        from core.discovery import discover
        data=discover(args.board,workers=args.workers,include_content=args.include_content,
                      provider='ashby' if command=='discover-ashby' else 'greenhouse')
        return Outcome('ok' if not data['failed_boards'] else 'manual_required',data,[])
    if command=='doctor':return diagnose(args.runtime)
    if command=='benchmark-web':
        from scripts.benchmark_web import benchmark
        return Outcome('ok',benchmark(args.samples,args.latency_ms),[])
    if command=='provider-doctor':
        import os
        from dataclasses import asdict
        from adapters.providers.firecrawl import CAPABILITIES
        return Outcome('ok',{'provider':'firecrawl-v2','credentials_configured':bool(os.environ.get('FIRECRAWL_API_KEY')),
            'capabilities':asdict(CAPABILITIES),'network_calls':0,'account_capabilities_verified':False,
            'tinyfish':{'status':'Experimental public Fetch only','credentials_configured':bool(os.environ.get('TINYFISH_API_KEY')),'max_urls':10,'live_verified':False},
            'tinyfish_browser':{'status':'Experimental single-page guest forms','max_sessions':10,'live_verified':False,
                'requires':'Exact cloud scope and optional Playwright client; no entitlement check'},
            'dependencies':'Core uses Python standard library; optional Browser client installed separately'},[])
    if command=='tinyfish-fetch' and not args.live:
        from adapters.providers.tinyfish_research import preview
        return preview(load_input(args.plan))
    if command=='discover' and not args.live:
        from adapters.providers.research import Research
        return Research(None).preview(load_input(args.plan))
    if command=='route-task':
        from core.routing import route_task
        return route_task(load_input(args.packet))
    if command=='source-registry':return Outcome('ok',load_input(ROOT/'connectors/registry.json'),[])
    if args.data_dir is None:
        raise WorkflowError('needs_input','--data-dir is required; choose an explicit external private workspace')
    work=Executor(args.data_dir,actor=args.actor)
    if command=='init':return work.init(args.language)
    if command=='start-campaign':
        from core.starter import start_campaign
        return start_campaign(work,args.cv,target=args.target,language=args.language)
    if not work.db_path.is_file():
        raise WorkflowError('needs_input','Workspace not initialized; run init first with this --data-dir')
    legacy={'status','add-job','check-package','check-approval','record-approval','invalidate'}
    if command not in legacy:
        with work._db() as db:
            schema=db.execute('PRAGMA user_version').fetchone()[0]
            if schema not in {1,2,3,4,5,6}:
                raise WorkflowError('needs_input','Run init to apply the compatible additive preparation schema')
            if command in {'render','review-documents','reject-documents','create-manifest','approve-manifest','check-manifest','revoke-manifest'} and schema<2:
                raise WorkflowError('needs_input','Run init to apply additive document/manifest schema 2; existing data is preserved')
            if command in {'start-execution','next-action','execution-status','recover-execution','stop-execution','record-action','advance-execution','check-action','cleanup-execution','record-cleanup','browser-act-plan'} and schema<3:
                raise WorkflowError('needs_input','Run init to apply additive execution schema 3; existing data is preserved')
            if command in {'create-authorization','approve-authorization','check-authorization','revoke-authorization','authorize-manifest','launch-execution'} and schema<4:
                raise WorkflowError('needs_input','Run init to apply additive standing authorization schema 4; existing data is preserved')
            if command in {'tinyfish-fetch','discover','research-status','cancel-research','research-report','import-research-jd'} and schema<5:
                raise WorkflowError('needs_input','Run init for additive public research schema 5')
            if command=='tinyfish-browser' and schema<6:
                raise WorkflowError('needs_input','Run init for additive parallel execution schema 6')
    if command in {'career-writing-brief','career-check-draft'}:
        from core.career_drafting import writing_brief, check_draft
        from core.contracts import object_fields
        if command=='career-writing-brief':
            return writing_brief(work,args.job_id,kind=args.kind,language=args.language,limit=args.limit)
        packet=work.private_json(args.file)
        object_fields(packet,{'request','draft'},set(),'draft check packet')
        return check_draft(work,packet['request'],packet['draft'])
    if command in {'career-context','career-email-context','career-evaluate'}:
        from core.career_memory import retrieve, email_context, evaluate
        if command=='career-context':return retrieve(work,args.query,limit=args.limit,max_chars=args.max_chars)
        if command=='career-email-context':return email_context(work,args.job_id,language=args.language,limit=args.limit)
        return evaluate(work,work.private_json(args.file))
    if command in {'learning-export','learning-check'}:
        from core.learning import export_reviewed, check_export
        if command=='learning-export':return export_reviewed(work,args.job_id,args.output)
        return check_export(work,args.directory)
    if command in {'growth-context','growth-capture','growth-plan','growth-review','growth-check',
                   'growth-evidence','growth-export','growth-check-export'}:
        from core import career_growth
        if command=='growth-context':return career_growth.gap_context(work,args.job_id)
        if command=='growth-capture':return career_growth.capture(work,args.job_id)
        if command=='growth-plan':return career_growth.import_plan(work,work.private_json(args.file))
        if command=='growth-review':return career_growth.review_plan(work,args.fingerprint,work.private_json(args.file))
        if command=='growth-check':return career_growth.check_plan(work,args.fingerprint)
        if command=='growth-evidence':return career_growth.record_evidence(work,args.fingerprint,args.action_id,args.artifact,args.note)
        if command=='growth-export':return career_growth.export_reviewed(work,args.fingerprint,args.output)
        return career_growth.check_export(work,args.directory)
    if command in {'outcome-record','outcome-report'}:
        from core import cv_outcomes
        if command=='outcome-record':return cv_outcomes.record(work,work.private_json(args.file))
        return cv_outcomes.report(work,min_age_days=args.min_age_days,as_of=args.as_of,job_ids=args.job_id)
    if command in {'performance-record','performance-report'}:
        from core.performance import record, report, export
        if command=='performance-record':return record(work,work.private_json(args.file))
        filters={key:getattr(args,key) for key in ('model_id','phase','workload_id')}
        if args.output:return export(work,args.output,args.format,**filters)
        if args.format!='json':raise ContractError('Choose a new --output under reports/performance/ for Markdown/CSV')
        return report(work,**filters)
    if command in {'discover','research-status','cancel-research','research-report','import-research-jd'}:
        from adapters.providers.research import Research
        from adapters.providers.contracts import ProviderError
        research=Research(work)
        try:
            if command=='discover':return research.discover(load_input(args.plan),args.approve_plan,individual=args.individual)
            if command=='research-report':return research.summary(args.fingerprint)
            if command=='import-research-jd':return research.import_jd(args.evidence_id,load_input(args.file))
            return research.status(args.fingerprint,cancel=command=='cancel-research')
        except ProviderError as error:
            return Outcome('manual_required',{'provider_error':error.code,'possibly_accepted':error.possibly_accepted},
                           ['Inspect persisted tasks; do not relaunch an uncertain request.'])
    if command=='browser-act-plan':
        from adapters.browser_act import plan_session
        from core.parallel_execution import ParallelExecutor
        return plan_session(ParallelExecutor(args.data_dir,actor=args.actor),args.run_id,args.request_id,args.browser_id)
    if command in {'parallel-cleanup','record-parallel-cleanup','start-parallel-execution','parallel-status','next-parallel-action','record-parallel-action','check-parallel-action','recover-parallel-execution','stop-parallel-execution'}:
        from core.parallel_execution import ParallelExecutor
        parallel=ParallelExecutor(args.data_dir,actor=args.actor)
        if command=='start-parallel-execution':return parallel.start_parallel_execution(args.fingerprint,args.bridge_id,args.runtime_minutes,workers=args.workers)
        if command=='parallel-cleanup':return parallel.parallel_cleanup(args.run_id)
        if command=='record-parallel-cleanup':return parallel.record_parallel_cleanup(args.run_id,work.private_json(args.receipt))
        if command=='parallel-status':return parallel.parallel_status(args.run_id)
        if command=='next-parallel-action':return parallel.next_parallel_action(args.run_id,args.job_id)
        if command=='record-parallel-action':return parallel.record_parallel_action(args.run_id,work.private_json(args.receipt))
        if command=='check-parallel-action':return parallel.check_parallel_action(args.run_id,args.request_id)
        if command=='recover-parallel-execution':return parallel.recover_parallel_execution(args.run_id,args.job_id)
        return parallel.stop_parallel_execution(args.run_id,args.reason)
    if command=='tinyfish-browser':
        from core.parallel_execution import ParallelExecutor, run_parallel_with_bridge
        from adapters.tinyfish_browser import preview, TinyFishBrowserBridge
        parallel=ParallelExecutor(args.data_dir,actor=args.actor)
        forms=work.private_json(args.forms);scope=work.private_json(args.cloud_scope)
        if not args.live:return preview(parallel,args.run_id,forms,scope)
        bridge=TinyFishBrowserBridge(parallel,args.run_id,forms,scope,args.approve_cloud_scope,
                                    action_timeout_seconds=args.action_timeout_seconds)
        return run_parallel_with_bridge(parallel,args.run_id,bridge,action_timeout_seconds=args.action_timeout_seconds)
    if command=='tinyfish-fetch':
        from adapters.providers.tinyfish_research import fetch
        from adapters.providers.contracts import ProviderError
        try:return fetch(work,load_input(args.plan),args.approve_plan)
        except ProviderError as error:
            return Outcome('manual_required',{'provider_error':error.code,'possibly_accepted':error.possibly_accepted},['Inspect persisted task state before any retry.'])
    if command=='import-cv':return work.import_cv(args.file,args.source_id)
    if command=='import-profile':return work.import_profile(load_input(args.file))
    if command=='profile':return work.inspect_profile()
    if command=='confirm-profile':return work.confirm_profile(args.fingerprint,args.confirmation)
    if command=='import-jd':return work.import_job(load_input(args.file))
    if command=='duplicate-candidates':return work.duplicate_candidates(args.job_id)
    if command=='assess':
        result=work.assess(args.job_id,load_input(args.matrix))
        if not args.capture_growth or result.outcome!='ok':return result
        try:
            from core.career_growth import capture
            captured=capture(work,[args.job_id])
        except WorkflowError as error:
            captured=Outcome(error.outcome,{},[str(error)])
        except (ContractError,ValueError,TypeError,KeyError,OSError) as error:
            captured=Outcome('needs_input',{},[str(error)])
        except sqlite3.Error as error:
            captured=Outcome('failed',{},['Growth capture SQLite operation failed: '+str(error)])
        issues=list(result.issues)
        if captured.outcome!='ok':
            issues.append('Assessment was saved; growth capture did not complete. Inspect growth_capture and retry growth-capture explicitly.')
        return Outcome(result.outcome,{**result.data,'growth_capture':captured.json()},issues,
                       result.message,result.schema_version)
    if command=='prepare':return work.prepare(args.job_id,load_input(args.plan))
    if command=='import-wording':
        result=work.import_wording(args.job_id,work.private_json(args.file))
        if args.include_review_packet:result.data['review_packet']=work.wording_packet(args.job_id).data
        return result
    if command=='wording-packet':return work.wording_packet(args.job_id)
    if command=='review-wording':return work.review_wording(args.job_id,work.private_json(args.file))
    if command=='reject-wording':return work.reject_wording(args.job_id,args.reason)
    if command=='render':return work.render(args.job_id,args.soffice)
    if command=='review-documents':return work.review_documents(args.render_id,args.review)
    if command=='reject-documents':return work.reject_documents(args.render_id,args.reason)
    if command=='create-manifest':return work.create_manifest(work.private_json(args.plan))
    if command=='approve-manifest':return work.approve_manifest(args.fingerprint,args.confirmation)
    if command=='check-manifest':return work.check_manifest(args.fingerprint,work.private_json(args.intent) if args.intent else None)
    if command=='revoke-manifest':return work.revoke_manifest(args.fingerprint,args.reason)
    if command=='create-authorization':return work.create_authorization(work.private_json(args.plan))
    if command=='approve-authorization':return work.approve_authorization(args.fingerprint,args.confirmation)
    if command=='check-authorization':return work.check_authorization(args.fingerprint)
    if command=='revoke-authorization':return work.revoke_authorization(args.fingerprint,args.reason)
    if command=='authorize-manifest':return work.authorize_manifest(args.fingerprint,args.authorization)
    if command=='start-execution':return work.start_execution(args.fingerprint,args.bridge_id,args.runtime_minutes)
    if command=='launch-execution':return work.launch_execution(args.fingerprint,args.authorization,args.bridge_id,args.runtime_minutes)
    if command=='next-action':return work.next_action(args.run_id)
    if command=='execution-status':return work.execution_status(args.run_id)
    if command=='check-action':return work.check_action(args.run_id,args.request_id)
    if command=='recover-execution':return work.recover_execution(args.run_id)
    if command=='stop-execution':return work.stop_execution(args.run_id,args.reason)
    if command=='record-action':return work.record_action(args.run_id,work.private_json(args.receipt))
    if command=='advance-execution':return work.advance_execution(args.run_id,work.private_json(args.receipt))
    if command=='cleanup-execution':return work.cleanup_execution(args.run_id)
    if command=='record-cleanup':return work.record_cleanup(args.run_id,work.private_json(args.receipt))
    if command=='resume':return work.resume()
    if command=='throughput':return work.throughput(args.target,args.window_minutes)
    if command=='handoff':return work.handoff(args.job_id)
    if command in {'report','tracker'}:
        if args.output:
            target=work.inside(args.output)
            expected_suffix='.'+args.format
            if (Path(args.output).is_absolute() or not target.is_relative_to(work.data_dir/'reports') or
                    target.suffix!=expected_suffix):
                raise WorkflowError('blocked','Report output must be a relative reports/ path with the selected .json or .md extension; tracker/evidence/drafts are protected')
        result=work.tracker() if command=='tracker' else work.resume()
        if not args.output:return result
        if args.format=='json':content=json.dumps(result.json(),ensure_ascii=False,indent=2)
        elif command=='tracker':
            from core.tracking import markdown
            content=markdown(result.data)
        else:
            vi=work.language()=='vi'
            lines=['# '+('Báo cáo tìm việc' if vi else 'Job search checkpoint'),'',
                result.data['mode']+' — '+('Số hồ sơ có xác nhận từ trình duyệt: ' if vi else 'Host-observed confirmed applications: ')+str(result.data.get('observed_submissions',0)),'',
                '| Job | State | Draft stale |','|---|---|---|']
            for job in result.data['jobs']:
                lines.append(f"| {work.literal(job['employer']+' — '+job['title'])} | {job['state']} | {job['draft_stale']} |")
            if result.data.get('document_sets'):
                lines += ['','## '+('Tài liệu' if vi else 'Documents'),'',
                    '| Render | Reviewed | Stale |','|---|---|---|']
                for item in result.data['document_sets']:
                    lines.append(f"| {item['render_id']} | {item.get('reviewed',False)} | {item['stale']} |")
            if result.data.get('manifests'):
                lines += ['','## '+('Phê duyệt cục bộ' if vi else 'Local approvals'),'',
                    '| Manifest | Approved | Execution enabled |','|---|---|---|']
                for item in result.data['manifests']:
                    lines.append(f"| {item['fingerprint']} | {item['approved']} | {item.get('execution_enabled',False)} |")
            content='\n'.join(lines)+'\n'
        target=work.atomic_text(args.output,content)
        return Outcome(result.outcome,{'path':str(target.relative_to(work.data_dir)),
            'sha256':work.hash_file(target),'format':args.format},result.issues)
    if command=='status':return Outcome('ok',work.status(),[])
    if command=='add-job':return Outcome('ok',work.add_job(**work.load_private_json(args.job)),[])
    if command=='check-package':return Outcome('ok',work.check_package(work.load_private_json(args.package),args.action),[])
    if command=='check-approval':
        approved=work.check_approval(work.load_private_json(args.package),args.action)
        return Outcome('ok' if approved else 'blocked',{'approved':approved},[] if approved else ['No current matching approval.'])
    if command=='record-approval':
        return Outcome('ok',work.record_approval(work.load_private_json(args.package),args.confirmation,reviewed=args.reviewed),[])
    return Outcome('ok',{'invalidated':work.invalidate(args.approval_id,args.reason)},[])


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8')
    try:
        result=execute(parser().parse_args(argv))
    except WorkflowError as error:
        result=Outcome(error.outcome,{},[str(error)])
    except (ContractError,PackageError,ValueError,TypeError,KeyError,OSError) as error:
        result=Outcome('needs_input',{},[str(error)])
    except sqlite3.Error as error:
        result=Outcome('failed',{},['SQLite operation failed; retain the workspace and inspect migration/lock state: '+str(error)])
    print(json.dumps(result.json(),ensure_ascii=False,sort_keys=True))
    return 0 if result.outcome=='ok' else 2


if __name__=='__main__':raise SystemExit(main())
