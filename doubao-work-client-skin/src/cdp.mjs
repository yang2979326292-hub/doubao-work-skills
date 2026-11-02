import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {supportedTarget} from './theme.mjs';
const exec=promisify(execFile),infoScript=fileURLToPath(new URL('./client-info.ps1',import.meta.url));
export async function clientInfo(action='Inspect',port=9342){
 const {stdout}=await exec('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',infoScript,'-Action',action,'-Port',String(port)],{encoding:'utf8',windowsHide:true,timeout:60000});
 return JSON.parse(stdout.trim().replace(/^\uFEFF/,''));
}
export async function listTargets(port){
 await clientInfo('PortOwner',port);
 const response=await fetch(`http://127.0.0.1:${port}/json/list`,{signal:AbortSignal.timeout(15000),redirect:'error'});
 if(!response.ok)throw new Error('客户端调试接口返回错误');
 const targets=await response.json();return Array.isArray(targets)?targets.filter(supportedTarget):[];
}
export async function discover(){const info=await clientInfo();for(const port of info.ports){try{const pages=await listTargets(port);if(pages.length)return {...info,port,pages};}catch{}}
 return {...info,port:null,pages:[]};
}
export class Session{
 constructor(target,port){
  const u=new URL(target.webSocketDebuggerUrl);
  if(u.protocol!=='ws:'||!['127.0.0.1','localhost','[::1]'].includes(u.hostname)||Number(u.port)!==port||u.username||u.password)throw new Error('拒绝非本机客户端调试地址');
  this.target=target;this.port=port;this.pending=new Map();this.seq=0;this.closed=false;
 }
 async open(){await clientInfo('PortOwner',this.port);this.ws=new WebSocket(this.target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.ws.close();reject(new Error('客户端连接超时'));},5000);this.ws.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});this.ws.addEventListener('error',()=>{clearTimeout(timer);reject(new Error('客户端连接失败'));},{once:true});});
  this.ws.addEventListener('message',e=>{let m;try{m=JSON.parse(String(e.data));}catch{return;}if(m.method==='Runtime.bindingCalled')this.onBinding?.(m.params);const p=this.pending.get(m.id);if(!p)return;clearTimeout(p.timer);this.pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);});
  this.ws.addEventListener('close',e=>{this.closeReason=`调试连接关闭（${e.code}${e.reason?'：'+e.reason:''}）`;this.close();});return this;
 }
 send(method,params={}){const encoded=JSON.stringify({id:this.seq+1,method,params});if(Buffer.byteLength(encoded)>1024*1024)return Promise.reject(new Error('单次调试消息超过1MB，请分块传输'));if(this.closed)return Promise.reject(new Error('客户端连接已关闭'));return new Promise((resolve,reject)=>{const id=++this.seq,timer=setTimeout(()=>{this.pending.delete(id);reject(new Error('客户端命令超时'));},25000);this.pending.set(id,{resolve,reject,timer});try{this.ws.send(JSON.stringify({id,method,params}));}catch(e){clearTimeout(timer);this.pending.delete(id);reject(e);}});}
 async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:false});if(r.exceptionDetails)throw new Error('客户端页面执行失败：'+(r.exceptionDetails.text||'未知错误'));return r.result?.value;}
 close(){if(this.closed)return;this.closed=true;for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(new Error(this.closeReason||'客户端连接结束'));}this.pending.clear();try{this.ws.close();}catch{}}
}
