# installez pywikibot avant
import pywikibot
import re
import time
import requests

# Connexion au site
site = pywikibot.Site('en', 'vikidia')
site.login()

# Session requests pour limiter les erreurs 429
S = requests.Session()
wikiurl = "https://en.vikidia.org"  # URL du wiki

def search_page(search):
    """Faire une recherche via l'API avec requests pour limiter les 429."""
    searchurl = "https://en.vikidia.org/w/api.php"
    searchparam = {
        'action': "query",
        'list': "search",
        'srsearch': search,
        'format': "json",
    }
    R = S.get(url=searchurl, params=searchparam)
    if R.status_code == 429:
        print("⚠️ Trop de requêtes ! Pause 60s...")
        time.sleep(60)
        R = S.get(url=searchurl, params=searchparam)
    return R.json()

def gerer_orphelin(page):
    """Ajoute ou retire {{orphan}} selon si la page est orpheline ou non."""
    content = page.text
    backlinks = list(page.getReferences(total=1))
    is_linked = len(backlinks) > 0
    has_orphan = re.search(r"\{\{\s*[Oo]rphan\s*(\|[^}]*)?\s*\}\}", content) is not None

    if is_linked and has_orphan:
        new_content = re.sub(r"\{\{\s*[Oo]rphan\s*(\|[^}]*)?\s*\}\}\n?", "", content, flags=re.I)
        if new_content != content:
            page.text = new_content
            page.save(summary="- orphan")
            print(f"✅ {page.title()} : orphan retiré")
            return True
        return False

    if not is_linked and not has_orphan:
        new_content = "{{orphan}}\n" + content
        page.text = new_content
        page.save(summary="+ orphan")
        print(f"✅ {page.title()} : orphan ajouté")
        return True

    print(f"ℹ️ {page.title()} : pas de modification nécessaire")
    return False

# ---- Programme principal ----
def main():
    random_pages = []
    for page in site.randompages(total=70):
        if page.namespace() == 0:
            random_pages.append(page)
        if len(random_pages) >= 50:
            break

    print("🔎 Articles sélectionnés :")
    for p in random_pages:
        print("-", p.title())

    for page in random_pages:
        try:
            modified = gerer_orphelin(page)
            if modified:
                print("⏳ Pause 60s avant la prochaine modification...")
                time.sleep(60)
        except Exception as e:
            print(f"⚠️ Erreur sur {page.title()} : {e}")

if __name__ == "__main__":
    main()
