"""音乐下载器 Web 界面 - 用于 NAS 远程部署"""
import os
import re
import requests
from flask import Flask, render_template_string, request, jsonify
from musicdl import musicdl as MusicDL

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

download_dir = os.environ.get('DOWNLOAD_DIR', '/downloads')
os.makedirs(download_dir, exist_ok=True)

_song_cache = {}


def build_client(sources=None):
    if sources is None:
        sources = ['NeteaseMusicClient', 'QQMusicClient', 'KugouMusicClient', 'KuwoMusicClient', 'MiguMusicClient']
    cfg = {s: {"search_size_per_source": 20, "search_size_per_page": 20, "strict_limit_search_size_per_page": False} for s in sources}
    return MusicDL.MusicClient(music_sources=sources, init_music_clients_cfg=cfg)


INDEX_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>音乐下载器</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f5f5f5; padding: 16px; }
.container { max-width: 900px; margin: 0 auto; }
h1 { color: #333; margin-bottom: 16px; font-size: 22px; }
.card { background: #fff; border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.input-row { display: flex; gap: 8px; margin-bottom: 10px; }
.input-row input { flex: 1; padding: 10px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.input-row button { padding: 10px 16px; background: #1890ff; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; white-space: nowrap; }
.tabs { display: flex; gap: 4px; margin-bottom: 12px; }
.tab { padding: 8px 16px; background: #f0f0f0; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; }
.tab.active { background: #1890ff; color: #fff; }
.song-item { display: flex; align-items: center; padding: 10px; border-bottom: 1px solid #f0f0f0; }
.song-item input[type="checkbox"] { margin-right: 10px; }
.song-name { flex: 1; font-size: 14px; }
.song-artist { color: #999; font-size: 12px; margin-right: 12px; }
.btn { padding: 8px 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-success { background: #52c41a; color: #fff; }
.status { margin-top: 10px; padding: 10px; background: #f9f9f9; border-radius: 4px; font-size: 13px; max-height: 200px; overflow-y: auto; }
.empty { color: #999; padding: 20px; text-align: center; }
.folder-info { color: #1890ff; font-size: 12px; margin-top: 6px; }
</style>
</head>
<body>
<div class="container">
  <h1>🎵 音乐下载器</h1>
  <div class="card">
    <div class="tabs">
      <button class="tab active" id="tab-btn-search" onclick="switchTab('search')">🔍 搜索歌曲</button>
      <button class="tab" id="tab-btn-album" onclick="switchTab('album')">💿 专辑/歌手/歌单链接</button>
    </div>
    <div id="tab-search">
      <div class="input-row">
        <input type="text" id="search_kw" placeholder="输入歌曲名或歌手名..." onkeypress="if(event.key==='Enter')doSearch()">
        <button onclick="doSearch()">搜索</button>
      </div>
    </div>
    <div id="tab-album" style="display:none">
      <div class="input-row">
        <input type="text" id="link_url" placeholder="粘贴网易云/咪咕 专辑/歌手/歌单链接...">
        <button onclick="doLink()">解析</button>
      </div>
    </div>
  </div>
  <div class="card">
    <b>音源</b>
    <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:12px;font-size:13px">
      <label><input type="checkbox" id="src_netease" checked> 网易云</label>
      <label><input type="checkbox" id="src_qq" checked> QQ音乐</label>
      <label><input type="checkbox" id="src_kugou"> 酷狗</label>
      <label><input type="checkbox" id="src_kuwo"> 酷我</label>
      <label><input type="checkbox" id="src_migu" checked> 咪咕</label>
    </div>
    <div class="folder-info">保存目录: /volume2/downloads2/music<span id="folder_label"></span></div>
  </div>
  <div class="card">
    <div class="input-row" style="margin-bottom:0">
      <button class="btn" onclick="selectAll(true)">全选</button>
      <button class="btn" onclick="selectAll(false)">取消</button>
      <button class="btn btn-success" onclick="doDownload()" style="margin-left:auto">📥 下载选中</button>
    </div>
    <div id="songList"><p class="empty">输入关键词搜索音乐</p></div>
  </div>
  <div class="card"><b>状态</b><div class="status" id="status">就绪</div></div>
</div>
<script>
let songs = [], currentFolder = '', songKeys = [];
function switchTab(t){document.getElementById('tab-btn-search').classList.toggle('active',t==='search');document.getElementById('tab-btn-album').classList.toggle('active',t==='album');document.getElementById('tab-search').style.display=t==='search'?'block':'none';document.getElementById('tab-album').style.display=t==='album'?'block':'none';}
function log(m){document.getElementById('status').innerHTML=m+'<br>'+document.getElementById('status').innerHTML;}
function doSearch(){const kw=document.getElementById('search_kw').value.trim();if(!kw)return;currentFolder='';document.getElementById('folder_label').textContent='';log('搜索: '+kw);fetch('/api/search?kw='+encodeURIComponent(kw)).then(r=>r.json()).then(d=>{songs=d.songs||[];songKeys=d.keys||[];render();log('找到 '+songs.length+' 首');});}
function doLink(){const url=document.getElementById('link_url').value.trim();if(!url)return;
  // 根据URL自动勾选对应音源
  const all=['src_netease','src_qq','src_kugou','src_kuwo','src_migu'];
  let active='';
  if(url.includes('163.com')) active='src_netease';
  else if(url.includes('y.qq.com')) active='src_qq';
  else if(url.includes('kugou.com')) active='src_kugou';
  else if(url.includes('kuwo.cn')) active='src_kuwo';
  else if(url.includes('migu.cn')) active='src_migu';
  all.forEach(id=>{document.getElementById(id).checked=(id===active);});
  log('解析链接中...');fetch('/api/link?url='+encodeURIComponent(url)).then(r=>r.json()).then(d=>{songs=d.songs||[];songKeys=d.keys||[];currentFolder=d.folder||'';document.getElementById('folder_label').textContent=currentFolder?' → '+currentFolder:'';render();log('找到 '+songs.length+' 首'+(currentFolder?'，保存到: '+currentFolder:''));});}
function render(){const el=document.getElementById('songList');if(!songs.length){el.innerHTML='<p class="empty">无结果</p>';return;}el.innerHTML=songs.map((s,i)=>`<div class="song-item"><input type="checkbox" id="ck${i}"><span class="song-name">${s.song_name||''}</span><span class="song-artist">${s.singers||''}</span></div>`).join('');}
function selectAll(v){songs.forEach((_,i)=>document.getElementById('ck'+i).checked=v);}
function doDownload(){const selIdx=songs.map((_,i)=>i).filter(i=>document.getElementById('ck'+i).checked);if(!selIdx.length){alert('请先勾选歌曲');return;}const selKeys=selIdx.map(i=>songKeys[i]).filter(k=>k);log('开始下载 '+selKeys.length+' 首...'+(currentFolder?' → '+currentFolder:''));fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keys:selKeys,folder:currentFolder})}).then(r=>r.json()).then(d=>log(d.msg||'完成'));}
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)


@app.route('/api/search')
def api_search():
    kw = request.args.get('kw', '')
    if not kw: return jsonify({'songs': [], 'keys': []})
    try:
        client = build_client()
        results = client.search(keyword=kw)
        songs, keys, seen = [], [], set()
        for src, ss in results.items():
            for si in ss:
                nid = getattr(si, 'identifier', '')
                sk = f"{src}_{nid}"
                if sk in seen: continue
                seen.add(sk)
                _song_cache[sk] = si
                songs.append({'song_name': getattr(si, 'song_name', ''), 'singers': getattr(si, 'singers', '')})
                keys.append(sk)
                if len(songs) >= 50: break
            if len(songs) >= 50: break
        return jsonify({'songs': songs, 'keys': keys})
    except Exception as e:
        return jsonify({'songs': [], 'keys': [], 'error': str(e)})


@app.route('/api/link')
def api_link():
    url = request.args.get('url', '')
    if not url: return jsonify({'songs': [], 'keys': []})
    try:
        # 网易云歌单
        m = re.search(r'music\.163\.com/#/playlist\?id=(\d+)', url)
        if m: return parse_netease_playlist(m.group(1))
        # 网易云歌手
        m = re.search(r'music\.163\.com/#/artist\?id=(\d+)', url)
        if m: return parse_netease_artist(m.group(1))
        # 网易云专辑
        m = re.search(r'music\.163\.com/#/album\?id=(\d+)', url)
        if m: return parse_netease_album(m.group(1))
        # 网易云单曲
        m = re.search(r'music\.163\.com/#/song\?id=(\d+)', url)
        if m: return parse_netease_song(m.group(1))
        # QQ音乐歌单
        m = re.search(r'y\.qq\.com/n/ryqq[^/]*/playlist/(\d+)', url)
        if m: return parse_qq_playlist(m.group(1))
        # QQ音乐专辑
        m = re.search(r'y\.qq\.com/n/ryqq[^/]*/albumDetail/([A-Za-z0-9]+)', url)
        if m: return parse_qq_album(m.group(1))
        # QQ音乐单曲
        m = re.search(r'y\.qq\.com/n/ryqq[^/]*/songDetail/([A-Za-z0-9]+)', url)
        if m: return parse_qq_song(m.group(1))
        m = re.search(r'y\.qq\.com/n/ryqq[^/]*/song/([A-Za-z0-9]+)', url)
        if m: return parse_qq_song(m.group(1))
        # QQ音乐歌手
        m = re.search(r'y\.qq\.com/n/ryqq[^/]*/singerDetail[?/]([A-Za-z0-9]+)', url)
        if m: return parse_qq_singer(m.group(1))
        m = re.search(r'y\.qq\.com/n/ryqq[^/]*/singer/([A-Za-z0-9]+)', url)
        if m: return parse_qq_singer(m.group(1))
        # 酷我歌单
        m = re.search(r'kuwo\.cn/playlist_detail/(\d+)', url)
        if m: return parse_kuwo_playlist(m.group(1))
        # 酷我单曲
        m = re.search(r'kuwo\.cn/(?:song|play)_detail/(\d+)', url)
        if m: return parse_kuwo_song(m.group(1))
        # 酷我歌手
        m = re.search(r'kuwo\.cn/singer_detail/(\d+)', url)
        if m: return parse_kuwo_singer(m.group(1))
        # 酷我专辑
        m = re.search(r'kuwo\.cn/album_detail/(\d+)', url)
        if m: return parse_kuwo_album(m.group(1))
        # 酷狗歌单
        m = re.search(r'kugou\.com/yy/special/single/(\d+)', url)
        if m: return parse_kugou_playlist(m.group(1))
        # 酷狗单曲
        m = re.search(r'kugou\.com/song/([A-Za-z0-9]+)', url)
        if m: return parse_kugou_song(m.group(1))
        # 酷狗歌手
        m = re.search(r'kugou\.com/singer/(\d+)', url)
        if m: return parse_kugou_singer(m.group(1))
        # 酷狗专辑
        m = re.search(r'kugou\.com/album/(\d+)', url)
        if m: return parse_kugou_album(m.group(1))
        # 咪咕单曲
        m = re.search(r'(?:songDetail|play)[?&]cId=(\d+)', url)
        if m: return parse_migu_song(m.group(1))
        # 咪咕专辑
        m = re.search(r'albumId=(\d+)', url)
        if m: return parse_migu_album(m.group(1))
        # 咪咕歌手
        m = re.search(r'singerDetail\?id=(\d+)', url)
        if m: return parse_migu_singer(m.group(1))
        # 咪咕歌单
        m = re.search(r'playListDetail[?&]listId=(\d+)', url)
        if m: return parse_migu_playlist(m.group(1))
        m = re.search(r'playlistDetail[?&]playlistId=(\d+)', url)
        if m: return parse_migu_playlist(m.group(1))
        return jsonify({'songs': [], 'keys': [], 'error': '不支持的链接格式'})
    except Exception as e:
        return jsonify({'songs': [], 'keys': [], 'error': str(e)})


def parse_netease_playlist(playlist_id):
    """解析网易云歌单：快速返回歌曲列表，下载时直接用ID解析"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://music.163.com/"}
    r = requests.get(f"https://music.163.com/api/playlist/detail?id={playlist_id}", headers=headers, timeout=15)
    d = r.json()
    pl = d.get("result", {})
    playlist_name = pl.get("name", f"playlist-{playlist_id}")
    tracks = pl.get("tracks", [])
    if not tracks:
        return jsonify({'songs': [], 'keys': [], 'folder': playlist_name, 'error': '歌单为空'})

    songs_out, keys = [], []
    for track in tracks:
        name = track.get("name", "")
        artists = " ".join([a.get("name", "") for a in track.get("artists", [])])
        track_id = str(track.get("id", ""))
        key = f"netease_pid_{track_id}"
        # 缓存歌曲ID，下载时直接解析
        _song_cache[key] = {'song_id': track_id, 'pending': True, 'name': name, 'artists': artists}
        songs_out.append({'song_name': name, 'singers': artists})
        keys.append(key)

    return jsonify({'songs': songs_out, 'keys': keys, 'folder': playlist_name})


def parse_netease_artist(artist_id):
    """解析网易云歌手：获取歌手名后搜索"""
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
    r = requests.get(f"https://music.163.com/api/artist/{artist_id}", headers=headers, timeout=15)
    d = r.json()
    artist_name = d.get("artist", {}).get("name", f"artist-{artist_id}")
    ne = build_client(['NeteaseMusicClient']).music_clients['NeteaseMusicClient']
    results = ne.search(keyword=artist_name)
    songs_out, keys, seen = [], [], set()
    for si in results:
        nid = getattr(si, 'identifier', '')
        if nid in seen: continue
        seen.add(nid)
        key = f"netease_{nid}"
        _song_cache[key] = si
        songs_out.append({'song_name': si.song_name, 'singers': si.singers})
        keys.append(key)
    return jsonify({'songs': songs_out, 'keys': keys, 'folder': artist_name})


def parse_netease_album(album_id):
    """解析网易云专辑"""
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
    try:
        r = requests.get(f"https://music.163.com/api/album/{album_id}", headers=headers, timeout=15)
        d = r.json()
        album_name = d.get("album", {}).get("name", f"album-{album_id}")
    except:
        album_name = f"album-{album_id}"
    ne = build_client(['NeteaseMusicClient']).music_clients['NeteaseMusicClient']
    results = ne.search(keyword=album_name)
    songs_out, keys, seen = [], [], set()
    for si in results:
        nid = getattr(si, 'identifier', '')
        if nid in seen: continue
        seen.add(nid)
        key = f"netease_{nid}"
        _song_cache[key] = si
        songs_out.append({'song_name': si.song_name, 'singers': si.singers})
        keys.append(key)
    return jsonify({'songs': songs_out, 'keys': keys, 'folder': album_name})


def parse_qq_playlist(playlist_id):
    """解析QQ音乐歌单：快速返回歌曲列表，下载时用songmid解析"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://y.qq.com/"}
    r = requests.get(f"https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg?type=1&json=1&utf8=1&onlysong=0&disstid={playlist_id}&format=json", headers=headers, timeout=15)
    d = r.json()
    cdlist = d.get("cdlist", [])
    if not cdlist:
        return jsonify({'songs': [], 'keys': [], 'error': '歌单为空'})
    cd = cdlist[0]
    playlist_name = cd.get("dissname", f"playlist-{playlist_id}")
    tracks = cd.get("songlist", [])

    seen = set()
    songs_out, keys = [], []
    for track in tracks:
        songmid = track.get("songmid", "")
        if not songmid or songmid in seen: continue
        seen.add(songmid)
        name = track.get("songname", "")
        singers = " ".join([s.get("name", "") for s in track.get("singer", [])])
        key = f"qq_pid_{songmid}"
        _song_cache[key] = {'songmid': songmid, 'pending': True, 'source': 'QQMusicClient'}
        songs_out.append({'song_name': name, 'singers': singers})
        keys.append(key)

    return jsonify({'songs': songs_out, 'keys': keys, 'folder': playlist_name})


def parse_qq_album(albummid):
    """解析QQ音乐专辑：快速返回歌曲列表，下载时用songmid解析"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://y.qq.com/",
        "Content-Type": "application/json"
    }
    data = {
        "comm": {"format": "json", "ct": 24, "cv": 0},
        "albumSongList": {
            "module": "music.musichallAlbum.AlbumSongList",
            "method": "GetAlbumSongList",
            "param": {"albummid": albummid, "begin": 0, "num": 100}
        }
    }
    r = requests.post("https://u.y.qq.com/cgi-bin/musicu.fcg", json=data, headers=headers, timeout=15)
    d = r.json()
    songlist = d.get('albumSongList', {}).get('data', {}).get('songList', [])
    if not songlist:
        return jsonify({'songs': [], 'keys': [], 'error': '专辑为空'})

    playlist_name = albummid
    songs_out, keys, seen = [], [], set()
    for item in songlist:
        si = item.get('songInfo', {})
        songmid = si.get('mid', '')
        if not songmid or songmid in seen: continue
        seen.add(songmid)
        name = si.get('name', '')
        singers = " ".join([s.get('name', '') for s in si.get('singer', [])])
        if playlist_name == albummid:
            playlist_name = si.get('album', {}).get('name', f'album-{albummid}')
        key = f"qq_album_{songmid}"
        _song_cache[key] = {'songmid': songmid, 'pending': True, 'source': 'QQMusicClient'}
        songs_out.append({'song_name': name, 'singers': singers})
        keys.append(key)

    return jsonify({'songs': songs_out, 'keys': keys, 'folder': playlist_name})


def parse_netease_song(song_id):
    """解析网易云单曲"""
    ne = build_client(['NeteaseMusicClient']).music_clients['NeteaseMusicClient']
    si = ne._parsewiththirdpartapis(search_result={'id': int(song_id)}, request_overrides={})
    if not si.with_valid_download_url:
        return jsonify({'songs': [], 'keys': [], 'error': '无法获取该歌曲下载链接'})
    key = f"netease_{getattr(si, 'identifier', song_id)}"
    _song_cache[key] = si
    return jsonify({'songs': [{'song_name': si.song_name, 'singers': si.singers}], 'keys': [key], 'folder': si.singers or '单曲'})


def parse_qq_song(songmid):
    """解析QQ音乐单曲"""
    qq = build_client(['QQMusicClient']).music_clients['QQMusicClient']
    si = qq._parsewiththirdpartapis(search_result={'songmid': songmid}, request_overrides={})
    if not si.with_valid_download_url:
        return jsonify({'songs': [], 'keys': [], 'error': '无法获取该歌曲下载链接'})
    key = f"qq_{getattr(si, 'identifier', songmid)}"
    _song_cache[key] = si
    return jsonify({'songs': [{'song_name': si.song_name, 'singers': si.singers}], 'keys': [key], 'folder': si.singers or '单曲'})


def parse_kuwo_song(rid):
    """解析酷我单曲"""
    kw = build_client(['KuwoMusicClient']).music_clients['KuwoMusicClient']
    si = kw._parsewiththirdpartapis(search_result={'rid': int(rid), 'musicrid': f'MUSIC_{rid}'}, request_overrides={})
    if not si.with_valid_download_url:
        return jsonify({'songs': [], 'keys': [], 'error': '无法获取该歌曲下载链接'})
    if not si.song_name or si.song_name == 'NULL':
        si.song_name = f'歌曲{rid}'
    if not si.singers or si.singers == 'NULL':
        si.singers = ''
    key = f"kuwo_{rid}"
    _song_cache[key] = si
    return jsonify({'songs': [{'song_name': si.song_name, 'singers': si.singers}], 'keys': [key], 'folder': si.singers or '单曲'})


def parse_kugou_song(file_hash):
    """解析酷狗单曲"""
    kg = build_client(['KugouMusicClient']).music_clients['KugouMusicClient']
    si = kg._parsewiththirdpartapis(search_result={'hash': file_hash}, request_overrides={})
    if not si.with_valid_download_url:
        return jsonify({'songs': [], 'keys': [], 'error': '无法获取该歌曲下载链接'})
    key = f"kugou_{getattr(si, 'identifier', file_hash)}"
    _song_cache[key] = si
    return jsonify({'songs': [{'song_name': si.song_name, 'singers': si.singers}], 'keys': [key], 'folder': si.singers or '单曲'})


def parse_migu_song(content_id):
    """解析咪咕单曲"""
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.migu.cn/"}
    r = requests.get(f"https://app.c.nf.migu.cn/MIGUM3.0/v1.0/content/resourceinfo.do?resourceId={content_id}&resourceType=2", headers=headers, timeout=15)
    rc = r.json().get('resource', [])
    if not rc:
        return jsonify({'songs': [], 'keys': [], 'error': '无法获取该歌曲信息'})
    raw = rc[0]
    if raw.get('singer') and not raw.get('singerList'):
        raw['singerList'] = [{'name': raw['singer']}]
    migu = build_client(['MiguMusicClient']).music_clients['MiguMusicClient']
    si = migu._parsewithofficialapiv1(search_result=raw, lossless_quality_is_sufficient=False)
    if not si.with_valid_download_url:
        return jsonify({'songs': [], 'keys': [], 'error': '无法获取该歌曲下载链接'})
    key = f"migu_{getattr(si, 'identifier', content_id)}"
    _song_cache[key] = si
    return jsonify({'songs': [{'song_name': si.song_name, 'singers': si.singers}], 'keys': [key], 'folder': si.singers or '单曲'})


def parse_qq_singer(singermid):
    """解析QQ音乐歌手：从页面获取歌手名后搜索"""
    try:
        r = requests.get(f"https://y.qq.com/n/ryqq/singer/{singermid}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=10)
        m = re.search(r'<meta\s+name="keywords"\s+content="([^",]+)', r.text)
        singer_name = m.group(1).strip() if m else f'QQ歌手-{singermid}'
    except:
        singer_name = f'QQ歌手-{singermid}'
    qq = build_client(['QQMusicClient']).music_clients['QQMusicClient']
    results = qq.search(keyword=singer_name)
    songs_out, keys, seen = [], [], set()
    for si in results:
        nid = getattr(si, 'identifier', '')
        if nid in seen: continue
        seen.add(nid)
        key = f"qq_{nid}"
        _song_cache[key] = si
        songs_out.append({'song_name': si.song_name, 'singers': si.singers})
        keys.append(key)
    return jsonify({'songs': songs_out, 'keys': keys, 'folder': singer_name})


def parse_kuwo_playlist(pid):
    """解析酷我歌单：快速返回歌曲列表，下载时用rid解析"""
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)"}
    all_tracks, page, total = [], 1, 0
    while True:
        r = requests.get(f"https://m.kuwo.cn/newh5app/wapi/api/www/playlist/playListInfo?pid={pid}&pn={page}&rn=100", headers=headers, timeout=15)
        d = r.json()
        if d.get('code') not in (0, 200): break
        data = d.get('data', {})
        if page == 1:
            playlist_name = data.get('name', f'playlist-{pid}')
            total = int(data.get('total', 0))
        tracks = data.get('musicList', [])
        if not tracks: break
        all_tracks.extend(tracks)
        if len(all_tracks) >= total or len(tracks) < 100: break
        page += 1

    songs_out, keys = [], []
    for t in all_tracks:
        rid = t.get('rid', 0)
        if not rid: continue
        name = t.get('name', '')
        artist = t.get('artist', '')
        key = f"kuwo_pid_{rid}"
        _song_cache[key] = {'rid': rid, 'pending': True, 'source': 'KuwoMusicClient'}
        songs_out.append({'song_name': name, 'singers': artist})
        keys.append(key)
    return jsonify({'songs': songs_out, 'keys': keys, 'folder': playlist_name})


def parse_kuwo_singer(singer_id):
    """解析酷我歌手：获取歌手名后搜索"""
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)"}
    try:
        r = requests.get(f"https://m.kuwo.cn/newh5app/wapi/api/www/artist/info?artistid={singer_id}", headers=headers, timeout=10)
        singer_name = r.json().get('data', {}).get('name', f'artist-{singer_id}')
    except:
        singer_name = f'artist-{singer_id}'
    kw = build_client(['KuwoMusicClient']).music_clients['KuwoMusicClient']
    results = kw.search(keyword=singer_name)
    songs_out, keys, seen = [], [], set()
    for si in results:
        nid = getattr(si, 'identifier', '')
        if nid in seen: continue
        seen.add(nid)
        key = f"kuwo_{nid}"
        _song_cache[key] = si
        songs_out.append({'song_name': si.song_name, 'singers': si.singers})
        keys.append(key)
    return jsonify({'songs': songs_out, 'keys': keys, 'folder': singer_name})


def parse_kuwo_album(album_id):
    """解析酷我专辑：获取专辑名后搜索"""
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)"}
    try:
        r = requests.get(f"https://m.kuwo.cn/newh5app/wapi/api/www/album/info?albumid={album_id}", headers=headers, timeout=10)
        album_name = r.json().get('data', {}).get('album', {}).get('name', f'album-{album_id}')
    except:
        album_name = f'album-{album_id}'
    kw = build_client(['KuwoMusicClient']).music_clients['KuwoMusicClient']
    results = kw.search(keyword=album_name)
    songs_out, keys, seen = [], [], set()
    for si in results:
        nid = getattr(si, 'identifier', '')
        if nid in seen: continue
        seen.add(nid)
        key = f"kuwo_{nid}"
        _song_cache[key] = si
        songs_out.append({'song_name': si.song_name, 'singers': si.singers})
        keys.append(key)
    return jsonify({'songs': songs_out, 'keys': keys, 'folder': album_name})


def parse_kugou_playlist(special_id):
    """解析酷狗歌单：快速返回歌曲列表，下载时用hash解析"""
    import hashlib, time as _time
    headers = {
        'User-Agent': 'Android9-AndroidPhone-11239-18-0-playlist-wifi',
        'Host': 'gatewayretry.kugou.com',
        'x-router': 'pubsongscdn.kugou.com',
        'mid': '239526275778893399526700786998289824956',
        'dfid': '-',
        'clienttime': str(int(_time.time()))
    }
    all_tracks, page, total = [], 1, 0
    while True:
        api_url = f"http://gatewayretry.kugou.com/v2/get_other_list_file?specialid={special_id}&need_sort=1&module=CloudMusic&clientver=11239&pagesize=300&specalidpgc={special_id}&userid=0&page={page}&type=0&area_code=1&appid=1005"
        query = api_url.split("?", 1)[1]
        sorted_query = "&".join(sorted(query.split("&")))
        raw = "OIlwieks28dk2k092lksi2UIkp" + sorted_query + "OIlwieks28dk2k092lksi2UIkp"
        signature = hashlib.md5(raw.encode()).hexdigest()
        try:
            r = requests.get(api_url + '&signature=' + signature, headers=headers, timeout=15)
            d = r.json()
        except:
            break
        info = d.get('data', {}).get('info', [])
        if not info: break
        if page == 1:
            total = int(d.get('data', {}).get('count', 0) or len(info))
        all_tracks.extend(info)
        if len(all_tracks) >= total or len(info) < 300: break
        page += 1

    playlist_name = f"playlist-{special_id}"
    songs_out, keys, seen = [], [], set()
    for t in all_tracks:
        h = t.get('hash', '')
        if not h or h in seen: continue
        seen.add(h)
        name = t.get('songname', '')
        singer = t.get('singerName', '')
        key = f"kugou_pid_{h}"
        _song_cache[key] = {'file_hash': h, 'pending': True, 'source': 'KugouMusicClient'}
        songs_out.append({'song_name': name, 'singers': singer})
        keys.append(key)
    return jsonify({'songs': songs_out, 'keys': keys, 'folder': playlist_name})


def parse_kugou_singer(singer_id):
    """解析酷狗歌手：获取歌手名后搜索"""
    try:
        r = requests.get(f"https://www.kugou.com/yy/singer/home/{singer_id}.html",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        m = re.search(r'<title>([^-<]+)-', r.text)
        singer_name = m.group(1).strip() if m else f'artist-{singer_id}'
    except:
        singer_name = f'artist-{singer_id}'
    kg = build_client(['KugouMusicClient']).music_clients['KugouMusicClient']
    results = kg.search(keyword=singer_name)
    songs_out, keys, seen = [], [], set()
    for si in results:
        nid = getattr(si, 'identifier', '')
        if nid in seen: continue
        seen.add(nid)
        key = f"kugou_{nid}"
        _song_cache[key] = si
        songs_out.append({'song_name': si.song_name, 'singers': si.singers})
        keys.append(key)
    return jsonify({'songs': songs_out, 'keys': keys, 'folder': singer_name})


def parse_kugou_album(album_id):
    """解析酷狗专辑：获取专辑名后搜索"""
    try:
        r = requests.get(f"https://www.kugou.com/yy/album/single/{album_id}.html",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        m = re.search(r'<title>([^-<]+)-', r.text)
        album_name = m.group(1).strip() if m else f'album-{album_id}'
    except:
        album_name = f'album-{album_id}'
    kg = build_client(['KugouMusicClient']).music_clients['KugouMusicClient']
    results = kg.search(keyword=album_name)
    songs_out, keys, seen = [], [], set()
    for si in results:
        nid = getattr(si, 'identifier', '')
        if nid in seen: continue
        seen.add(nid)
        key = f"kugou_{nid}"
        _song_cache[key] = si
        songs_out.append({'song_name': si.song_name, 'singers': si.singers})
        keys.append(key)
    return jsonify({'songs': songs_out, 'keys': keys, 'folder': album_name})


def parse_migu_playlist(playlist_id):
    """解析咪咕歌单"""
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.migu.cn/"}
    try:
        r_info = requests.get(f"https://app.c.nf.migu.cn/MIGUM3.0/resource/playlist/v2.0?playlistId={playlist_id}", headers=headers, timeout=15)
        playlist_name = r_info.json().get("data", {}).get("title", f"playlist-{playlist_id}")
    except:
        playlist_name = f"playlist-{playlist_id}"
    all_songs_raw, page = [], 1
    while True:
        r = requests.get(f"https://app.c.nf.migu.cn/MIGUM3.0/resource/playlist/song/v2.0?pageNo={page}&pageSize=50&playlistId={playlist_id}", headers=headers, timeout=15)
        d = r.json()
        if d.get("code") != "000000": break
        ss = d.get("data", {}).get("songList", [])
        total = int(d.get("data", {}).get("totalCount", 0))
        all_songs_raw.extend(ss)
        if len(all_songs_raw) >= total or not ss: break
        page += 1
    migu = build_client(['MiguMusicClient']).music_clients['MiguMusicClient']
    songs, keys = [], []
    for raw in all_songs_raw:
        try:
            singer_name_raw = raw.get('singer', '')
            if isinstance(singer_name_raw, str) and singer_name_raw:
                raw['singerList'] = [{'name': singer_name_raw}]
            si = migu._parsewithofficialapiv1(search_result=raw, lossless_quality_is_sufficient=False)
            if si.with_valid_download_url:
                key = f"migu_{getattr(si, 'identifier', '')}"
                _song_cache[key] = si
                songs.append({'song_name': si.song_name, 'singers': si.singers})
                keys.append(key)
        except:
            pass
    return jsonify({'songs': songs, 'keys': keys, 'folder': playlist_name})


def parse_migu_album(album_id):
    """解析咪咕专辑"""
    headers = {"User-Agent": "Mozilla/5.0"}
    r_info = requests.get(f"https://app.c.nf.migu.cn/MIGUM3.0/resource/album/v2.0?albumId={album_id}", headers=headers, timeout=15)
    album_name = r_info.json().get("data", {}).get("title", f"album-{album_id}")
    all_songs_raw = []
    page = 1
    while True:
        r = requests.get(f"https://app.c.nf.migu.cn/MIGUM3.0/resource/album/song/v2.0?pageNo={page}&pageSize=50&albumId={album_id}", headers=headers, timeout=15)
        d = r.json()
        if d.get("code") != "000000": break
        ss = d.get("data", {}).get("songList", [])
        total = int(d.get("data", {}).get("totalCount", 0))
        all_songs_raw.extend(ss)
        if len(all_songs_raw) >= total or not ss: break
        page += 1
    migu = build_client(['MiguMusicClient']).music_clients['MiguMusicClient']
    songs, keys = [], []
    for raw in all_songs_raw:
        try:
            singer_name_raw = raw.get('singer', '')
            if isinstance(singer_name_raw, str) and singer_name_raw:
                raw['singerList'] = [{'name': singer_name_raw}]
            si = migu._parsewithofficialapiv1(search_result=raw, lossless_quality_is_sufficient=False)
            if si.with_valid_download_url:
                key = f"migu_{getattr(si, 'identifier', '')}"
                _song_cache[key] = si
                songs.append({'song_name': si.song_name, 'singers': si.singers})
                keys.append(key)
        except:
            pass
    return jsonify({'songs': songs, 'keys': keys, 'folder': album_name})


def parse_migu_singer(singer_id):
    """解析咪咕歌手"""
    headers = {"User-Agent": "Mozilla/5.0", "Origin": "https://h5.nf.migu.cn", "Referer": "https://h5.nf.migu.cn/"}
    all_songs_raw, singer_name, page, total = [], "", 1, 0
    while True:
        r = requests.get(f"https://c.musicapp.migu.cn/v1.0/content/singer_songs.do?singerId={singer_id}&pageNo={page}&pageSize=50&resourceType=2", headers=headers, timeout=15)
        d = r.json()
        if d.get("code") != "000000": break
        if page == 1:
            singer_name = d.get("singer", {}).get("singer", "") or d.get("singer", {}).get("name", "")
            total = int(d.get("songNum", 0))
        ss = d.get("songlist", [])
        if not ss: break
        all_songs_raw.extend(ss)
        if len(all_songs_raw) >= total or len(ss) < 50: break
        page += 1
    migu = build_client(['MiguMusicClient']).music_clients['MiguMusicClient']
    songs, keys = [], []
    for raw in all_songs_raw:
        try:
            singer_name_raw = raw.get('singer', '')
            if isinstance(singer_name_raw, str) and singer_name_raw:
                raw['singerList'] = [{'name': singer_name_raw}]
            si = migu._parsewithofficialapiv1(search_result=raw, lossless_quality_is_sufficient=False)
            if si.with_valid_download_url:
                if not si.singers or si.singers == 'NULL':
                    si.singers = singer_name
                key = f"migu_{getattr(si, 'identifier', '')}"
                _song_cache[key] = si
                songs.append({'song_name': si.song_name, 'singers': si.singers})
                keys.append(key)
        except:
            pass
    return jsonify({'songs': songs, 'keys': keys, 'folder': singer_name})


@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json()
    keys = data.get('keys', [])
    folder = data.get('folder', '')
    if not keys: return jsonify({'msg': '无歌曲'})
    try:
        save_dir = download_dir
        if folder:
            safe = re.sub(r'[\\/:*?"<>|]', '_', folder)
            save_dir = os.path.join(download_dir, safe)
        os.makedirs(save_dir, exist_ok=True)
        client = build_client()
        ne = client.music_clients.get('NeteaseMusicClient')
        count, failed = 0, 0
        for key in keys:
            cached = _song_cache.get(key)
            if not cached:
                failed += 1; continue
            # 处理待解析的歌曲（来自歌单，直接用ID解析）
            if isinstance(cached, dict) and cached.get('pending'):
                try:
                    src = cached.get('source', 'NeteaseMusicClient')
                    src_client = client.music_clients.get(src)
                    if 'song_id' in cached:
                        # 网易云：直接用歌曲ID解析
                        si = src_client._parsewiththirdpartapis(search_result={'id': int(cached['song_id'])})
                        if si.with_valid_download_url:
                            cached = si
                        else:
                            failed += 1; continue
                    elif 'songmid' in cached:
                        # QQ音乐：用songmid解析
                        si = src_client._parsewiththirdpartapis(search_result={'songmid': cached['songmid']})
                        if si.with_valid_download_url:
                            cached = si
                        else:
                            failed += 1; continue
                    elif 'file_hash' in cached:
                        # 酷狗：用hash解析
                        si = src_client._parsewiththirdpartapis(search_result={'hash': cached['file_hash']})
                        if si.with_valid_download_url:
                            cached = si
                        else:
                            failed += 1; continue
                    elif 'rid' in cached:
                        # 酷我：用rid解析
                        si = src_client._parsewiththirdpartapis(search_result={'rid': cached['rid'], 'musicrid': f"MUSIC_{cached['rid']}"})
                        if si.with_valid_download_url:
                            cached = si
                        else:
                            failed += 1; continue
                    elif 'search_keyword' in cached:
                        results = src_client.search(keyword=cached['search_keyword'])
                        if results:
                            cached = results[0]
                        else:
                            failed += 1; continue
                    else:
                        failed += 1; continue
                except:
                    failed += 1; continue
            si = cached
            try:
                si.work_dir = save_dir
                song_name = si.song_name or 'unknown'
                singers = si.singers or ''
                ext = (si.ext or 'mp3').removeprefix('.')
                safe_name = re.sub(r'[\\/:*?"<>|]', '_', f"{song_name} - {singers}")
                si._save_path = os.path.join(save_dir, f"{safe_name}.{ext}")
                src = si.source if hasattr(si, 'source') else 'MiguMusicClient'
                dl = client.music_clients.get(src, client)
                dl.download(song_infos=[si])
                # 保存同名歌词文件
                if getattr(si, 'lyric', None):
                    lrc_path = os.path.splitext(si._save_path)[0] + '.lrc'
                    try:
                        with open(lrc_path, 'w', encoding='utf-8') as lf:
                            lf.write(si.lyric)
                    except:
                        pass
                count += 1
            except:
                failed += 1
        msg = f'完成 {count}/{len(keys)} 首'
        if failed: msg += f'（{failed}失败）'
        return jsonify({'msg': msg + f' → {save_dir}'})
    except Exception as e:
        return jsonify({'msg': f'下载失败: {e}'})


if __name__ == '__main__':
    print(f'下载目录: {download_dir}')
    app.run(host='0.0.0.0', port=8080, debug=False)
