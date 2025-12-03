# main.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests, subprocess, uuid, os, json, shlex
from bs4 import BeautifulSoup

app = FastAPI()
# Permitir llamadas desde GitHub Pages / cualquier origen (ajusta si quieres)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok"}

# ---- DuckDuckGo HTML search (sin API key) ----
@app.get("/search")
def search(q: str = Query(...), max_results: int = 10):
    """
    Realiza una búsqueda en DuckDuckGo (versión HTML) y devuelve resultados.
    """
    url = "https://duckduckgo.com/html/"
    params = {"q": q}
    r = requests.post(url, data=params, timeout=15)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Error en DuckDuckGo")
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for a in soup.select(".result__a"):
        if len(results) >= max_results:
            break
        title = a.get_text().strip()
        href = a.get("href")
        # duckduckgo returns relative redirect links like "/l/?kh=-1&uddg=ENCODEDURL"
        # We attempt to extract the real URL from uddg param if present
        if href and "uddg=" in href:
            # try to extract parameter
            try:
                from urllib.parse import parse_qs, urlparse, unquote
                parsed = urlparse(href)
                q = parse_qs(parsed.query)
                if "uddg" in q:
                    real = unquote(q["uddg"][0])
                    href = real
            except Exception:
                pass
        results.append({"title": title, "url": href})
    return JSONResponse({"query": q, "results": results})

# ---- Scrape a webpage and list videos found ----
@app.get("/scrape")
def scrape(url: str = Query(...)):
    """
    Descarga la página indicada, busca URLs de video y devuelve:
    - metadata (title, description)
    - lista de videos encontrados (mp4/webm, iframes, ytdlp-extracted)
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible)"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al descargar la página: {e}")

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Status {r.status_code} al descargar la página")

    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.title.string.strip() if soup.title else ""
    description = ""
    desc_tag = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
    if desc_tag and desc_tag.get("content"):
        description = desc_tag.get("content").strip()

    videos = []

    # 1) Buscar etiquetas <video> y <source>
    for v in soup.find_all("video"):
        # direct src
        src = v.get("src")
        if src:
            videos.append({"type":"video-tag", "url":requests.compat.urljoin(url, src)})
        # source inside video
        for s in v.find_all("source"):
            src2 = s.get("src")
            if src2:
                videos.append({"type":"video-source", "url":requests.compat.urljoin(url, src2)})

    # 2) Buscar links directos a mp4/webm
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith((".mp4", ".webm", ".m3u8")):
            videos.append({"type":"direct-link", "url": requests.compat.urljoin(url, href)})

    # 3) Iframes (podemos devolver el src para intentar extraer con yt-dlp)
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if src:
            videos.append({"type":"iframe", "url": requests.compat.urljoin(url, src)})

    # 4) Intentar extraer con yt-dlp (más fiable para YouTube/Many providers)
    # Ejecutamos yt-dlp --dump-single-json --no-warnings --skip-download <url>
    # y parseamos formatos (no descargamos).
    try:
        proc = subprocess.run(
            ["yt-dlp", "--no-warnings", "--skip-download", "--dump-single-json", url],
            capture_output=True, text=True, timeout=40
        )
        if proc.returncode == 0 and proc.stdout:
            info = json.loads(proc.stdout)
            # buscar formatos con direct video URL (mp4/webm/hls)
            if "formats" in info:
                for f in info["formats"]:
                    f_url = f.get("url")
                    if f_url:
                        # evitar duplicados
                        videos.append({"type":"yt-dlp-format", "url": f_url, "format_id": f.get("format_id")})
            # also try 'url' top-level
            if "url" in info and info["url"]:
                videos.append({"type":"yt-dlp-top-url", "url": info["url"]})
    except Exception:
        # No es crítico; seguimos con lo que tengamos
        pass

    # Deduplicate preserving order
    seen = set()
    dedup = []
    for v in videos:
        u = v.get("url")
        if not u: continue
        if u in seen: continue
        seen.add(u)
        dedup.append(v)

    # Convert any found video urls into proxy /stream links
    stream_links = []
    for v in dedup:
        u = v["url"]
        # Build the public streaming URL at your render backend
        proxy = f"https://switchvideo.onrender.com/stream?url={requests.utils.requote_uri(u)}"
        stream_links.append({"type": v.get("type"), "original_url": u, "stream_url": proxy})

    return JSONResponse({
        "title": title,
        "description": description,
        "original_url": url,
        "videos": stream_links
    })

# ---- Streaming proxy (simple) ----
@app.get("/stream")
def stream_video(url: str = Query(...)):
    """
    Proxy streaming: obtiene el contenido remoto y lo pasa al cliente.
    (Nota: esto reenvía bytes tal cual; si quieres convertir con ffmpeg o frames,
    se debe implementar procesamiento adicional).
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        remote = requests.get(url, stream=True, headers=headers, timeout=20)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al solicitar el recurso: {e}")

    if remote.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Status {remote.status_code} from origin")

    def iterfile():
        for chunk in remote.iter_content(chunk_size=1024*8):
            if chunk:
                yield chunk

    # intentamos deducir content-type
    ctype = remote.headers.get("Content-Type", "video/mp4")
    return StreamingResponse(iterfile(), media_type=ctype)
