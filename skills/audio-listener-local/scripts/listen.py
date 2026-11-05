#!/usr/bin/env python3
"""Local audio evidence: bounded decoding, ASR, sound tags, acoustic measurements."""
from pathlib import Path
import argparse, hashlib, json, math, os, sys, time, wave
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.runtime'/'deps'))
SPEECH='sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17'
EVENTS='sherpa-onnx-zipformer-small-audio-tagging-2024-04-15'
RATE=16000

def save_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def prepare_output(path):
    path=Path(path).resolve()
    if path.exists() and any(path.iterdir()): raise ValueError('OUTPUT_NOT_EMPTY: Choose a new output folder; existing files will not be overwritten')
    path.mkdir(parents=True,exist_ok=True)
    return path

def decode(path,max_seconds=1800):
    import av,numpy as np
    path=Path(path).resolve(strict=True)
    if not path.is_file(): raise ValueError('INPUT_NOT_FILE')
    if path.stat().st_size>1024**3: raise ValueError('INPUT_TOO_LARGE: maximum 1 GiB')
    chunks=[]; count=0
    with av.open(str(path)) as c:
        if not c.streams.audio: raise ValueError('NO_AUDIO_STREAM')
        s=c.streams.audio[0]
        metadata={'codec':s.codec_context.name,'sample_rate':s.codec_context.sample_rate,'channels':s.codec_context.channels,'source_bytes':path.stat().st_size}
        resampler=av.AudioResampler(format='flt',layout='mono',rate=RATE)
        for frame in c.decode(s):
            for f in resampler.resample(frame):
                a=f.to_ndarray().flatten(); count+=len(a)
                if count>max_seconds*RATE: raise ValueError(f'DURATION_LIMIT: maximum {max_seconds}s; not silently truncated')
                chunks.append(a)
        for f in resampler.resample(None):
            a=f.to_ndarray().flatten();count+=len(a);chunks.append(a)
    if count>max_seconds*RATE: raise ValueError('DURATION_LIMIT')
    if not chunks or count==0: raise ValueError('EMPTY_AUDIO')
    samples=np.concatenate(chunks).astype('float32')
    if not np.isfinite(samples).all(): raise ValueError('NON_FINITE_AUDIO')
    metadata['duration_seconds']=round(len(samples)/RATE,4)
    return samples,metadata

def write_wav(path,samples):
    import numpy as np
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
        w.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())

def acoustic(samples):
    import numpy as np
    from scipy.signal import correlate,find_peaks
    rms=float(np.sqrt(np.mean(samples.astype('float64')**2)))
    frames=len(samples)//320
    env=np.sqrt(np.mean(samples[:frames*320].reshape(-1,320)**2,axis=1)) if frames else np.array([rms])
    onset=np.maximum(0,np.diff(env))
    tempo=None; strength=None
    if len(onset)>250 and float(np.std(onset))>0.0002:
        corr=correlate(onset-onset.mean(),onset-onset.mean(),mode='full',method='fft')[len(onset)-1:]
        lo,hi=int(50*60/200),int(50*60/50)
        lag=lo+int(np.argmax(corr[lo:hi+1])); strength=float(corr[lag]/max(corr[0],1e-15))
        if strength>0.12: tempo=round(60*50/lag,1)
    return {'rms_dbfs':round(20*math.log10(max(rms,1e-12)),2),'peak_dbfs':round(20*math.log10(max(float(np.max(np.abs(samples))),1e-12)),2),'near_silence_fraction':round(float(np.mean(env<0.003)),4),'tempo_bpm_estimate':tempo,'tempo_periodicity_score':None if strength is None else round(strength,4),'tempo_caveat':'能量包络周期估计，不是拍点真值；可能存在半速/倍速歧义，讲话与机械声也可能产生节律。'}

def model_paths():
    return ROOT/'.runtime'/'models'/SPEECH,ROOT/'.runtime'/'models'/EVENTS

