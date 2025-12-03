import requests
from bs4 import BeautifulSoup
import time

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ============================
#  BUSCADORES
# ============================

def search_google(q):
    url = f"https://www.google.com/search?q={q}&num=50"
    try:
        html = requests.get(url, headers=HEADERS, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.select("a"):
            h = a.get("href","")
            if h.startswith("/url?q="):
                h = h.split("/url?q=")[1].split("&")[0]
                if h.startswith("http"):
                    links.append(h)
        return links
    except:
        return []

def search_bing(q):
    url = f"https://www.bing.com/search?q={q}&count=50"
    try:
        html = requests.get(url, headers=HEADERS, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        return [a["href"] for a in soup.select("li.b_algo h2 a") if a.get("href","").startswith("http")]
    except:
        return []

def search_duck(q):
    url = f"https://duckduckgo.com/html/?q={q}"
    try:
        html = requests.get(url, headers=HEADERS, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        return [a["href"] for a in soup.select(".result__a")]
    except:
        return []

def search_yahoo(q):
    url = f"https://search.yahoo.com/search?p={q}"
    try:
        html = requests.get(url, headers=HEADERS, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        return [a["href"] for a in soup.select("h3.title a") if a.get("href","").startswith("http")]
    except:
        return []


# ============================
# CRAWLER PROFUNDO
# ============================

def deep_crawl(url, depth=1, visited=None):
    if visited is None:
        visited = set()

    if depth == 0 or url in visited:
        return []

    visited.add(url)
    links = []

    try:
        html = requests.get(url, headers=HEADERS, timeout=10).text
    except:
        return []

    soup = BeautifulSoup(html, "html.parser")

    for a in soup.select("a[href]"):
        href = a["href"]
        if href.startswith("http") and "google" not in href and "bing" not in href:
            links.append(href)

    # Limitar a 10 links para evitar explosión
    deeper = []
    for link in links[:10]:
        deeper += deep_crawl(link, depth - 1, visited)

    return list(set(links + deeper))


# ============================
# MEGA BUSCADOR FINAL
# ============================

def mega_search(query, crawl_depth=1):
    print("Buscando en Google...")
    g = search_google(query)
    time.sleep(1)

    print("Buscando en Bing...")
    b = search_bing(query)
    time.sleep(1)

    print("Buscando en DuckDuckGo...")
    d = search_duck(query)
    time.sleep(1)

    print("Buscando en Yahoo...")
    y = search_yahoo(query)

    # combino todos
    all_links = list(set(g + b + d + y))

    print(f"Encontrados {len(all_links)} links iniciales.")

    # CRAWLING PROFUNDO
    crawled = []
    for link in all_links[:20]:  # limite para evitar lags
        print(f"Crawling: {link}")
        crawled += deep_crawl(link, crawl_depth)

    final = list(set(all_links + crawled))
    print(f"Total final: {len(final)} links recopilados.")

    return final


# ============================
# PRUEBA
# ============================

resultados = mega_search("perritos", crawl_depth=2)

for r in resultados[:50]:
    print(r)
