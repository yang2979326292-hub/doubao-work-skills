import fs from 'node:fs/promises';
export const CHUNK_BYTES=384*1024;
export function clientExpression(code){return `(()=>{if(!['doubaowork:','chrome:'].includes(location.protocol)||!['doubaowork-chat','doubaowork-launcher'].includes(location.hostname)||!document.querySelector('[data-testid="chat-route-layout"]')||!document.getElementById('chat-route-main')||!window.__DCS__)throw new Error('主窗口已导航，停止媒体传输');return ${code};})()`;}
export async function uploadMedia(session,file,{key,type,onProgress=()=>{},shouldStop=()=>false}){
 const handle=await fs.open(file,'r');let started=false;
 try{
  const {size}=await handle.stat();if(size<1||size>150*1024*1024)throw new Error('媒体为空或超过150MB');
  const begin=await session.evaluate(clientExpression(`window.__DCS__.beginMedia(${JSON.stringify({key,type,size})})`));if(!begin?.ok)throw new Error(begin?.reason||'媒体暂存失败');started=true;
  const buffer=Buffer.alloc(CHUNK_BYTES);let position=0,index=0;
  while(position<size){if(await shouldStop())throw new Error('用户已停止传输');const {bytesRead}=await handle.read(buffer,0,Math.min(CHUNK_BYTES,size-position),position);if(bytesRead===0)throw new Error('媒体读取提前结束');
   const response=await session.evaluate(clientExpression(`window.__DCS__.appendMedia(${index},${JSON.stringify(buffer.subarray(0,bytesRead).toString('base64'))})`));
   position+=bytesRead;index++;if(!response?.ok||response.received!==position)throw new Error('媒体分块累计校验失败');await onProgress(position,size);
  }
  const response=await session.evaluate(clientExpression('window.__DCS__.finishMedia()'));if(!response?.ok||response.bytes!==size)throw new Error('媒体完整长度校验失败');return response;
 }catch(e){if(started&&!session.closed)await session.evaluate(clientExpression('window.__DCS__.cancelMedia()')).catch(()=>{});throw e;}
 finally{await handle.close();}
}
