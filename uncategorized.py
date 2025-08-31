# vous devez installer pywikibot comme ceci dans votre bash : pip install pywikibot

import pywikibot
from pywikibot import config, pagegenerators
import re
import time

# ----------------------
# CONFIGURATION DU BOT
# ----------------------

# Site ciblé : en.vikidia.org
site = pywikibot.Site('en', 'vikidia')  # nécessite la famille "vikidia" dans ta config pywikibot 
site.login()  # se logue avec les identifiants définis dans user-config.py

# ----------------------
# RÉGLAGES
# ----------------------
NUM_PAGES = 50
SLEEP_AFTER_EDIT = 60  # secondes : pause uniquement APRES une modification, si vous avez le botflag mettez 1

# Regex de détection
category_re = re.compile(r"\[\[\s*Category\s*:", re.IGNORECASE)
# template uncategorised/uncategorized, avec IGNORECASE et prise en charge d'éventuels paramètres: {{Uncategorized|...}}
uncat_re = re.compile(r"\{\{\s*(?:uncategorised|uncategorized)\b[^}]*\}\}", re.IGNORECASE)

# ----------------------
# GENERATEUR DE PAGES ALÉATOIRES
# ----------------------
# Utilisation correcte : RandomPageGenerator(total=...)
pages = pagegenerators.RandomPageGenerator(total=NUM_PAGES, site=site, namespaces=[0])

# ----------------------
# TRAITEMENT
# ----------------------
for page in pages:
    try:
        # skip redirect pages
        if page.isRedirectPage():
            print(f"↪️ Skipping redirect: {page.title()}")
            continue

        title = page.title()
        text = page.text
        original_text = text  # pour comparaison après modifs

        print(f"\n🔎 Checking: {title}")

        has_category = bool(category_re.search(text))
        has_uncat_template = bool(uncat_re.search(text))

        summary = None

        # cas : pas de catégories
        if not has_category:
            if not has_uncat_template:
                print("➡️ No categories & no uncat template → adding {{Uncategorized}} at bottom.")
                if not text.endswith("\n"):
                    text += "\n"
                text += "{{Uncategorized}}\n"
                summary = "Bot: add {{Uncategorized}} (page has no categories)"
            else:
                print("✔️ No categories but uncategorised template already present → nothing to do.")
        # cas : il y a des catégories ET le template uncategorised présent -> on supprime le template
        elif has_uncat_template:
            print("➡️ Has categories but still has uncategorised template → removing it.")
            text = uncat_re.sub("", text)
            # nettoyage des retours à la ligne superflus et ajout d'une fin propre
            text = re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"
            summary = "Bot: remove {{Uncategorized}}/{{uncategorised}} (categories present)"
        else:
            print("✔️ Has categories and no uncategorised template → nothing to do.")

        # sauvegarde si modifié
        if summary and text != original_text:
            page.text = text
            # attention : certains paramètres peuvent varier selon la version de pywikibot,
            # ici on utilise les arguments standards pour compatibilité
            page.save(summary=summary, minor=True)
            print(f"✅ Saved: {title} — {summary}")
            print(f"⏳ Sleeping {SLEEP_AFTER_EDIT}s (after edit)...")
            time.sleep(SLEEP_AFTER_EDIT)

    except pywikibot.exceptions.Error as e:
        print(f"❌ Pywikibot error on {page.title()}: {e}")
    except Exception as e:
        print(f"❌ Other error on {page.title()}: {e}")
