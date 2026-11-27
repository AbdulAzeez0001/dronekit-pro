// Bench-test page served at http://192.168.4.1/ (MIT).
// The full control panel lives in software/control-panel/; this is the
// minimum to check the link with the props OFF.
#pragma once

#include <Arduino.h>

static const char INDEX_HTML[] PROGMEM = R"HTML(<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DroneKit bench</title>
<style>
:root{--bg:#fff;--fg:#111;--mut:#666;--line:#ddd;--red:#c62828;--grn:#2e7d32}
@media (prefers-color-scheme:dark){:root{--bg:#111;--fg:#eee;--mut:#aaa;--line:#333}}
body{background:var(--bg);color:var(--fg);font:16px system-ui,sans-serif;margin:0;padding:16px;max-width:520px}
h1{font-size:20px;margin:0 0 4px}p.warn{color:var(--red);margin:0 0 12px}
.row{display:flex;gap:8px;margin:8px 0}button{flex:1;font-size:18px;padding:14px;border:1px solid var(--line);border-radius:8px;background:none;color:var(--fg)}
#kill{background:var(--red);color:#fff;border:0}label{display:block;margin-top:12px;color:var(--mut)}
input[type=range]{width:100%}table{width:100%;margin-top:12px;border-collapse:collapse}td{padding:4px 0;border-bottom:1px solid var(--line)}td+td{text-align:right}
</style></head><body>
<h1>DroneKit bench test</h1>
<p class="warn">Props off. Kill: the red button or the space bar.</p>
<div class="row"><button id="arm">Arm</button><button id="disarm">Disarm</button></div>
<div class="row"><button id="kill">KILL</button></div>
<label>Throttle <span id="tv">0.00</span></label><input id="thr" type="range" min="0" max="1" step="0.01" value="0">
<label>Roll</label><input class="spring" id="roll" type="range" min="-1" max="1" step="0.01" value="0">
<label>Pitch</label><input class="spring" id="pitch" type="range" min="-1" max="1" step="0.01" value="0">
<label>Yaw</label><input class="spring" id="yaw" type="range" min="-1" max="1" step="0.01" value="0">
<table id="t"></table>
<script>
const $=id=>document.getElementById(id);let ws,tlm={},me=0;
function connect(){ws=new WebSocket('ws://'+location.host+'/ws');
 ws.onmessage=e=>{const m=JSON.parse(e.data);
  if(m.type==='hello'){me=m.client_id;}
  else if(m.type==='telemetry'){const l=tlm.last;tlm=m;tlm.last=l;show();}
  else if(m.type==='error'||m.type==='event'){tlm.last=m.type+': '+m.msg;show();}};
 ws.onclose=()=>{tlm={last:'disconnected, retrying'};show();setTimeout(connect,1000);};}
function send(o){if(ws&&ws.readyState===1)ws.send(JSON.stringify(o));}
function show(){const rows=[['Pilot (this page)',tlm.pilot_id===undefined?undefined:tlm.pilot_id===me],['Arm asked',tlm.armed_cmd],['Betaflight armed',tlm.armed],
 ['Arming blocked flags',tlm.arming_disabled],['FC link',tlm.fc_link],['Battery V',tlm.vbat],
 ['Roll',tlm.roll],['Pitch',tlm.pitch],['Heading',tlm.heading],['Last message',tlm.last]];
 $('t').innerHTML=rows.map(r=>'<tr><td>'+r[0]+'</td><td>'+(r[1]===undefined?'-':r[1])+'</td></tr>').join('');}
document.querySelectorAll('.spring').forEach(s=>{const back=()=>{s.value=0};s.addEventListener('pointerup',back);s.addEventListener('touchend',back);});
$('thr').oninput=()=>{$('tv').textContent=(+$('thr').value).toFixed(2)};
$('arm').onclick=()=>send({type:'arm'});$('disarm').onclick=()=>send({type:'disarm'});
const kill=()=>{$('thr').value=0;$('tv').textContent='0.00';send({type:'kill'});};
$('kill').onclick=kill;document.addEventListener('keydown',e=>{if(e.code==='Space'){e.preventDefault();kill();}});
setInterval(()=>{if(document.visibilityState==='visible')send({type:'control',roll:+$('roll').value,pitch:+$('pitch').value,yaw:+$('yaw').value,throttle:+$('thr').value});},50);
connect();show();
</script></body></html>)HTML";
