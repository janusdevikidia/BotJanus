import pywikibot
import requests
import time
from pywikibot.pagegenerators import RandomPageGenerator

# Connexion au site Vikidia en anglais
site_vikidia = pywikibot.Site('en', 'vikidia')
# USER_AGENT = votre user agent

# Vérifie si un titre existe sur Wikipedia et n'est pas une désambiguïsation
def check_wikipedia_article(title):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "categories",
        "redirects": 1,
        "format": "json"
    }
    try:
        r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}).json()
    except Exception as e:
        return None, f"Error contacting Wikipedia: {e}"

    pages = r["query"]["pages"]
    page = next(iter(pages.values()))

    if "missing" in page:
        return None, "Not found"

    if "categories" in page:
        for cat in page["categories"]:
            if "disambiguation" in cat["title"].lower():
                return None, "Disambiguation"

    return page["title"], "OK"

# Ajoute l'interwiki à la fin de l'article Vikidia
def add_interwiki_to_article(vikidia_title):
    if "(" in vikidia_title or ")" in vikidia_title:
        print(f"➡️ {vikidia_title} — SKIPPED (Title may cause parser issues)")
        return

    try:
        page = pywikibot.Page(site_vikidia, vikidia_title)
        if page.namespace() != 0:
            print(f"➡️ {vikidia_title} — SKIPPED (Not in main namespace)")
            return
        text = page.text
    except Exception as e:
        print(f"➡️ {vikidia_title} — SKIPPED (Error reading page: {e})")
        return

    wp_title, status = check_wikipedia_article(vikidia_title)
    if not wp_title:
        print(f"➡️ {vikidia_title} — SKIPPED ({status})")
        return

    interwiki_code = f"[[wp:{wp_title}]]"
    if interwiki_code in text:
        print(f"➡️ {vikidia_title} — Interwiki déjà présent")
        return

    try:
        page.text = text.strip() + "\n\n" + interwiki_code
        page.save(summary="Add interwiki to en.wikipedia")
        print(f"✅ {vikidia_title} — Interwiki ajouté : {interwiki_code}")
    except Exception as e:
        print(f"➡️ {vikidia_title} — SKIPPED (Error saving page: {e})")

# Récupère N pages aléatoires de Vikidia
def get_random_vikidia_pages(n=50):
    generator = RandomPageGenerator(total=n, site=site_vikidia)
    return [page.title() for page in generator]

# Script principal
if __name__ == "__main__":
    random_titles = get_random_vikidia_pages(200)
    for title in random_titles:
        add_interwiki_to_a
rticle(title)
