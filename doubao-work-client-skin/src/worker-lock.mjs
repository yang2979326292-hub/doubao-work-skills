import fs from 'node:fs/promises';
import path from 'node:path';
// One worker owns a data folder. Stale locks are removed only when their PID no longer exists.
export async function acquireWorker(data){
 const file=path.join(data,'worker.lock');
 for(let attempt=0;attempt<2;attempt++){
  try{const handle=await fs.open(file,'wx');await handle.writeFile(JSON.stringify({pid:process.pid,startedAt:new Date().toISOString()}));await handle.close();
   return {owned:true,async release(){try{const value=JSON.parse(await fs.readFile(file,'utf8'));if(value.pid===process.pid)await fs.unlink(file);}catch(e){if(e.code!=='ENOENT')throw e;}}};
  }catch(e){if(e.code!=='EEXIST')throw e;}
  let value;try{value=JSON.parse(await fs.readFile(file,'utf8'));}catch{return {owned:false,reason:'锁文件尚未完整或无法解析，未启动重复宿主'};}
  if(!Number.isInteger(value.pid)||value.pid<1)return {owned:false,reason:'锁文件无效，未覆盖'};
  try{process.kill(value.pid,0);return {owned:false,reason:'已有宿主'};}catch(e){if(e.code!=='ESRCH')return {owned:false,reason:'不能确定旧宿主已退出'};}
  await fs.unlink(file).catch(e=>{if(e.code!=='ENOENT')throw e;});
 }
 return {owned:false,reason:'锁竞争，未启动重复宿主'};
}
