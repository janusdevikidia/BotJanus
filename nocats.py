
"""
Script Pywikibot : Nettoyage des catégories mortes
Auteur : BotJanus
Description :
    Ce script choisit x pages aléatoires et supprime les catégories inexistantes.
"""

import pywikibot
import time
import random

# ==============================
# ⚙️  VARIABLES MODIFIABLES
# ==============================

# Nom du site (famille et langue, par ex : ('vikidia', 'fr'))
FAMILY = 'vikidia'
LANG = 'en'

# Nombre de pages aléatoires à traiter
N_PAGES = 10

# Délai (en secondes) entre chaque édition
SLEEP_TIME = 5

# Résumé d’édition
EDIT_SUMMARY =  "Removal of non-existent categories"

# ==============================
# 🚀  DÉBUT DU SCRIPT
# ==============================

# Création du site et connexion
site = pywikibot.Site(LANG, FAMILY)
site.login()

# Application du user-agent
print(f"Connecté à {LANG}.{FAMILY}.org en tant que {site.user()} ✅")
print(f"Traitement de {N_PAGES} pages aléatoires...\n")

# Récupération de pages aléatoires
pages = list(site.randompages(total=N_PAGES))

for page in pages:
    print(f"➡️  Analyse de la page : {page.title()}")
    try:
        text = page.text
        cats = page.categories()
        new_text = text
        removed = []

        # Vérifie chaque catégorie
        for cat in cats:
            if not cat.exists():
                cat_wikitext = f"[[{cat.title()}]]"
                # Supprime toutes les occurrences dans le texte
                if cat_wikitext in new_text:
                    new_text = new_text.replace(cat_wikitext, "")
                    removed.append(cat.title())

        if removed and new_text != text:
            print(f"   🧹 Catégories supprimées : {', '.join(removed)}")
            page.text = new_text.strip()
            page.save(summary=EDIT_SUMMARY)
        else:
            print("   ✅ Rien à supprimer.")

        print(f"   ⏳ Attente de {SLEEP_TIME} sec avant la prochaine page...\n")
        time.sleep(SLEEP_TIME)

    except Exception as e:
        print(f"   ⚠️ Erreur sur {page.title()} : {e}")
        continue

print("✅ Script terminé ! 🎉")
