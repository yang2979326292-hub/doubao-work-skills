// Client-only theme model. No browser extension APIs or webpage hosts.
export const DEFAULTS={version:1,enabled:true,accent:'#3370ff',surface:'#181818',opacity:0.82,dim:0.18,fit:'cover',media:'',mediaType:''};
export function normalize(input={}){
 const color=(v,d)=>typeof v==='string'&&/^#[a-f\d]{6}$/i.test(v)?v.toLowerCase():d;
 const num=(v,d)=>typeof v==='number'&&Number.isFinite(v)?Math.max(0,Math.min(1,v)):d;
 return {version:1,enabled:typeof input.enabled==='boolean'?input.enabled:true,accent:color(input.accent,DEFAULTS.accent),surface:color(input.surface,DEFAULTS.surface),opacity:num(input.opacity,.82),dim:num(input.dim,.18),fit:input.fit==='contain'?'contain':'cover',media:typeof input.media==='string'&&/^[a-f\d-]{36}\.(png|jpg|jpeg|webp|gif|mp4|webm)$/.test(input.media)?input.media:'',mediaType:['image/png','image/jpeg','image/webp','image/gif','video/mp4','video/webm'].includes(input.mediaType)?input.mediaType:''};
}
export const TARGET_HOSTS=['doubaowork-chat','doubaowork-launcher'];
export function supportedTarget(t){try{const u=new URL(t.url);return t.type==='page'&&u.protocol==='doubaowork:'&&TARGET_HOSTS.includes(u.hostname)&&!!t.webSocketDebuggerUrl;}catch{return false;}}
export function foreground(hex){const c=hex.match(/[\da-f]{2}/gi).map(v=>{const x=parseInt(v,16)/255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4;});const l=.2126*c[0]+.7152*c[1]+.0722*c[2];return (l+.05)/.05>=1.05/(l+.05)?'#000000':'#ffffff';}
export function css(input){const c=normalize(input),rgba=`rgba(${c.surface.match(/[\da-f]{2}/gi).map(x=>parseInt(x,16)).join(',')},${c.opacity})`;
return `html[data-dcs-theme]{--dcs-accent:${c.accent};--dcs-surface:${rgba};--dcs-text:${foreground(c.surface)};--dcs-on-accent:${foreground(c.accent)};--brand-primary:${c.accent}!important;--color-primary:${c.accent}!important;}
html[data-dcs-theme] [data-testid="chat-route-layout"]{position:relative!important;isolation:isolate;background:${c.surface}!important;}
#dcs-background{position:absolute;inset:0;z-index:0;pointer-events:none;overflow:hidden;}
#dcs-background img,#dcs-background video{width:100%;height:100%;display:block;object-fit:${c.fit};}
#dcs-background::after{content:'';position:absolute;inset:0;background:rgba(0,0,0,${c.dim});}
html[data-dcs-theme] [data-dcs-layer]{position:relative!important;z-index:1!important;}
html[data-dcs-theme] [data-dcs-shell]{background:transparent!important;background-image:none!important;}
html[data-dcs-theme] [data-dcs-surface]{background:${rgba}!important;color:var(--dcs-text)!important;}
html[data-dcs-theme] [data-dcs-nested]{background:transparent!important;background-image:none!important;}
html[data-dcs-theme] [data-testid="chat_input"]>.guidance-input-surface,
html[data-dcs-theme] [data-testid="chat_input_input"],
html[data-dcs-theme] [data-testid="chat_input_input"] [contenteditable="true"]{background:transparent!important;color:var(--dcs-text)!important;}
html[data-dcs-theme] [data-testid="message_text_content"],html[data-dcs-theme] [data-testid="message_content"]{color:var(--dcs-text)!important;}
html[data-dcs-theme] [data-testid="message_text_content"] :where(p,span,h1,h2,h3,h4,li,strong,em,blockquote){color:inherit!important;}
html[data-dcs-theme] [data-testid="chat_input_send_button"]:not(:disabled){background:var(--dcs-accent)!important;color:var(--dcs-on-accent)!important;}
html[data-dcs-theme] [data-testid="chat_input_send_button"]:hover:not(:disabled){filter:brightness(.9);}
html[data-dcs-theme] [data-testid="message_text_content"] a{color:var(--dcs-accent)!important;}
html[data-dcs-theme] [data-testid="conversation-list-v2-item"]:hover{background:color-mix(in srgb,var(--dcs-accent) 15%,transparent)!important;}
#dcs-settings-entry{position:fixed;right:16px;top:132px;z-index:2147483645;background:#252525;color:white;border:1px solid #666;border-radius:8px;padding:8px 12px;font:13px 'Microsoft YaHei UI',sans-serif;cursor:pointer;}
`;
}
