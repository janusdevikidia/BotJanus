# si vous voulez utiliser ce script assurez vous d'avoir rempli tout les paramètres entres crochets ([])
import re
import time
import requests
import pywikibot

# ====== VARIABLES ======
langue = "fr"  # langue du wiki ("fr", "en", ...)
wikiurl = "https://fr.vikidia.org"  # URL du wiki
message = "[texte]"  # texte à poster
titre = "[titre]"  # titre de la section
resume = "[résumé]"  # résumé de modification
page_abonnes = "[page abonnés]"  # doit contenir des liens avec Discussion utilisateur ou User talk
delai = 60  # délai en secondes entre chaque envoi

# Connexion au site avec Pywikibot
site = pywikibot.Site(langue, "vikidia", user="[le nom de votre Bot]")
site.login()

# Charger la page des abonnés
abonnes_page = pywikibot.Page(site, page_abonnes)
texte_abonnes = abonnes_page.get()

# Extraire les utilisateurs
pattern = r"\*\s*\[\[\s*(?:Discussion\s+utilisateur(?:rice)?|User talk)\s*:\s*([^\]|]+)"
utilisateurs = re.findall(pattern, texte_abonnes, flags=re.IGNORECASE)

print(f"✅ {len(utilisateurs)} abonnés trouvés : {utilisateurs}")

# Boucle sur chaque utilisateur
for i, user in enumerate(utilisateurs, start=1):
    # Construire la PDD
    pdd = pywikibot.Page(site, f"Discussion utilisateur:{user}")
    print(f"[{i}/{len(utilisateurs)}] → Ajout du texte à la fin de {pdd.title()}")

    # Ajouter le texte à la fin sans supprimer le reste
    pdd.text = pdd.text + f"\n\n== {titre} ==\n{message}"

    # Sauvegarder avec résumé
    pdd.save(summary=resume)

    # Pause pour éviter les 429
    if i < len(utilisateurs):
        print(f"⏳ Pause de {delai} sec avant le prochain envoi...")
        time.sleep(delai)

print("✅ Toutes les PDD ont ét
é traitées. Opération terminée.")
