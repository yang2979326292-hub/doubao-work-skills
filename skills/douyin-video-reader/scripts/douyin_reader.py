#!/usr/bin/env python3
"""抖音作品程序化读取：短链解析 → 结构化作品数据 → 媒体下载 → 本地证据。

不需要用户打开浏览器、登录或点击：
- 短链解析走纯 HTTP 跳转；
- 作品数据优先读页面内嵌 SSR JSON，读不到时用无窗口(headless) Chromium 载入同一条
  作品页，从页面自身的服务端渲染数据(flight payload)或页面 API 响应中取回作品对象；
- 图文作品取图片与配乐音轨，视频作品取 mp4、抽帧并交本地 ASR 转写。
所有字段都来自站点返回，脚本不生成画面描述。
"""
from pathlib import Path
import argparse, hashlib, ipaddress, json, re, socket, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = Path(__file__).resolve().parents[1]
AUDIO_SKILL = ROOT.parent / 'audio-listener-local'
sys.path.insert(0, str(ROOT / '.runtime' / 'deps'))
sys.path.insert(0, str(AUDIO_SKILL / '.runtime' / 'deps'))
sys.path.insert(0, str(AUDIO_SKILL / 'scripts'))

UA_PC = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
         '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
PAGE_HOSTS = {'v.douyin.com', 'www.douyin.com', 'douyin.com', 'www.iesdouyin.com',
              'iesdouyin.com', 'm.douyin.com'}
MEDIA_SUFFIXES = ('douyinvod.com', 'douyin.com', 'iesdouyin.com', 'bytecdn.cn', 'bytedance.com',
                  'ibytedtos.com', 'byteimg.com', 'snssdk.com', 'amemv.com', 'douyinpic.com',
                  'douyinstatic.com', 'zjcdn.com', 'pstatp.com')
MAX_BYTES = 1024 ** 3


class ReaderError(Exception):
    pass


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def check_url(url, page=False):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ReaderError('UNSAFE_URL: 仅接受 HTTPS、无用户信息、无自定义端口')
    h = p.hostname.lower()
    if page:
        if h not in PAGE_HOSTS:
            raise ReaderError('UNSUPPORTED_PLATFORM: 不是抖音页面域名')
        for addr in socket.getaddrinfo(h, 443, type=socket.SOCK_STREAM):
            if not ipaddress.ip_address(addr[4][0]).is_global:
                raise ReaderError('PRIVATE_ADDRESS_REJECTED')
    elif not any(h == s or h.endswith('.' + s) for s in MEDIA_SUFFIXES):
        raise ReaderError(f'UNSUPPORTED_MEDIA_HOST: {h}')
    return url


def http_get(url, page=False, timeout=30):
    check_url(url, page)
    req = urllib.request.Request(url, headers={'User-Agent': UA_PC, 'Referer': 'https://www.douyin.com/'})
    return urllib.request.urlopen(req, timeout=timeout)


def extract_link(text):
    urls = re.findall(r'https://[^\s<>"\u3000]+', text or '')
    urls = [u.rstrip('。，；！、）)]}”\'') for u in urls]
    valid = [u for u in urls if urllib.parse.urlsplit(u).hostname in PAGE_HOSTS]
    if not valid:
        raise ReaderError('LINK_REQUIRED: 需要一条抖音链接（v.douyin.com 或 www.douyin.com/video|note）')
    return valid[0]


def resolve_link(text):
    link = extract_link(text)
    with http_get(link, page=True) as r:
        final = r.url
        r.read(1)
    path = urllib.parse.urlsplit(final).path
    if re.search(r'/(login|passport|verify|captcha)(/|\?)', path, re.I):
        raise ReaderError('AUTH_REQUIRED: 链接进入登录/验证页，停止，不绕过')
    m = re.search(r'/(video|note|slides)/(\d{6,})', path)
    if not m:
        raise ReaderError(f'UNSUPPORTED_PAGE: 无法从 {final} 识别作品 ID')
    return {'source_url': link, 'resolved_url': final,
            'kind': 'video' if m.group(1) == 'video' else 'note', 'aweme_id': m.group(2)}


