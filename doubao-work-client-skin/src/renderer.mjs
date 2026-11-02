/* Executed only inside verified Doubao Work internal chat renderer. */
export function bootstrap(){
 const isClient=()=>['doubaowork:','chrome:'].includes(location.protocol)&&['doubaowork-chat','doubaowork-launcher'].includes(location.hostname)&&document.querySelector('[data-testid="chat-route-layout"]')&&document.getElementById('chat-route-main');
 if(!isClient())return {ok:false,reason:'不是豆包工作客户端主对话界面'};
 if(window.__DCS__?.transportVersion===3)return {ok:true,reused:true};
 if(window.__DCS__)window.__DCS__.destroy();
 const attributes=new Map();let staged=null,prepared=null;const originalRoot=document.documentElement.getAttribute('data-dcs-theme');let media=null,mediaKey='',objectURL='',generation=0,playingError='',style=null,expectedOpacity=null;
 function remember(node,attr){if(!attributes.has(node))attributes.set(node,new Map());const map=attributes.get(node);if(!map.has(attr))map.set(attr,node.getAttribute(attr));}
 function mark(node,attr){remember(node,attr);node.setAttribute(attr,'');}
 function unmark(){for(const [node,map]of attributes)for(const [attr,value]of map)value===null?node.removeAttribute(attr):node.setAttribute(attr,value);attributes.clear();}
 function clearMedia(){if(media){const v=media.querySelector('video');if(v){v.pause();v.removeAttribute('src');v.load();}media.remove();media=null;}if(objectURL)URL.revokeObjectURL(objectURL);objectURL='';mediaKey='';playingError='';}
 function beginMedia(config){cancelMedia();if(!/^[a-f\d-]{36}\.(png|jpg|jpeg|webp|gif|mp4|webm)$/.test(config.key)||!['image/png','image/jpeg','image/webp','image/gif','video/mp4','video/webm'].includes(config.type)||!Number.isInteger(config.size)||config.size<1||config.size>150*1024*1024)return {ok:false,reason:'媒体参数无效'};staged={...config,parts:[],received:0,index:0};return {ok:true};}
 function appendMedia(index,base64){if(!isClient()||!staged||index!==staged.index||base64.length>524288)throw new Error('媒体分块顺序或大小无效');const bin=atob(base64),bytes=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);if(staged.received+bytes.length>staged.size)throw new Error('媒体长度超出声明');staged.parts.push(bytes);staged.received+=bytes.length;staged.index++;return {ok:true,received:staged.received};}
 function finishMedia(){if(!staged||staged.received!==staged.size)throw new Error('媒体未完整接收');const blob=new Blob(staged.parts,{type:staged.type});prepared={key:staged.key,type:staged.type,url:URL.createObjectURL(blob)};const bytes=staged.received;staged=null;return {ok:true,bytes};}
 function cancelMedia(){staged=null;if(prepared)URL.revokeObjectURL(prepared.url);prepared=null;return {ok:true};}
 function layers(){unmark();const layout=document.querySelector('[data-testid="chat-route-layout"]');
  for(const child of layout.children)if(child.id!=='dcs-background')mark(child,'data-dcs-layer');
  const main=document.querySelector('#chat-route-main > main');
  const candidates=new Set([main,...document.querySelectorAll('[data-testid="message-list"],[data-testid="chat_input"],[data-testid="message_content"]')].filter(Boolean));
  for(const node of candidates){let parent=node.parentElement,nested=false;while(parent&&parent!==layout){if(candidates.has(parent)){nested=true;break;}parent=parent.parentElement;}
   mark(node,nested?'data-dcs-nested':'data-dcs-surface');parent=node.parentElement;while(parent&&parent!==layout){if(!candidates.has(parent))mark(parent,'data-dcs-shell');parent=parent.parentElement;}
  }
  for(const node of document.querySelectorAll('[data-testid="message-block-container"],[data-testid="union_message"],[data-testid="receive_message"],[data-testid="send_message"]'))mark(node,'data-dcs-nested');
  for(const node of document.querySelectorAll('[data-testid="send_message"] [class^="content-"],#chat-route-main > main div[class*="h-header-height"]'))mark(node,'data-dcs-nested');
 }
 async function apply(config){
  if(!isClient())return {ok:false,reason:'页面已离开客户端对话布局'};
  const ticket=++generation;
  if(!config.enabled){removeTheme();return {ok:true,disabled:true};}
  document.documentElement.setAttribute('data-dcs-theme','');
  if(!style){style=document.createElement('style');style.id='dcs-theme-style';document.head.append(style);}style.textContent=config.css;
  layers();
  const layout=document.querySelector('[data-testid="chat-route-layout"]');
  expectedOpacity=config.opacity;window.__DCS__.revision=config.revision;
  if(!config.mediaKey){clearMedia();return status();}
  if(config.mediaKey!==mediaKey||!media||!media.isConnected){
   if(!prepared||prepared.key!==config.mediaKey)return {ok:false,reason:'背景尚未传输完成'};
   const next=prepared;prepared=null;
   clearMedia();mediaKey=config.mediaKey;objectURL=next.url;
   media=document.createElement('div');media.id='dcs-background';media.setAttribute('aria-hidden','true');
   const video=config.mediaType.startsWith('video/'),element=document.createElement(video?'video':'img');
   if(video){element.muted=true;element.autoplay=true;element.loop=true;element.playsInline=true;element.preload='auto';}else element.alt='';
   const decode=new Promise(resolve=>{const timer=setTimeout(()=>resolve(false),15000);const done=ok=>{clearTimeout(timer);resolve(ok);};element.onerror=()=>{playingError='媒体无法解码';done(false);};video?element.onloadeddata=()=>done(true):element.onload=()=>done(true);});
   element.src=objectURL;media.append(element);layout.prepend(media);
   const decoded=await decode;if(ticket!==generation)return {ok:false,reason:'新设置已取代本次应用'};
   if(!decoded){playingError=playingError||'媒体解码超时';return {ok:false,reason:playingError};}
   if(video){try{await element.play();}catch{playingError='客户端拒绝自动播放';}}
  }
  window.__DCS__.revision=config.revision;return status();
 }
 function status(){const v=media?.querySelector('video'),image=media?.querySelector('img'),main=document.querySelector('#chat-route-main > main');const ready=!media||(v?v.readyState>=2&&(document.hidden||!v.paused):image?.complete&&image?.naturalWidth>0);const computed=main?getComputedStyle(main):null;const rgba=computed?.backgroundColor.match(/^rgba?\(([^)]+)\)$/);const parts=rgba?rgba[1].split(',').map(Number):[];const actualAlpha=parts.length===4?parts[3]:parts.length===3?1:null;const surfaceVerified=typeof expectedOpacity==='number'&&actualAlpha!==null&&Math.abs(actualAlpha-expectedOpacity)<.011;return {mediaKey,transportVersion:3,ok:!!style?.isConnected&&!!main&&!playingError&&!!ready&&surfaceVerified,surfaceVerified,actualAlpha,hasClientLayout:!!isClient(),hasStyle:!!style?.isConnected,hasMedia:!!media?.isConnected,videoReady:v?v.readyState:null,videoPlaying:v?!v.paused:null,imageReady:image?image.complete&&image.naturalWidth>0:null,surface:main?getComputedStyle(main).backgroundColor:null,opacity:main?getComputedStyle(main).opacity:null,revision:window.__DCS__?.revision,reason:playingError||(!ready?'媒体尚未就绪':!surfaceVerified?'对话底色实际值未匹配，请检查客户端版本适配':'')};}
 function removeTheme(){generation++;cancelMedia();clearMedia();style?.remove();style=null;unmark();originalRoot===null?document.documentElement.removeAttribute('data-dcs-theme'):document.documentElement.setAttribute('data-dcs-theme',originalRoot);}
 const entry=document.createElement('button');entry.id='dcs-settings-entry';entry.type='button';entry.textContent='皮肤设置';entry.style.cssText="position:fixed;right:16px;top:132px;z-index:2147483645;background:#252525;color:white;border:1px solid #666;border-radius:8px;padding:8px 12px;font:13px 'Microsoft YaHei UI',sans-serif;cursor:pointer;";entry.addEventListener('click',()=>{if(typeof window.__DCS_OPEN__==='function')window.__DCS_OPEN__('settings');});document.body.append(entry);
 const visibility=()=>{const v=media?.querySelector('video');if(!v)return;document.hidden?v.pause():v.play().catch(()=>{playingError='视频恢复播放失败';});};document.addEventListener('visibilitychange',visibility);
 window.__DCS__={apply,status,removeTheme,beginMedia,appendMedia,finishMedia,cancelMedia,transportVersion:3,revision:'',destroy(){cancelMedia();removeTheme();entry.remove();document.removeEventListener('visibilitychange',visibility);delete window.__DCS__;}};
 return {ok:true};
}
