import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import {normalize,css,DEFAULTS} from './theme.mjs';
import {bootstrap} from './renderer.mjs';
import {discover,Session,listTargets} from './cdp.mjs';
import {uploadMedia,clientExpression} from './media-transfer.mjs';
import {upgradeRegions,fixLeftSurfaces} from './regions.mjs';
import {acquireWorker} from './worker-lock.mjs';
const startup=process.argv.includes('--startup'),exitWithClient=process.argv.includes('--exit-with-client');
const portIndex=process.argv.indexOf('--port');
const preferredPort=portIndex>=0?Number(process.argv[portIndex+1]):null;
let connectedOnce=false,startupComplete=false;const birth=Date.now();
const root=fileURLToPath(new URL('../',import.meta.url));
const dataIndex=process.argv.indexOf('--data-root');
const data=dataIndex>=0?path.resolve(process.argv[dataIndex+1]):path.join(root,'data');
const configPath=path.join(data,'settings.json'),statusPath=path.join(data,'status.json'),stopPath=path.join(data,'stop.request');
await fs.mkdir(data,{recursive:true});
async function atomic(file,value){const tmp=file+'.'+crypto.randomUUID()+'.tmp';await fs.writeFile(tmp,JSON.stringify(value,null,2),'utf8');await fs.rename(tmp,file);}
async function report(value){await atomic(statusPath,{...value,updatedAt:new Date().toISOString()});}
async function config(){try{return normalize(JSON.parse((await fs.readFile(configPath,'utf8')).replace(/^\uFEFF/,'')));}catch(e){if(e.code==='ENOENT')return {...DEFAULTS};throw new Error('本机设置文件无法解析，未覆盖：'+e.message);}}
async function payload(){const c=await config();return {...c,css:css(c),mediaKey:c.media,revision:crypto.createHash('sha256').update(JSON.stringify(c)).digest('hex')};}
const mode=process.argv[2]||'inspect';
let workerLock=null;
if(mode==='watch'){workerLock=await acquireWorker(data);if(!workerLock.owned){console.log(JSON.stringify({reused:true,reason:workerLock.reason}));process.exit(0);}}
const sessions=new Map();let busy=false,stopped=false,lastFailureRevision='',failures=0,lastTargetsAt=0;
const shouldStop=()=>fs.stat(stopPath).then(()=>true,()=>false);
async function close(){stopped=true;for(const s of sessions.values())s.close();sessions.clear();await workerLock?.release();}
async function tick(){if(busy||stopped)return;busy=true;
 try{
  if(await shouldStop()){await fs.unlink(stopPath);await close();return;}
  const connected=[...sessions.values()].find(s=>!s.closed);
  const found=connected?{port:connected.port}:preferredPort?{port:preferredPort}:await discover();
  if(exitWithClient&&!connected&&(connectedOnce||Date.now()-birth>120000)){
   const info=await discover();if(!info.running){await close();return;}
  }
  if(!found.port){await report({phase:'needs-client-restart',message:'主窗口接口未开启；请从桌面或开始菜单的豆包工作入口启动。'});return;}
  const p=await payload();
  if(lastFailureRevision===p.revision&&failures>=2){await report({phase:'not-applied',message:'应用失败后已停止自动重试，防止重复传输影响客户端。请查看 transfer-error.json，或调整设置后重试。',port:found.port});return;}
  if(lastFailureRevision!==p.revision){lastFailureRevision=p.revision;failures=0;}
  const targets=connected&&Date.now()-lastTargetsAt<30000?[...sessions.values()].map(s=>s.target):await listTargets(found.port);if(!connected||Date.now()-lastTargetsAt>=30000)lastTargetsAt=Date.now();const live=new Set(targets.map(t=>t.id));for(const [id,s]of sessions)if(!live.has(id)||s.closed){s.close();sessions.delete(id);}
  let count=0,last=null;
  for(const target of targets){let s=sessions.get(target.id);try{
   if(!s){s=await new Session(target,found.port).open();s.onBinding=params=>{if(params.name==='__DCS_OPEN__'&&params.payload==='settings'){fs.writeFile(path.join(data,'open-settings.request'),'open','utf8').catch(()=>{});const panel=path.join(root,'豆包客户端皮肤-自动启动版.exe');fs.stat(panel).then(()=>{const child=spawn(panel,[],{cwd:root,detached:true,stdio:'ignore'});child.on('error',()=>{});child.unref();},()=>{});}};await s.send('Runtime.enable');await s.send('Runtime.addBinding',{name:'__DCS_OPEN__'});sessions.set(target.id,s);}
   const init=await s.evaluate(`(()=>{if(!['doubaowork:','chrome:'].includes(location.protocol)||!['doubaowork-chat','doubaowork-launcher'].includes(location.hostname))return {ok:false};return (${bootstrap.toString()})();})()`);
   if(!init?.ok){last={ok:false,reason:'客户端主布局正在准备'};continue;}
   await s.evaluate(`(${upgradeRegions.toString()})()`);
   await s.evaluate(`(${fixLeftSurfaces.toString()})()`);
   // Remove a prior reveal without destroying the decoded video or current skin.
   await s.evaluate(clientExpression('(()=>{window.__DCS__?.reveal?.cancel();if(window.__DCS__){delete window.__DCS__.reveal;delete window.__DCS__.revealVersion;}return true;})()'));
   const current=await s.evaluate(clientExpression('window.__DCS__.status()'));
   if(current?.ok&&current.regionVersion===4&&current.revision===p.revision){last=current;connectedOnce=true;count++;continue;}
   if(p.enabled&&p.mediaKey&&(!current?.hasMedia||current.mediaKey!==p.mediaKey)){
    const base=await s.evaluate(clientExpression(`window.__DCS__.apply(${JSON.stringify({...p,mediaKey:''})})`));
    if(!base?.surfaceVerified)throw new Error(base?.reason||'主布局表面尚未匹配');
    await report({phase:'transferring',message:'正在分块传输本地背景；不上传服务器。',port:found.port,progress:0});
    let lastPercent=-1;
    await uploadMedia(s,path.join(data,'media',p.mediaKey),{key:p.mediaKey,type:p.mediaType,shouldStop,onProgress:async(done,total)=>{const percent=Math.floor(done/total*100);if(percent!==lastPercent){lastPercent=percent;await report({phase:'transferring',message:`本地背景传输 ${percent}%`,progress:percent,port:found.port});}}});
   }
   last=await s.evaluate(clientExpression(`window.__DCS__.apply(${JSON.stringify(p)})`));
   if(!last?.ok)throw new Error(last?.reason||'客户端应用验证失败');
   connectedOnce=true;startupComplete=true;count++;
  }catch(e){try{await s?.evaluate(clientExpression('window.__DCS__?.reveal?.cancel()'));}catch{}last={ok:false,reason:e.message};failures++;await atomic(path.join(data,'transfer-error.json'),{message:e.message,revision:p.revision,port:found.port,time:new Date().toISOString()});s?.close();sessions.delete(target.id);}}
  if(count>0)failures=0;
  await report({phase:count>0?(p.enabled?'applied':'disabled'):'not-applied',message:count>0?(p.enabled?'已在豆包客户端主窗口应用皮肤':'已关闭皮肤，保留设置入口'):last?.reason||'未找到工作主窗口',port:found.port,verified:last,revision:p.revision});
 }catch(e){await report({phase:'error',message:e.message});}
 finally{busy=false;}
}
if(mode==='inspect'){const found=await discover();console.log(JSON.stringify({running:found.running,ready:!!found.port,client:found.executable,port:found.port}));await report({phase:found.port?'ready':'needs-client-restart',message:found.port?'主窗口接口可用':'主窗口接口未开启，请使用“启用客户端换肤”。',port:found.port});}
else if(mode==='restore'){const found=await discover();if(!found.port)throw new Error('主窗口接口不可用，无法验证恢复');for(const target of found.pages){const s=await new Session(target,found.port).open();try{await s.evaluate(`(()=>{if(window.__DCS__)window.__DCS__.destroy();return true;})()`);}finally{s.close();}}await report({phase:'restored',message:'已移除本插件临时皮肤和入口'});}
else if(mode==='once'){await tick();await close();console.log(await fs.readFile(statusPath,'utf8'));}
else if(mode==='watch'){
 await atomic(path.join(data,'worker.json'),{pid:process.pid,script:fileURLToPath(import.meta.url)});
 const quit=async()=>{await close();await fs.unlink(path.join(data,'worker.json')).catch(()=>{});};
 process.on('SIGTERM',quit);process.on('SIGINT',quit);
 await tick();
 const loop=async()=>{await tick();if(stopped){await fs.unlink(path.join(data,'worker.json')).catch(()=>{});return;}setTimeout(loop,startup&&!startupComplete&&Date.now()-birth<90000?1000:10000);};
 if(!stopped)setTimeout(loop,startup&&!startupComplete?1000:10000);
}else throw new Error('未知模式');