# ---------- 作品对象定位 ----------

def _walk_item(obj, want_id=None, fallback=None):
    if isinstance(obj, dict):
        if 'aweme_id' in obj or 'awemeId' in obj:
            got = str(obj.get('aweme_id') or obj.get('awemeId'))
            body = any(k in obj for k in ('desc', 'images', 'video', 'stats', 'authorInfo'))
            if body:
                if want_id is not None and got == str(want_id):
                    return obj
                if fallback is not None and fallback.get('item') is None:
                    fallback['item'] = obj
                return None
        for v in obj.values():
            found = _walk_item(v, want_id, fallback)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _walk_item(v, want_id, fallback)
            if found:
                return found
    return None


def find_item(data, want_id=None, allow_fallback=False):
    fallback = {'item': None}
    item = _walk_item(data, want_id, fallback)
    return item or (fallback['item'] if allow_fallback else None)


FLIGHT_PUSH = re.compile(r'self\.__pace_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)')


def flight_payload(html):
    """把 React flight 推送的字符串片段拼回完整数据流。"""
    parts = []
    for m in FLIGHT_PUSH.finditer(html):
        try:
            parts.append(json.loads(m.group(1)))
        except ValueError:
            continue
    return ''.join(parts)


def item_from_flight(html, aweme_id):
    flight = flight_payload(html)
    for anchor in (f'"awemeId":"{aweme_id}","aweme":',
                   f'"awemeId":"{aweme_id}",'):
        idx = flight.find(anchor)
        if idx < 0:
            continue
        start = flight.find('{', idx + len(anchor))
        if start < 0:
            continue
        try:
            wrapper, _ = json.JSONDecoder().raw_decode(flight[start:])
        except ValueError:
            continue
        detail = wrapper.get('detail') or wrapper
        if isinstance(detail, dict) and str(detail.get('awemeId') or detail.get('aweme_id')) == aweme_id:
            return detail
    return None


def item_from_ssr(kind, aweme_id):
    """纯 HTTP 通道：极少数页面仍内嵌作品 JSON。"""
    for url in (f'https://www.iesdouyin.com/share/{kind}/{aweme_id}/',
                f'https://www.douyin.com/{kind}/{aweme_id}'):
        try:
            with http_get(url, page=True) as r:
                body = r.read(4 * 1024 * 1024).decode('utf-8', 'ignore')
        except Exception:
            continue
        flight_item = item_from_flight(body, aweme_id)
        if flight_item:
            return flight_item, 'http:flight'
        for marker in ('window._ROUTER_DATA', 'window.__INITIAL_STATE__'):
            idx = body.find(marker)
            if idx < 0:
                continue
            start = body.find('{', idx)
            try:
                data, _ = json.JSONDecoder().raw_decode(body[start:])
            except ValueError:
                continue
            item = find_item(data, aweme_id)
            if item:
                return item, f'http:{marker}'
    return None, None