def doctor():
    import importlib.util
    speech,events=model_paths()
    deps={m:importlib.util.find_spec(m) is not None for m in ['av','numpy','scipy','sherpa_onnx','PIL']}
    files={str(p):p.is_file() for p in [speech/'model.int8.onnx',speech/'tokens.txt',events/'model.int8.onnx',events/'class_labels_indices.csv']}
    return {'ready':all(deps.values()) and all(files.values()),'dependencies':deps,'models':files,'runtime':str(ROOT/'.runtime'),'inference':'local CPU; no media upload'}

def tagger_create():
    import sherpa_onnx as s
    _,p=model_paths()
    config=s.AudioTaggingConfig(model=s.AudioTaggingModelConfig(zipformer=s.OfflineZipformerAudioTaggingModelConfig(model=str(p/'model.int8.onnx')),num_threads=2,debug=False,provider='cpu'),labels=str(p/'class_labels_indices.csv'),top_k=8)
    if not config.validate(): raise ValueError('INVALID_EVENT_MODEL')
    return s.AudioTagging(config)

def event_windows(samples,tagger):
    import numpy as np
    windows=[]
    for start in range(0,len(samples),10*RATE):
        x=samples[start:start+10*RATE]
        if float(np.sqrt(np.mean(x.astype('float64')**2)))<0.0001:
            tags=[{'name':'Silence','score':1.0,'index':494,'measurement_only':True}]
        else:
            stream=tagger.create_stream();stream.accept_waveform(sample_rate=RATE,waveform=x)
            tags=[{'name':e.name,'index':int(e.index),'score':round(float(e.prob),5)} for e in tagger.compute(stream)]
        windows.append({'start':round(start/RATE,3),'end':round((start+len(x))/RATE,3),'tags':tags})
    return windows

def _meaningful(text):
    """过滤只有标点或单字符的伪转写。"""
    import re as _re
    core=_re.sub(r'[\s\W_]+','',text,flags=_re.UNICODE)
    return len(core)>=2

def speech_segments(samples,recognizer,events):
    import numpy as np
    result=[]
    # 25-second chunks bound CPU/memory; report chunk boundaries rather than invented word timing.
    for start in range(0,len(samples),25*RATE):
        x=samples[start:start+25*RATE];end=start+len(x)
        if float(np.sqrt(np.mean(x.astype('float64')**2)))<0.0001: continue
        # Avoid ASR hallucinations on clearly non-speech windows when event evidence is available.
        overlap=[w for w in events if w['end']>start/RATE and w['start']<end/RATE]
        speech_score=max([t['score'] for w in overlap for t in w['tags'] if t['index'] in (0,1,2,3,4,5,6,7,8,9)] or [0])
        if overlap and speech_score<0.12: continue
        stream=recognizer.create_stream();stream.accept_waveform(RATE,x);recognizer.decode_stream(stream)
        r=stream.result
        text=r.text.strip()
        if not text or not _meaningful(text): continue
        row={'start':round(start/RATE,3),'end':round(end/RATE,3),'text':text,'timing':'chunk interval, not forced alignment'}
        for k in ('lang','emotion','event','timestamps','tokens'):
            v=getattr(r,k,None)
            if v is not None:
                if k=='timestamps': v=[round(start/RATE+float(t),3) for t in v]
                elif k=='tokens':v=list(v)
                else:v=str(v)
                row[k]=v
        result.append(row)
    return result

