// Hot-upgrade only surface styling; keeps the existing decoded video and Blob URL.
export function upgradeRegions(){
 if(!['doubaowork:','chrome:'].includes(location.protocol)||!['doubaowork-chat','doubaowork-launcher'].includes(location.hostname)||!window.__DCS__)return false;
 const api=window.__DCS__;if(api.regionVersion>=2)return true;
 const marked=new Map();let lastConfig=null;
 const roots=['[data-testid="flow_chat_sidebar"]','[data-testid="right-panel-container"]','[data-testid="samantha_layout_right_side"] section[class*="fixedPanel"]'];
 function set(node,attr){if(!marked.has(node))marked.set(node,new Map());if(!marked.get(node).has(attr))marked.get(node).set(attr,node.getAttribute(attr));if(!node.hasAttribute(attr))node.setAttribute(attr,'');}
 function update(){if(!lastConfig?.enabled)return;for(const node of marked.keys())if(!node.isConnected)marked.delete(node);const layout=document.querySelector('[data-testid="chat-route-layout"]');
  const surfaces=new Set(roots.flatMap(s=>[...document.querySelectorAll(s)]));
  for(const node of surfaces){let p=node.parentElement,covered=false;while(p&&p!==layout){if(surfaces.has(p)){covered=true;break;}p=p.parentElement;}set(node,covered?'data-dcs-nested':'data-dcs-surface');}
  const sidebar=document.querySelector('[data-testid="flow_chat_sidebar"]');if(sidebar)for(const node of sidebar.querySelectorAll('[data-testid="chat_list_wrapper"],[data-testid="conversation-section"]'))set(node,'data-dcs-nested');
  for(const node of document.querySelectorAll('[data-testid="samantha_layout_right_side"] [class*="fixedPanelHeader"],[data-testid="samantha_layout_right_side"] [class*="fixedPanelContent"],[data-testid="samantha_layout_right_side"] [class*="modalContent"],[data-testid="samantha_layout_right_side"] section[class*="group"]'))set(node,'data-dcs-nested');
 }
 function clear(){for(const [node,attrs]of marked)for(const [a,v]of attrs)v===null?node.removeAttribute(a):node.setAttribute(a,v);marked.clear();}
 const originalApply=api.apply,originalStatus=api.status,originalDestroy=api.destroy;
 let lastKey='';
 api.apply=async config=>{lastConfig=config;const key=JSON.stringify([config.enabled,config.opacity,config.dim,config.accent,config.surface,config.fit,config.mediaKey]);
  const prior=originalStatus();if(lastKey===key&&config.enabled&&prior.hasStyle&&prior.surfaceVerified&&(!config.mediaKey||prior.hasMedia)){api.revision=config.revision;return api.status();}
  const result=await originalApply(config);lastKey=key;if(config.enabled)update();else clear();return api.status();};
 api.status=()=>{const result=originalStatus();const video=document.querySelector('#dcs-background video');if(video&&video.readyState>=2&&!video.paused&&result.surfaceVerified&&result.hasStyle){result.ok=true;result.reason='';}result.regionVersion=2;return result;};
 let scheduled=null;const observer=new MutationObserver(()=>{if(!scheduled)scheduled=setTimeout(()=>{scheduled=null;update();},1000);});
 observer.observe(document.querySelector('[data-testid="chat-route-layout"]'),{childList:true,subtree:true});
 api.destroy=()=>{observer.disconnect();if(scheduled)clearTimeout(scheduled);clear();originalDestroy();};api.regionVersion=2;return true;
}

// Version 4: cover every inherited sidebar container, not just the scroll viewport.
// CSS covers newly mounted nodes; no additional observer or video work.
export function fixLeftSurfaces(){
 if(!['doubaowork:','chrome:'].includes(location.protocol)||!['doubaowork-chat','doubaowork-launcher'].includes(location.hostname)||!window.__DCS__)return false;
 const api=window.__DCS__;if(api.regionVersion===4)return true;
 let style=document.getElementById('dcs-left-fix-style');
 const maskSelector='#chat-route-main > main aside[class*="gutter-"] [class*="mask-"].pointer-events-none';
 const scrollSelector='[data-testid="flow_chat_sidebar"] div.bg-inherit';
 const rules=`html[data-dcs-theme] ${scrollSelector}{background:transparent!important;background-image:none!important;}html[data-dcs-theme] ${maskSelector}{background:transparent!important;background-image:none!important;}`;
 if(style&&style.textContent!==rules)style.textContent=rules;
 function mount(){const existing=[...document.querySelectorAll('#dcs-left-fix-style')];style=existing.shift();for(const duplicate of existing)duplicate.remove();if(!style){style=document.createElement('style');style.id='dcs-left-fix-style';document.head.append(style);}if(style.textContent!==rules)style.textContent=rules;}
 function clean(){style?.remove();style=null;}
 const apply=api.apply,status=api.status,destroy=api.destroy,remove=api.removeTheme;
 api.apply=async config=>{await apply(config);if(config.enabled)mount();else clean();return api.status();};
 api.status=()=>{const s=status();s.regionVersion=4;s.leftFixActive=!!style?.isConnected;return s;};
 api.removeTheme=()=>{clean();return remove();};api.destroy=()=>{clean();return destroy();};
 api.regionVersion=4;if(status().hasStyle)mount();return true;
}
