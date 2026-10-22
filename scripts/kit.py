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
    discover=commands.add_parser('discover-greenhouse',help='bounded public board GETs; leads only, no candidate data or submission')
    discover.add_argument('--board',action='append',required=True)
    discover.add_argument('--workers',type=int,default=3)
    discover.add_argument('--include-content',action='store_true',help='include full untrusted descriptions; default returns compact leads')
    doctor=commands.add_parser('doctor',help='read-only runtime diagnosis; no account/browser connection')
    doctor.add_argument('--runtime',choices=['generic','codex','claude','grok'],default='generic')
    route=commands.add_parser('route-task',help='deterministic model/tool plan; no model call or workspace access')
    route.add_argument('--packet',type=Path,required=True)
    init=commands.add_parser('init',help='additive local workspace initialization')
    init.add_argument('--language',choices=['en','vi'],default='en')
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
    handoff=commands.add_parser('handoff');handoff.add_argument('--job-id',type=int,required=True)
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
    if command=='discover-greenhouse':
        from core.discovery import discover
        data=discover(args.board,workers=args.workers,include_content=args.include_content)
        return Outcome('ok' if not data['failed_boards'] else 'manual_required',data,[])
    if command=='doctor':return diagnose(args.runtime)
    if command=='route-task':
        from core.routing import route_task
        return route_task(load_input(args.packet))
    if command=='source-registry':return Outcome('ok',load_input(ROOT/'connectors/registry.json'),[])
    if args.data_dir is None:
        raise WorkflowError('needs_input','--data-dir is required; choose an explicit external private workspace')
    work=Executor(args.data_dir,actor=args.actor)
    if command=='init':return work.init(args.language)
    if not work.db_path.is_file():
        raise WorkflowError('needs_input','Workspace not initialized; run init first with this --data-dir')
    legacy={'status','add-job','check-package','check-approval','record-approval','invalidate'}
    if command not in legacy:
        with work._db() as db:
            schema=db.execute('PRAGMA user_version').fetchone()[0]
            if schema not in {1,2,3,4}:
                raise WorkflowError('needs_input','Run init to apply the compatible additive preparation schema')
            if command in {'render','review-documents','reject-documents','create-manifest','approve-manifest','check-manifest','revoke-manifest'} and schema<2:
                raise WorkflowError('needs_input','Run init to apply additive document/manifest schema 2; existing data is preserved')
            if command in {'start-execution','next-action','execution-status','recover-execution','stop-execution','record-action','advance-execution','check-action','cleanup-execution','record-cleanup'} and schema<3:
                raise WorkflowError('needs_input','Run init to apply additive execution schema 3; existing data is preserved')
            if command in {'create-authorization','approve-authorization','check-authorization','revoke-authorization','authorize-manifest','launch-execution'} and schema<4:
                raise WorkflowError('needs_input','Run init to apply additive standing authorization schema 4; existing data is preserved')
    if command=='import-cv':return work.import_cv(args.file,args.source_id)
    if command=='import-profile':return work.import_profile(load_input(args.file))
    if command=='profile':return work.inspect_profile()
    if command=='confirm-profile':return work.confirm_profile(args.fingerprint,args.confirmation)
    if command=='import-jd':return work.import_job(load_input(args.file))
    if command=='assess':return work.assess(args.job_id,load_input(args.matrix))
    if command=='prepare':return work.prepare(args.job_id,load_input(args.plan))
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
