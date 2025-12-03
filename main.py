from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import requests
from bs4 import BeautifulSoup

app = FastAPI()

# ------------------------------------------------
# 1. BUSCADOR USANDO BRAVE SEARCH API (FUNCIONA EN RENDER)
# ------------------------------------------------
@app.get("/search")
def search(q: str):
    try:
        api_url = f"https://search.brave.com/api/suggest?q={q}"

        r = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()

        results = []

        # data[1] = títulos
        # data[2] = URLs
        titles = data[1]
        urls = data[2]

        for title, url in zip(titles, urls):
            results.append({
                "title": title,
                "url": url,
                "snippet": title
            })

        return {"results": results}

    except Exception:
        raise HTTPException(500, "Error en BRAVE")


# ------------------------------------------------
# 2. SCRAPER DE PÁGINAS PARA DETECTAR VIDEOS
# ------------------------------------------------
@app.get("/scrape")
def scrape(url: str):
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers)
    except:
        raise HTTPException(400, "URL no válida")

    soup = BeautifulSoup(r.text, "html.parser")

    videos = []

    # Buscar <video>
    for tag in soup.find_all("video"):
        if tag.get("src"):
            videos.append(tag.get("src"))
        for source in tag.find_all("source"):
            if source.get("src"):
                videos.append(source.get("src"))

    # Buscar links a .mp4/.webm
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href.endswith((".mp4", ".webm", ".mov")):
            videos.append(href)

    # Convertir videos a streaming proxy
    fixed = [
        f"https://switchvideo.onrender.com/stream?url={v}"
        for v in videos
    ]

    title = soup.title.string if soup.title else "Sin título"

    return {
        "title": title,
        "videos": fixed,
        "raw_videos": videos
    }


# ------------------------------------------------
# 3. STREAMING PROXY PARA QUE SWITCH PUEDA VER LOS VIDEOS
# ------------------------------------------------
@app.get("/stream")
def stream(url: str):
    try:
        r = requests.get(url, stream=True)
    except:
        raise HTTPException(400, "Video no accesible")

    return StreamingResponse(
        r.iter_content(chunk_size=1024),
        media_type="video/mp4"
    )


@app.get("/")
def home():
    return {"status": "ok"}