def item_from_page(kind, aweme_id, debug=False):
    """无窗口 Chromium：载入作品页，从页面 SSR 数据或页面 API 响应取回作品对象。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise ReaderError(f'PLAYWRIGHT_MISSING: {e}. 先运行 scripts/setup.py --dependencies')
    target = f'https://www.douyin.com/{kind}/{aweme_id}'
    responses = {}
    engine = None

    with sync_playwright() as p:
        launch = {'headless': True,
                  'args': ['--disable-blink-features=AutomationControlled', '--lang=zh-CN', '--mute-audio']}
        try:
            browser = p.chromium.launch(channel='chrome', **launch)
            engine = 'chrome-headless'
        except Exception:
            browser = p.chromium.launch(**launch)
            engine = 'chromium-headless'
        ctx = browser.new_context(user_agent=UA_PC, locale='zh-CN', viewport={'width': 1440, 'height': 900})
        page = ctx.new_page()

        def on_response(resp):
            """页面自身发出的 aweme 接口响应：视频页的作品对象只在这里出现。"""
            if 'item' in responses or '/aweme/' not in resp.url:
                return
            try:
                data = resp.json()
            except Exception:
                return
            if isinstance(data, dict) and isinstance(data.get('aweme_detail'), dict):
                cand = data['aweme_detail']
                if str(cand.get('aweme_id') or cand.get('awemeId')) == aweme_id:
                    responses['item'] = cand
                    responses['channel'] = resp.url.split('?')[0]
                    if debug:
                        print(f'[debug] xhr {responses["channel"]} -> aweme {aweme_id}', file=sys.stderr)
                    return
            item = find_item(data, aweme_id)
            if item:
                responses['item'] = item
                responses['channel'] = resp.url.split('?')[0]
                if debug:
                    print(f'[debug] xhr {responses["channel"]} -> aweme {aweme_id}', file=sys.stderr)

        page.on('response', on_response)
        page.goto(target, wait_until='domcontentloaded', timeout=45000)
        # 文件页的数据在页面 HTML 里；视频页要等页面自己发 detail 请求，故两段式等待。
        page.wait_for_timeout(3000)
        html = page.content()
        if not item_from_flight(html, aweme_id):
            for _ in range(24):
                if 'item' in responses:
                    break
                page.wait_for_timeout(500)
        if 'item' not in responses:
            html = page.content()
        if debug:
            print(f'[debug] page title={page.title()!r} html={len(html)}B '
                  f'flight_hit={bool(item_from_flight(html, aweme_id))} api_hit={"item" in responses}',
                  file=sys.stderr)
        ctx.close()
        browser.close()

    item = item_from_flight(html, aweme_id)
    if item:
        return item, f'{engine}:flight'
    if 'item' in responses:
        return responses['item'], f'{engine}:api({responses.get("channel", "")})'
    if re.search(r'pageNeedLogin|请先登录|login-modal', html):
        raise ReaderError('AUTH_REQUIRED: 页面要求登录/验证，停止，不绕过')
    raise ReaderError('ITEM_DATA_UNAVAILABLE: 页面未返回作品数据（该作品可能已删除、私密或受限）')


# ---------- 字段归一化 ----------

def addr_url(addr):
    """兼容 {src} / {urlList} / {url_list} 三种地址结构。"""
    if isinstance(addr, str):
        return addr.replace('http://', 'https://')
    if isinstance(addr, list):
        for a in addr:
            u = addr_url(a)
            if u:
                return u
        return None
    if isinstance(addr, dict):
        for key in ('urlList', 'url_list'):
            vals = addr.get(key) or []
            for u in vals:
                if isinstance(u, str) and u:
                    return u.replace('http://', 'https://')
        for key in ('src', 'url'):
            if isinstance(addr.get(key), str) and addr[key]:
                return addr[key].replace('http://', 'https://')
    return None


def fmt_time(epoch):
    if not epoch:
        return None
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(epoch)))
    except (ValueError, OSError, OverflowError):
        return None


def normalize(item, resolved, extraction):
    images = [u for u in (addr_url(i) for i in (item.get('images') or [])) if u]
    video = item.get('video') or {}
    music = item.get('music') or {}
    author = item.get('authorInfo') or item.get('author') or {}
    stats = item.get('stats') or item.get('statistics') or {}
    texts = item.get('textExtra') or item.get('text_extra') or []
    tags = [t.get('hashtagName') or t.get('hashtag_name') for t in texts
            if (t.get('hashtagName') or t.get('hashtag_name'))]
    duration_ms = video.get('duration') or 0
    is_note = bool(images) or str(item.get('awemeType') or item.get('aweme_type') or '') in ('68', '150')
    play = addr_url(video.get('playAddr') or video.get('play_addr'))
    stat_map = {}
    for camel, snake, label in (('diggCount', 'digg_count', '点赞'), ('commentCount', 'comment_count', '评论'),
                                ('shareCount', 'share_count', '分享'), ('collectCount', 'collect_count', '收藏'),
                                ('playCount', 'play_count', '播放')):
        val = stats.get(camel) if stats.get(camel) is not None else stats.get(snake)
        if val is not None:
            stat_map[label] = val
    return {
        'aweme_id': str(item.get('awemeId') or item.get('aweme_id') or resolved['aweme_id']),
        'kind': 'note' if is_note else 'video',
        'desc': (item.get('desc') or '').strip(),
        'title': (item.get('itemTitle') or item.get('caption') or '').strip(),
        'author': author.get('nickname', ''),
        'author_sec_uid': author.get('secUid') or author.get('sec_uid', ''),
        'create_time': fmt_time(item.get('createTime') or item.get('create_time')),
        'hashtags': tags,
        'duration_seconds': round(duration_ms / 1000, 2) if duration_ms else None,
        'images': images,
        'image_count': len(images),
        'video_url': None if is_note else play,
        'music': {
            'id': music.get('idStr') or music.get('id'),
            'title': music.get('title') or music.get('musicName', ''),
            'author': music.get('author') or music.get('ownerNickname', ''),
            'duration_seconds': music.get('duration'),
            'audio_url': addr_url(music.get('playUrl') or music.get('play_url')) or play,
            'is_original_sound': bool(music.get('isOriginal')),
            'user_count': music.get('userCount'),
        },
        'statistics': stat_map,
        'source_url': resolved['source_url'],
        'resolved_url': resolved['resolved_url'],
        'extraction': extraction,
        'retrieval': 'HTTP 短链解析 + 页面数据（无登录、无人工操作）',
    }


# ---------- 媒体下载与本地证据 ----------

def acquire(kind, aweme_id, debug=False, attempts=2):
    """取作品对象：HTTP 优先，失败再走无窗口页面；瞬时失败重试一次，登录墙不重试。"""
    last = None
    for n in range(attempts):
        item, extraction = item_from_ssr(kind, aweme_id)
        if item:
            return item, extraction
        try:
            return item_from_page(kind, aweme_id, debug)
        except ReaderError as e:
            last = e
            if 'AUTH_REQUIRED' in str(e) or 'PLAYWRIGHT_MISSING' in str(e):
                raise
            if n + 1 < attempts:
                if debug:
                    print(f'[debug] retry #{n + 1}: {e}', file=sys.stderr)
                time.sleep(3)
    raise last


def download(url, path):
    check_url(url)
    part = path.with_suffix(path.suffix + '.part')
    total = 0
    with http_get(url, timeout=60) as r, part.open('wb') as f:
        ctype = r.headers.get('Content-Type', '')
        if ctype.startswith('text/'):
            raise ReaderError('NOT_MEDIA_RESPONSE')
        while chunk := r.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_BYTES:
                raise ReaderError('DOWNLOAD_LIMIT: 单文件上限 1 GiB')
            f.write(chunk)
    if not total:
        raise ReaderError('EMPTY_DOWNLOAD')
    part.replace(path)
    return total


def prepare_output(path):
    p = Path(path).resolve()
    if p.exists() and any(p.iterdir()):
        raise ReaderError('OUTPUT_NOT_EMPTY: 请换一个新目录，已有文件不会被覆盖')
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_image(url, dest):
    from PIL import Image
    raw = dest.with_suffix('.raw')
    download(url, raw)
    try:
        with Image.open(raw) as im:
            im = im.convert('RGB')
            im.thumbnail((1600, 1600))
            out = dest.with_suffix('.jpg')
            im.save(out, quality=90)
            return out, im.size
    finally:
        if raw.exists():
            raw.unlink()


def video_overview(video, out, interval=2.0, max_frames=60, max_seconds=1800):
    import av, numpy as np
    from PIL import Image, ImageDraw
    rows, next_t, last_t = [], 0.0, None
    with av.open(str(video)) as c:
        if not c.streams.video:
            raise ReaderError('NO_VIDEO_STREAM')
        s = c.streams.video[0]
        duration = float(s.duration * s.time_base) if s.duration else (float(c.duration / av.time_base) if c.duration else None)
        if duration and duration > max_seconds:
            raise ReaderError('DURATION_LIMIT')
        if duration:
            interval = max(interval, duration / max(1, max_frames - 1))
        origin = float(s.start_time * s.time_base) if s.start_time is not None else 0.0
        meta = {'width': s.codec_context.width, 'height': s.codec_context.height,
                'duration_seconds': duration, 'audio_streams': len(c.streams.audio),
                'codec': s.codec_context.name, 'sampling_interval_seconds': round(interval, 3),
                'sampling': '均匀概览，不是逐帧检查'}
        frame_dir = out / 'frames'
        frame_dir.mkdir(exist_ok=True)
        for f in c.decode(s):
            if f.time is None:
                continue
            t = max(0, float(f.time) - origin)
            last_t = t
            if t > max_seconds:
                raise ReaderError('DURATION_LIMIT: 不会静默截断')
            if t + 0.001 < next_t:
                continue
            if len(rows) >= max_frames:
                break
            img = f.to_image()
            img.thumbnail((1280, 1280))
            name = f'frame_{len(rows) + 1:03d}.jpg'
            img.save(frame_dir / name, quality=91)
            rows.append({'time_seconds': round(t, 3), 'file': str((frame_dir / name).resolve())})
            next_t = t + interval
    if not rows:
        raise ReaderError('NO_DECODABLE_FRAMES')
    meta['sampled_until_seconds'] = last_t
    sheets = []
    for base in range(0, len(rows), 12):
        group = rows[base:base + 12]
        canvas = Image.new('RGB', (960, 270 * ((len(group) + 2) // 3)), (22, 22, 22))
        d = ImageDraw.Draw(canvas)
        for i, row in enumerate(group):
            with Image.open(row['file']) as im:
                im.thumbnail((312, 235))
                x = (i % 3) * 320 + (320 - im.width) // 2
                y = (i // 3) * 270
                canvas.paste(im, (x, y))
                d.text(((i % 3) * 320 + 8, y + 242), f"{row['time_seconds']:.2f}s", fill='white')
        p = out / f'contact_{base // 12 + 1:02d}.jpg'
        canvas.save(p, quality=90)
        sheets.append(str(p.resolve()))
    return meta, rows, sheets


def extract_audio(media, out):
    from listen import decode, write_wav
    try:
        samples, meta = decode(media)
    except ValueError as e:
        return None, str(e)
    audio = out / 'audio.wav'
    write_wav(audio, samples)
    return str(audio.resolve()), meta


def run(text, output, interval=2.0, max_frames=60, audio_mode='both', debug=False):
    resolved = resolve_link(text)
    item, extraction = acquire(resolved['kind'], resolved['aweme_id'], debug)
    info = normalize(item, resolved, extraction)
    out = prepare_output(output)
    save_json(out / 'item.json', info)

    media = {'video': None, 'audio': None, 'images': []}
    if info['kind'] == 'video':
        if not info['video_url']:
            raise ReaderError('NO_PLAYABLE_MEDIA')
        video = out / 'source.mp4'
        download(info['video_url'], video)
        media['video'] = str(video.resolve())
        meta, rows, sheets = video_overview(video, out, interval, max_frames)
        info['video'] = meta
        info['frames'] = rows
        info['contact_sheets'] = sheets
        audio_path, ameta = extract_audio(video, out)
        media['audio'] = audio_path
        info['audio_source'] = '视频自带音轨'
        info['audio_stream'] = ameta
    else:
        img_dir = out / 'images'
        img_dir.mkdir(exist_ok=True)
        rows = []
        for i, url in enumerate(info['images'], start=1):
            f, size = save_image(url, img_dir / f'img_{i:02d}')
            rows.append({'index': i, 'file': str(f.resolve()), 'size': size})
        media['images'] = [r['file'] for r in rows]
        info['image_files'] = rows
        if info['music'].get('audio_url'):
            raw = out / 'music_audio'
            download(info['music']['audio_url'], raw)
            audio_path, ameta = extract_audio(raw, out)
            media['audio'] = audio_path
            info['audio_source'] = '作品配乐/原声'
            info['audio_stream'] = ameta

    audio_result = None
    if media['audio']:
        from listen import analyze
        try:
            audio_result = analyze(media['audio'], out / 'audio_analysis', audio_mode)
            info['audio_analysis'] = str((out / 'audio_analysis').resolve())
        except Exception as e:
            info['audio_analysis_error'] = f'{type(e).__name__}: {e}'

    limits = (['图文作品没有视频画面，只能读图片与配乐，不能推断运镜或运动。',
               '脚本不生成画面描述；需用 Read 查看原图后再描述画面。']
              if info['kind'] == 'note' else
              [f'抽帧间隔 {info["video"]["sampling_interval_seconds"]}s，是均匀概览而非逐帧检查，'
               f'不得用未出现于采样帧推出全片不存在。',
               '脚本不生成画面描述；需用 Read 查看联系图或原帧后再描述画面。'])
    limits += ['转写按 25 秒分块，时间戳是块区间而非强制对齐；块边缘可能断句，文字可能有错漏。',
               '声音标签为候选分类，分数非校准概率；配乐若为平台曲库音乐，转写通常为空，不代表没有声音。',
               '互动数等计数随抓取时刻变化，回答需注明抓取时间。']
    info.update({'status': 'evidence_ready', 'output': str(out), 'media': media,
                 'speech_chunks': len(audio_result['speech']) if audio_result else 0,
                 'interpretation_status': 'not_yet_reviewed_by_agent',
                 'limitations': limits})
    save_json(out / 'evidence.json', info)

    lines = ['# 抖音作品读取证据', '',
             f"- 链接：{info['source_url']}",
             f"- 落点：{info['resolved_url']}",
             f"- 类型：{'图文（%d 张图片 + 配乐）' % info['image_count'] if info['kind'] == 'note' else '视频'}",
             f"- 作者：{info['author'] or '未返回'}",
             f"- 发布时间：{info['create_time'] or '未返回'}",
             f"- 文案：{info['desc'] or '未返回'}",
             f"- 话题：{'、'.join(info['hashtags']) or '无'}",
             f"- 互动：{json.dumps(info['statistics'], ensure_ascii=False)}",
             f"- 数据通道：{info['extraction']}",
             '', '## 素材落盘']
    if info['kind'] == 'video':
        v = info['video']
        lines.append(f"- 视频 {v['width']}x{v['height']}，{round(v['duration_seconds'], 2)}s，抽帧 {len(info['frames'])} 张（间隔 {v['sampling_interval_seconds']}s）")
        lines += [f"- 联系图：{p}" for p in info['contact_sheets']]
    else:
        lines += [f"- 图{r['index']:02d}：{r['file']}（{r['size'][0]}x{r['size'][1]}）" for r in info['image_files']]
        lines.append(f"- 配乐：{info['music']['title']} / {info['music']['author']}")
    lines += ['', '## 声音']
    if audio_result:
        lines.append(f"- 转写片段 {len(audio_result['speech'])} 条，详见 audio_analysis/")
        lines += [f"- [{x['start']:.2f}–{x['end']:.2f}s] {x['text']}" for x in audio_result['speech']] or ['- 未检出可可靠转写的人声']
    elif info.get('audio_analysis_error'):
        lines.append(f"- 音频分析失败：{info['audio_analysis_error']}")
    else:
        lines.append('- 无可用音轨')
    lines += ['', '## 边界'] + ['- ' + x for x in info['limitations']]
    (out / '证据.md').write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')
    return info


def doctor():
    import importlib.util
    deps = {m: importlib.util.find_spec(m) is not None
            for m in ('av', 'numpy', 'scipy', 'sherpa_onnx', 'PIL', 'playwright')}
    models = AUDIO_SKILL / '.runtime' / 'models'
    speech = models / 'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17'
    events = models / 'sherpa-onnx-zipformer-small-audio-tagging-2024-04-15'
    files = {p.name: (p / 'model.int8.onnx').is_file() for p in (speech, events)}
    chrome = any(Path(p).is_file() for p in (
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    ))
    return {'ready': all(deps.values()) and all(files.values()) and chrome,
            'dependencies': deps, 'audio_models': files, 'system_chrome': chrome,
            'audio_skill': str(AUDIO_SKILL)}


def main():
    ap = argparse.ArgumentParser(description='抖音作品程序化读取（无可见浏览器）')
    ap.add_argument('--link', help='抖音分享文本或链接')
    ap.add_argument('--aweme-id', help='已知作品 ID')
    ap.add_argument('--kind', choices=['video', 'note'], help='配合 --aweme-id 使用')
    ap.add_argument('--output', help='证据输出目录（必须为空或不存在）')
    ap.add_argument('--resolve-only', action='store_true')
    ap.add_argument('--item-only', action='store_true', help='只取作品结构化数据，不下载媒体')
    ap.add_argument('--doctor', action='store_true')
    ap.add_argument('--interval', type=float, default=2.0)
    ap.add_argument('--max-frames', type=int, default=60)
    ap.add_argument('--audio-mode', choices=['both', 'speech', 'sounds'], default='both')
    ap.add_argument('--debug', action='store_true')
    a = ap.parse_args()
    try:
        if a.doctor:
            r = doctor()
            print(json.dumps(r, ensure_ascii=False))
            return 0 if r['ready'] else 2
        if not 0.2 <= a.interval <= 60 or not 1 <= a.max_frames <= 180:
            raise ReaderError('INVALID_SAMPLING_OPTIONS')
        if a.aweme_id:
            if not a.kind:
                ap.error('--aweme-id 需要同时给出 --kind')
            resolved = {'source_url': f'https://www.douyin.com/{a.kind}/{a.aweme_id}',
                        'resolved_url': f'https://www.douyin.com/{a.kind}/{a.aweme_id}',
                        'kind': a.kind, 'aweme_id': a.aweme_id}
            if a.item_only:
                item, extraction = acquire(a.kind, a.aweme_id, a.debug)
                info = normalize(item, resolved, extraction)
                print(json.dumps(info, ensure_ascii=False)[:2000])
                return 0
            if not a.output:
                ap.error('--output 必填（或改用 --item-only）')
            item, extraction = acquire(a.kind, a.aweme_id, a.debug)
            info = normalize(item, resolved, extraction)
            out = prepare_output(a.output)
            save_json(out / 'item.json', info)
            print(json.dumps({'status': 'resolved', 'kind': info['kind'], 'author': info['author'],
                              'image_count': info['image_count'], 'has_video': bool(info['video_url']),
                              'extraction': extraction, 'item': str((out / 'item.json'))}, ensure_ascii=False))
            return 0
        if not a.link:
            ap.error('需要 --link 或（--aweme-id + --kind + --output）')
        if a.resolve_only:
            print(json.dumps(resolve_link(a.link), ensure_ascii=False))
            return 0
        if not a.output:
            ap.error('--output 必填')
        info = run(a.link, a.output, a.interval, a.max_frames, a.audio_mode, a.debug)
        print(json.dumps({'status': info['status'], 'kind': info['kind'],
                          'images': info['image_count'], 'frames': len(info.get('frames', [])),
                          'speech_chunks': info['speech_chunks'],
                          'evidence': str(Path(info['output']) / 'evidence.json'),
                          'report': str(Path(info['output']) / '证据.md')}, ensure_ascii=False))
        return 0
    except ReaderError as e:
        print(json.dumps({'status': 'error', 'error_type': 'ReaderError', 'message': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as e:
        print(json.dumps({'status': 'error', 'error_type': type(e).__name__, 'message': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
