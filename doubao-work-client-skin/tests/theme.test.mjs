import test from 'node:test';import assert from 'node:assert/strict';
import {normalize,css,supportedTarget,foreground} from '../src/theme.mjs';
test('只接受客户端内部协议，拒绝网页版与其他目标',()=>{assert.equal(supportedTarget({type:'page',url:'https://www.doubao.com/chat/',webSocketDebuggerUrl:'ws://127.0.0.1:9342/x'}),false);assert.equal(supportedTarget({type:'page',url:'doubaowork://doubaowork-chat/',webSocketDebuggerUrl:'ws://127.0.0.1:9342/x'}),true);assert.equal(supportedTarget({type:'node',url:'aha-runtime',webSocketDebuggerUrl:'ws://127.0.0.1:9333/x'}),false);});
test('不透明度保存0和1，不使用整体opacity',()=>{assert.equal(normalize({opacity:0}).opacity,0);assert.equal(normalize({opacity:1}).opacity,1);assert.ok(css({opacity:0}).includes('rgba(24,24,24,0)'));assert.ok(!css({opacity:.2}).includes('opacity:0.2'));});
test('拒绝颜色注入与媒体目录穿越',()=>{assert.equal(normalize({accent:'red;body{display:none}'}).accent,'#3370ff');assert.equal(normalize({media:'../secret'}).media,'');assert.equal(normalize({dim:Infinity}).dim,.18);});
test('明暗主题按钮前景保持对比',()=>{assert.equal(foreground('#ffffff'),'#000000');assert.equal(foreground('#000000'),'#ffffff');});
