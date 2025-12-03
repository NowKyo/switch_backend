from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/search")
async def search(q: str = Query(..., min_length=1)):
    try:
        url = f"https://www.bing.com/videos/api/getresults?q={q}&count=50"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
        }

        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()

        results = []

        for item in data.get("videos", []):
            title = item.get("tit")
            link = item.get("murl") or item.get("rurl")

            if title and link:
                results.append({
                    "title": title,
                    "url": link
                })

        return results

    except Exception as e:
        return JSONResponse(
            {"detail": f"Error interno: {str(e)}"},
            status_code=500
        )
