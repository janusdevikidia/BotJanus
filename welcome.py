# il faut installer pywikibot avant

import time
import pywikibot
from pywikibot import config

RC_LIMIT = 20          # number of recentchanges to scan
WELCOME_TEXT = "{{Welcome}}~~~~"
WELCOME_SUMMARY = "Bot: welcome new user 👋"
SLEEP_AFTER_SAVE = 60   # seconds to sleep after a real save

# Run settings
DRY_RUN = True    # True = don't write, only show what would be done, if you want to edit put False
VERBOSE = True    # True = print progress; set False to be quieter

# ------------- main bot -------------
class WelcomeBot:
    def __init__(self):
        self.site = pywikibot.Site('en', 'vikidia')
        try:
            self.site.login()
        except Exception:
            if VERBOSE:
                pywikibot.output("⚠️ Login failed or not needed; continuing (may be anonymous).")
        # current bot username to avoid self-welcome
        try:
            self.myname = self.site.user()
        except Exception:
            self.myname = None
        self.welcomed = 0
        self.scanned = 0

    def run(self):
        if VERBOSE:
            pywikibot.output("▶️ WelcomeBotJanus starting (includes IPs). DRY_RUN=%s" % DRY_RUN)

        try:
            rc_iter = self.site.recentchanges(total=RC_LIMIT)
        except Exception as e:
            pywikibot.output(f"❌ Could not get recentchanges: {e}")
            return

        for rc in rc_iter:
            self.scanned += 1

            # extract username robustly from rc
            uname = None
            if isinstance(rc, dict):
                uname = rc.get('user')
            else:
                uname = getattr(rc, 'user', None) or getattr(rc, 'actor', None)

            if not uname:
                if VERBOSE:
                    pywikibot.output(f"[{self.scanned}] - no user found in RC entry; skipping.")
                continue

            # skip bot-like names (silent for self)
            if 'bot' in uname.lower():
                if self.myname and uname == self.myname:
                    if VERBOSE:
                        pywikibot.output(f"[{self.scanned}] {uname}: skipped (self).")
                else:
                    if VERBOSE:
                        pywikibot.output(f"[{self.scanned}] {uname}: skipped (bot-name).")
                continue

            # get the user talk page (fast)
            talk_title = f"User talk:{uname}"
            try:
                talk_page = pywikibot.Page(self.site, talk_title)
            except Exception:
                if VERBOSE:
                    pywikibot.output(f"[{self.scanned}] {uname}: cannot construct talk page, skipping.")
                continue

            # if talk page already exists, skip
            try:
                if talk_page.exists():
                    if VERBOSE:
                        pywikibot.output(f"[{self.scanned}] {uname}: skipped (talk page exists).")
                    continue
            except Exception:
                if VERBOSE:
                    pywikibot.output(f"[{self.scanned}] {uname}: failed to check talk page existence; skipping.")
                continue

            # Ready to welcome
            if DRY_RUN:
                pywikibot.output(f"[{self.scanned}] DRY RUN: would welcome {uname}")
                continue

            # Write welcome
            try:
                talk_page.text = WELCOME_TEXT
                talk_page.save(summary=WELCOME_SUMMARY)
                self.welcomed += 1
                pywikibot.output(f"[{self.scanned}] ✅ Welcomed {uname} (total: {self.welcomed})")
                time.sleep(SLEEP_AFTER_SAVE)
            except pywikibot.EditConflict:
                if VERBOSE:
                    pywikibot.output(f"[{self.scanned}] {uname}: edit conflict, skipped.")
                continue
            except Exception as e:
                pywikibot.output(f"[{self.scanned}] ❌ Error saving talk page for {uname}: {e}")
                continue

        pywikibot.output(f"🏁 Done. Scanned: {self.scanned}, Welcomed: {self.welcomed}")

# ------------- run -------------
def main():
    bot = WelcomeBot()
    bot.run()

if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
