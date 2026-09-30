"""Fresh no-tool GLM inference through installed ZCode's workspace/generateText RPC."""
from pathlib import Path
import os, subprocess, json, time, selectors, argparse, uuid, hashlib
BUNDLE=Path('/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs')
NODE='/opt/homebrew/bin/node'


def generate(system_prompt: str, user_prompt: str, output_dir: Path) -> dict:
    output_dir=Path(output_dir).resolve();output_dir.mkdir(parents=True,exist_ok=True)
    isolated_root=output_dir/'isolated-user';isolated_root.mkdir(exist_ok=True)
    cwd=output_dir/'workspace';(cwd/'.zcode').mkdir(parents=True,exist_ok=True)
    config={'features':{'compact':False,'rewind':False,'subagent':False,'memory':False,'skill':False,'mcp':False},'memory':{'use':False},'plugins':{'enabled':False},'skills':{'enabled':False,'includeInstructions':False},'hooks':{'enabled':False},'mcp':{'servers':{}},'logging':{'level':'info'}}
    (cwd/'.zcode/config.json').write_text(json.dumps(config,indent=2)+'\n')
    preload=output_dir/'isolate-user.cjs'
    preload.write_text('const os = require("node:os");\nconst root = process.env.JJ_SKILL_EVAL_USER_ROOT;\nif (!root) throw new Error("Missing evaluation user root");\nos.homedir = () => root;\n')
    env=dict(os.environ)
    auth_base=env.get('ZCODE_DATA_BASE_DIR') or str(Path.home())
    env.pop('HOME',None);env.pop('USERPROFILE',None)
    env['JJ_SKILL_EVAL_USER_ROOT']=str(isolated_root)
    env['ZCODE_DATA_BASE_DIR']=auth_base
    env['ZCODE_STORAGE_DIR']=str(isolated_root/'.zcode')
    env['ZCODE_SESSION_DB_PATH']=str(isolated_root/'.zcode/cli/db/db.sqlite')
    env['ZCODE_BUILTIN_PROVIDER_CONFIG_FILE']='/Applications/ZCode.app/Contents/Resources/config/provider/zcode-builtin.json'
    env['ZCODE_PERSONAL_PROVIDER_CONFIG_FILE']=str(Path(auth_base)/'.zcode/v2/provider_config.json')
    env['ZCODE_MODEL_TELEMETRY_ENABLED']='0'
    request={'id':'jj-skill-eval','method':'workspace/generateText','params':{'workspace':{'workspacePath':str(cwd),'workspaceKey':'jj-skill-eval:'+str(uuid.uuid4())},'selection':{'providerId':'account:zai-individual-coding-plan','modelId':'GLM-5.3','options':{'reasoningLevel':'max'}},'messages':[{'role':'system','content':system_prompt},{'role':'user','content':user_prompt}],'tools':[],'querySource':'jj_skill_first_try_eval','maxOutputTokens':64000,'operationId':'jj-skill-eval-operation:'+str(uuid.uuid4())}}
    (output_dir/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    args=[NODE,'--require',str(preload),str(BUNDLE),'app-server','--stdio','--cwd',str(cwd),'--no-color']
    t=time.monotonic();messages=[];response=None;stderr_file=(output_dir/'stderr.txt').open('wb')
    process=subprocess.Popen(args,env=env,cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr_file,bufsize=0)
    def send(value):
        process.stdin.write((json.dumps(value)+'\n').encode());process.stdin.flush()
    builtin=json.loads(Path(env['ZCODE_BUILTIN_PROVIDER_CONFIG_FILE']).read_text())
    model_ids=next(r['config']['builtinModelIds'] for r in builtin['config']['providerConfigRules']['providerRules'] if r['providerId']=='account:zai-individual-coding-plan')
    account_setup={'id':'account-config','method':'provider/updateAccountConfig','params':{'revision':'jj-skill-eval-existing-account','basedOnZCodeBuiltinRevision':'zcode-builtin:'+str(builtin['revision'])+':'+hashlib.sha256(json.dumps(builtin['config'],separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'providers':{'account:zai-individual-coding-plan':{'builtinModelIds':model_ids,'access':{'type':'zhipu-account','entitled':True}}},'states':{'account:zai-individual-coding-plan':{'availability':'available','entitled':True,'current':True}}}}
    # Reuse the same auth material the GUI writes into its provider config.
    # It stays in process memory and is never printed or written to eval artifacts.
    legacy_config=json.loads((Path(auth_base)/'.zcode/v2/config.json').read_text())
    existing_auth=legacy_config['provider']['builtin:zai-coding-plan']['options']['apiKey']
    # Provider config revisions are based on ZCode's normalized schema, not raw JSON.
    # Read only the non-secret revision from this fresh process's startup log.
    builtin_revision=None
    for _ in range(100):
        for log in (isolated_root/'.zcode/cli/log').glob('*.jsonl'):
            for line in log.read_text().splitlines():
                try:entry=json.loads(line)
                except ValueError:continue
                if entry.get('event')=='zcode_protocol.provider_registry.ready':
                    builtin_revision=json.loads(entry['context']['configRevision'])[0]
        if builtin_revision:break
        time.sleep(.05)
    if builtin_revision:account_setup['params']['basedOnZCodeBuiltinRevision']=builtin_revision
    send(account_setup)
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ);buf=b''
    try:
        deadline=t+300
        while time.monotonic()<deadline and response is None:
            ready=selector.select(timeout=min(1,max(0,deadline-time.monotonic())))
            if not ready:
                if process.poll() is not None:break
                continue
            chunk=os.read(process.stdout.fileno(),65536)
            if not chunk:break
            buf+=chunk
            while b'\n' in buf:
                line,buf=buf.split(b'\n',1)
                if not line.strip():continue
                try:msg=json.loads(line)
                except ValueError:messages.append({'non_json_stdout':line.decode(errors='replace')});continue
                messages.append(msg)
                if msg.get('id')=='account-config':
                    if 'error' in msg:response=msg;break
                    send(request);continue
                if msg.get('id')==request['id'] and ('result' in msg or 'error' in msg):response=msg;break
                if 'id' in msg and 'method' in msg:
                    # Runtime authentication handshake is transport configuration,
                    # not model feedback. Existing local auth is left in place.
                    if msg['method']=='interaction/requestProviderRuntimeHeaders':
                        send({'id':msg['id'],'result':{'headersApplied':True,'requestAuth':{'apiKey':existing_auth}}})
                    else:
                        send({'id':msg['id'],'error':{'code':-32000,'message':'Evaluation client does not expose interactive capabilities'}})
    finally:
        selector.close()
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        stderr_file.close()
    (output_dir/'protocol-messages.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in messages))
    common={'transport_timeout_policy':'RPC operationId supplies a cancellable server AbortController instead of the default 60000-ms fallback. Client watchdog is 300 seconds; exactly one transport attempt per condition. Both arms use64000 outputtokens to accommodate maxreasoning; messages, selection, and tools are unchanged.','engine':'ZCode CLI 0.16.9 workspace/generateText','elapsed_seconds':time.monotonic()-t,'context_isolation':'One explicit system message, one explicit user message, empty tools list. Installed ZCode workspace/generateTextImpl forwards exactly these messages; no session history, AGENTS, skill auto-load, memory, or core agent system prompt is appended. Scratch storage; existing auth remains in supported ZCODE_DATA_BASE_DIR.','system_delivery':'separate system/user messages through ZCode protocol','request_file':str(output_dir/'request.json'),'protocol_file':str(output_dir/'protocol-messages.jsonl')}
    if response is None:
        result={**common,'raw_text':'','model':'unknown','engine_error':'No inference result before process exit or 300-second timeout','stderr':(output_dir/'stderr.txt').read_text()[-2000:]}
    elif 'error' in response:
        result={**common,'raw_text':'','model':'unknown','engine_error':response['error']}
    else:
        r=response['result'];result={**common,'raw_text':r.get('text',''),'model':r.get('selection',{}).get('modelId','unknown'),'model_selection':r.get('selection'),'usage':r.get('usage'),'tool_calls':r.get('toolCalls',[]),'finish_reason':r.get('finishReason')}
        if result['tool_calls']:result['engine_error']='Model emitted tools despite empty tool list; no tool executed'
    (output_dir/'adapter-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--system-file',required=True,type=Path);p.add_argument('--prompt-file',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    result=generate(a.system_file.read_text(),a.prompt_file.read_text(),a.output.parent)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='raw_text'},indent=2))