def analyze(source,output,mode='both',language='auto',max_seconds=1800):
    import sherpa_onnx as s
    samples,meta=decode(source,max_seconds)
    speech,events_path=model_paths()
    needed=[]
    if mode in ('both','speech'):needed += [speech/'model.int8.onnx',speech/'tokens.txt']
    if mode in ('both','sounds'):needed += [events_path/'model.int8.onnx',events_path/'class_labels_indices.csv']
    if any(not p.is_file() for p in needed): raise ValueError('MODEL_MISSING: run scripts/setup.py --models')
    out=prepare_output(output); started=time.monotonic()
    ev=event_windows(samples,tagger_create()) if mode in ('both','sounds') else []
    seg=[]
    if mode in ('both','speech'):
        r=s.OfflineRecognizer.from_sense_voice(model=str(speech/'model.int8.onnx'),tokens=str(speech/'tokens.txt'),num_threads=2,provider='cpu',language=language,use_itn=True)
        seg=speech_segments(samples,r,ev)
    metrics=acoustic(samples)
    singing=max([t['score'] for w in ev for t in w['tags'] if t['name']=='Singing'] or [0])
    payload={'status':'complete','source':str(Path(source).resolve()),'source_sha256':hashlib.file_digest(Path(source).open('rb'),'sha256').hexdigest(),'metadata':meta,'mode':mode,'inference_location':'local CPU','media_uploaded':False,'speech':seg,'sound_windows':ev,'acoustic':metrics,'singing_max_score':round(singing,4),'singing_hint':('检测到演唱类标签，音频可能含歌唱人声；其歌词转写不可靠，不应作为准确歌词引用' if singing>=0.12 else None),'elapsed_seconds':round(time.monotonic()-started,3),'limitations':['声音标签为候选分类，分数非校准概率；不据此断言真实事件或人物身份。','音乐风格/乐器仅在标签证据支持时描述；不支持曲名检索、完整配器识别、专业和声分析。','转写可能有错漏；both模式会过滤低人声分数片段，怀疑漏词时以speech模式复核。','无说话人身份识别；不推断健康、心理状态。','分块边缘可能断句；逐字时间戳若存在为模型估计。']}
    save_json(out/'analysis.json',payload)
    text='\n'.join(x['text'] for x in seg)
    (out/'transcript.txt').write_text(text or '未检出可可靠转写的人声。',encoding='utf-8-sig')
    lines=['# 本地音频识别结果','',f"输入：{Path(source).name}",f"时长：{meta['duration_seconds']} 秒",'处理：本地 CPU，未上传素材。','','## 人声转写']
    lines += [f"- [{x['start']:.2f}–{x['end']:.2f}s] {x['text']}" for x in seg] or ['未检出可可靠转写的人声。']
    if payload['singing_hint']:
        lines += ['', '## 演唱提示', payload['singing_hint'] + f"（Singing 最高分 {payload['singing_max_score']}）"]
    lines += ['','## 音乐、音效和环境声候选','标签及分数是识别证据，不是确定事实。']
    for w in ev:
        tags='；'.join(f"{t['name']} ({t['score']:.3f})" for t in w['tags'] if t['score']>=0.12)
        lines.append(f"- [{w['start']:.2f}–{w['end']:.2f}s] {tags or '无高分候选，无法确定'}")
    lines += ['','## 声学测量',f"RMS：{metrics['rms_dbfs']} dBFS；近静音占比：{metrics['near_silence_fraction']}",f"节奏估计：{metrics['tempo_bpm_estimate']} BPM（None 表示未得到可靠周期）",metrics['tempo_caveat'],'','## 边界与未覆盖项']+['- '+x for x in payload['limitations']]
    (out/'音频识别结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    return payload

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--doctor',action='store_true');ap.add_argument('--input');ap.add_argument('--output');ap.add_argument('--mode',choices=['both','speech','sounds'],default='both');ap.add_argument('--language',choices=['auto','zh','en','ja','ko','yue'],default='auto');ap.add_argument('--max-seconds',type=int,default=1800)
    a=ap.parse_args()
    try:
        if a.doctor:
            r=doctor();print(json.dumps(r,ensure_ascii=False));return 0 if r['ready'] else 2
        if not a.input or not a.output: ap.error('--input and --output are required')
        if not 1<=a.max_seconds<=7200:ap.error('--max-seconds must be 1..7200')
        r=analyze(a.input,a.output,a.mode,a.language,a.max_seconds)
        print(json.dumps({'status':r['status'],'output':str(Path(a.output).resolve()),'speech_chunks':len(r['speech']),'sound_windows':len(r['sound_windows'])},ensure_ascii=False));return 0
    except Exception as e:
        print(json.dumps({'status':'error','error_type':type(e).__name__,'message':str(e)},ensure_ascii=False),file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
