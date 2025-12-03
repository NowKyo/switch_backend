from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

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
        url = f"https://www.bing.com/videos/search?q={q}&FORM=HDRSC4"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
        }

        page = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.text, "html.parser")

        results = []

        # Selección correcta de hoy:
        for a in soup.select("a.mc_vtvc_link"):
            title = a.get("title", "").strip()
            link = a.get("href", "")

            if not link.startswith("http"):
                link = "https://www.bing.com" + link

            if title and link:
                results.append(
                    {
                        "title": title,
                        "url": link
                    }
                )

        return results

    except Exception as e:
        return JSONResponse({"detail": f"Error interno: {str(e)}"}, status_code=500)
