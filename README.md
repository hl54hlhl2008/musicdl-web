# MusicDL Web

基于 [musicdl](https://github.com/CharlesPikachu/musicdl) 的 NAS 远程音乐下载工具，通过浏览器操作，支持网易云/QQ音乐/咪咕等多音源搜索与批量下载。

## 功能

- 🔍 多音源搜索（网易云、QQ音乐、咪咕）
- 🔗 链接解析下载：
  - 网易云歌手/专辑/歌单链接
  - QQ音乐歌单链接
  - 咪咕专辑/歌手链接
- 📁 自动按歌手/专辑/歌名单独建文件夹
- 🎵 自动下载同名 .lrc 歌词文件
- 🐳 Docker 一键部署，适配群晖 NAS

## 部署（群晖 Container Manager）

### docker-compose.yml

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

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY web_app.py .
EXPOSE 8080
CMD ["python", "web_app.py"]
```

### requirements.txt

```
musicdl>=2.14.1
flask>=3.0.0
requests>=2.31.0
```

## 使用

1. 访问 `http://你的NAS_IP:58092`
2. 搜索歌曲或粘贴网易云/QQ/咪咕链接
3. 勾选歌曲，点击下载

## 支持的链接格式

| 平台 | 格式示例 |
|------|---------|
| 网易云歌手 | `https://music.163.com/#/artist?id=xxx` |
| 网易云歌单 | `https://music.163.com/#/playlist?id=xxx` |
| 网易云专辑 | `https://music.163.com/#/album?id=xxx` |
| QQ音乐歌单 | `https://y.qq.com/n/ryqq_v2/playlist/xxx` |
| 咪咕专辑 | `https://music.migu.cn/v5/#/albumDetail?albumId=xxx` |
| 咪咕歌手 | `https://music.migu.cn/v5/#/singerDetail?id=xxx` |

## License

MIT
