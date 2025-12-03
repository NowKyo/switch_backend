from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Permitir CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BRAVE_KEY = "brave_rkkf_1f2be8e6b1e07..."  # Ya te puse esta key temporal
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"

@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/search")
async def search(q: str = Query(..., min_length=1)):
    """
    Busca en Brave Search y regresa solo videos.
    """
    try:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_KEY
        }

        params = {
            "q": q + " video",
            "source": "web"
        }

        r = requests.get(BRAVE_URL, headers=headers, params=params, timeout=10)
        data = r.json()

        results = []

        if "web" in data and "results" in data["web"]:
            for item in data["web"]["results"]:
                url = item.get("url", "")
                title = item.get("title", "")

                # Aceptamos videos comunes de internet
                if any(x in url for x in ["youtube.com", "youtu.be", "mp4", "video"]):
                    results.append({
                        "title": title,
                        "url": url
                    })

        return results

    except Exception as e:
        return JSONResponse(
            {"detail": f"Error interno: {str(e)}"},
            status_code=500
        )
