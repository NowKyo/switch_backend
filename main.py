from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import requests
from bs4 import BeautifulSoup

app = FastAPI()

# ------------------------------------------------
# 1. BUSCADOR: DuckDuckGo API (JSON estable)
# ------------------------------------------------
@app.get("/search")
def search(q: str):
    try:
        api_url = (
            f"https://api.duckduckgo.com/?q={q}"
            "&format=json&no_redirect=1&no_html=1"
        )

        r = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()

        results = []

        # Resultado principal (si existe)
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", "Resultado"),
                "url": data.get("AbstractURL", ""),
                "snippet": data.get("AbstractText", "")
            })

        # Related Topics (lista de resultados)
        for item in data.get("RelatedTopics", []):
            # Si es resultado directo
            if isinstance(item, dict) and "FirstURL" in item:
                results.append({
                    "title": item.get("Text", ""),
                    "url": item.get("FirstURL", ""),
                    "snippet": item.get("Text", "")
                })

            # Si está agrupado
            if "Topics" in item:
                for sub in item["Topics"]:
                    results.append({
                        "title": sub.get("Text", ""),
                        "url": sub.get("FirstURL", ""),
                        "snippet": sub.get("Text", "")
                    })

        return {"results": results}

    except Exception:
        raise HTTPException(500, "Error en DuckDuckGo")


# ------------------------------------------------
# 2. SCRAPER DE PÁGINAS
#    Detecta videos dentro del HTML
# ------------------------------------------------
@app.get("/scrape")
def scrape(url: str):
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers)
    except:
        raise HTTPException(400, "URL no válida")

    soup = BeautifulSoup(r.text, "html.parser")

    # buscar videos en la página
    videos = []

    # Etiquetas <video>
    for tag in soup.find_all("video"):
        if tag.get("src"):
            videos.append(tag.get("src"))
        for source in tag.find_all("source"):
            if source.get("src"):
                videos.append(source.get("src"))

    # Links que terminan en video
    for link in soup.find_all("a"):
        href = link.get("href", "")
        if href.endswith((".mp4", ".webm", ".mov")):
            videos.append(href)

    # Convertir videos para Switch (stream proxy)
    fixed_videos = [
        f"https://switchvideo.onrender.com/stream?url={v}"
        for v in videos
    ]

    title = soup.title.string if soup.title else "Sin título"

    return {
        "title": title,
        "videos": fixed_videos,
        "raw_videos": videos
    }


# ------------------------------------------------
# 3. STREAMING PROXY
#    Convierte cualquier video en uno compatible
# ------------------------------------------------
@app.get("/stream")
def stream(url: str):
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, stream=True)
    except:
        raise HTTPException(400, "Video no accesible")

    return StreamingResponse(
        r.iter_content(chunk_size=1024),
        media_type="video/mp4"
    )


# Estado del servidor
@app.get("/")
def home():
    return {"status": "ok"}

