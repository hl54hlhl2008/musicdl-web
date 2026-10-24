# MusicDL Web

基于 [musicdl](https://github.com/CharlesPikachu/musicdl) 的 NAS 远程音乐下载工具。通过浏览器搜索歌曲或粘贴平台链接，批量下载到 NAS 指定目录，自动生成歌手/专辑/歌单文件夹，并附带同名歌词文件。

## 功能

- **五音源搜索**：网易云、QQ音乐、酷狗、酷我、咪咕，关键词搜索歌名或歌手
- **链接解析下载**（五平台单曲/歌单/歌手/专辑页）：
  - 网易云：单曲 / 歌手 / 专辑 / 歌单
  - QQ音乐：单曲 / 歌单 / 专辑 / 歌手
  - 酷狗：单曲 / 歌单 / 歌手 / 专辑
  - 酷我：单曲 / 歌单 / 歌手 / 专辑
  - 咪咕：单曲 / 歌单 / 专辑 / 歌手
- **自动音源识别**：粘贴链接解析时自动勾选对应平台音源，取消其他平台
- **智能目录**：解析歌手/专辑/歌单链接后，自动在下载目录下创建同名文件夹
- **歌词同步**：每首歌自动保存同名 `.lrc` 歌词文件
- **文件名规范**：`歌曲名 - 歌手名.扩展名`
- **Docker 部署**：适配群晖 Container Manager，一条命令启动

## 快速部署（群晖）

### 1. 上传文件

将 `web_app.py`、`Dockerfile`、`docker-compose.yml`、`requirements.txt` 放入同一文件夹，例如 `/volume1/docker/musicdl-web`。

### 2. Container Manager → 项目 → 新增

使用自带的 `docker-compose.yml`：

```yaml
services:
  musicdl-web:
    build: .
    container_name: musicdl-web
    ports:
      - "58092:8080"
    volumes:
      - /volume2/downloads2/music:/downloads
    environment:
      - TZ=Asia/Shanghai
    restart: unless-stopped
```

### 3. 访问

浏览器打开 `http://你的群晖IP:58092`

## 支持的链接格式

| 平台 | 类型 | 链接示例 |
|------|------|---------|
| 网易云 | 单曲 | `https://music.163.com/#/song?id=347230` |
| 网易云 | 歌手 | `https://music.163.com/#/artist?id=46487` |
| 网易云 | 歌单 | `https://music.163.com/#/playlist?id=46243538` |
| 网易云 | 专辑 | `https://music.163.com/#/album?id=xxxxx` |
| QQ音乐 | 单曲 | `https://y.qq.com/n/ryqq_v2/songDetail/001bcXOd2RQ8QF` |
| QQ音乐 | 歌单 | `https://y.qq.com/n/ryqq_v2/playlist/7693795600` |
| QQ音乐 | 专辑 | `https://y.qq.com/n/ryqq_v2/albumDetail/002if7UF4RpVpM` |
| QQ音乐 | 歌手 | `https://y.qq.com/n/ryqq/singer/0025NhlN2yWrP4` |
| 酷狗 | 单曲 | `https://www.kugou.com/song/688857974673645CE89EDA26A36DB19D.html` |
| 酷狗 | 歌单 | `https://www.kugou.com/yy/special/single/12345.html` |
| 酷狗 | 歌手 | `https://www.kugou.com/singer/12345` |
| 酷狗 | 专辑 | `https://www.kugou.com/album/12345.html` |
| 酷我 | 单曲 | `https://www.kuwo.cn/song_detail/6489512` |
| 酷我 | 歌单 | `https://www.kuwo.cn/playlist_detail/1289073215` |
| 酷我 | 歌手 | `https://www.kuwo.cn/singer_detail/12345` |
| 酷我 | 专辑 | `https://www.kuwo.cn/album_detail/12345` |
| 咪咕 | 单曲 | `https://music.migu.cn/v5/#/songDetail?cId=600913000009337537` |
| 咪咕 | 歌单 | `https://music.migu.cn/v5/#/playListDetail?listId=12345` |
| 咪咕 | 专辑 | `https://music.migu.cn/v5/#/albumDetail?albumId=1142829638` |
| 咪咕 | 歌手 | `https://music.migu.cn/v5/#/singerDetail?id=259` |

## 使用说明

### 搜索歌曲
1. 在「搜索歌曲」标签页输入歌名或歌手名
2. 从搜索结果中勾选需要的歌曲
3. 点击「下载选中」

### 链接批量下载
1. 在「专辑/歌手/歌单链接」标签页粘贴链接
2. 点击「解析」，系统自动识别平台并勾选对应音源，同时获取全部歌曲列表
3. 勾选歌曲后下载，文件自动存入对应名称的文件夹

### 下载目录结构
```
/volume2/downloads2/music/
├── Adele/
│   ├── Someone Like You - Adele.flac
│   ├── Someone Like You - Adele.lrc
│   └── Hello - Adele.flac
├── 史上最全 | 名侦探柯南OP合集/
│   ├── 胸がドキドキ - THE HIGH-LOWS.mp3
│   └── ...
└── 普通搜索歌曲直接下载到此目录/
```

## 本地开发运行

```bash
pip install -r requirements.txt
python web_app.py
# 访问 http://localhost:8080
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DOWNLOAD_DIR` | `/downloads` | 音乐下载保存目录 |

## 技术栈

- 后端：Flask + musicdl 2.14.x
- 前端：原生 HTML/CSS/JS（无构建步骤）
- 部署：Docker / docker-compose

## 免责声明

本项目仅供个人学习与技术研究使用，所有音乐数据来源于公开平台接口。请遵守当地版权法律法规，勿用于商业用途。

## License

MIT
