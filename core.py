# ==============================================================================
# Shelterluv Automation Core
# FINAL STABLE ORCHESTRATOR (UPDATED FOR INLINE RECONCILIATION & CHIP GUARD - 2026)
# ==============================================================================

from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import os
import time
import csv

# Import production Fi Nano integration layout module
import finano

from person_update import update_person_profile

from people import (
    find_person,
    open_add_person_modal,
    create_person_if_missing
)

from animals import (
    find_or_open_animal,
    complete_animal_form,
    add_microchip,
    submit_animal,
    open_animal,
    animal_name_matches
)

from microchips import add_microchip_if_needed

from vaccines import complete_vaccine

STORAGE_STATE_PATH = "shelterluv_storage.json"

def normalize_phone(value):
    """
    Converts phone values into Shelterluv display format:
    (###) ###-####
    
    Handles:
    - integers from Excel
    - raw digits
    - already formatted numbers
    - dashed/spaced formats
    """

    if value is None:
        return ""

    raw = str(value).strip()

    if raw.lower() in ["", "nan", "none"]:
        return ""

    # Remove Excel artifact
    if raw.endswith(".0"):
        raw = raw[:-2]

    # Keep digits only
    digits = "".join(
        c for c in raw
        if c.isdigit()
    )

    # Basic US phone validation
    if len(digits) != 10:
        return raw

    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

# ==============================================================================
# MAIN ENTRY
# ==============================================================================
def run_automation(input_file, log=print):

    # --------------------------------------------------------------------------
    # logging wrapper
    # --------------------------------------------------------------------------
    def log_safe(msg):
        try:
            log(msg)
        except Exception:
            print(msg)

    # --------------------------------------------------------------------------
    # SAFE CLICK
    # --------------------------------------------------------------------------
    def safe_click(page, locator_fn, label="", retries=4):
        last_err = None

        for i in range(retries):
            try:
                if page.is_closed():
                    raise Exception("Page closed")

                locator = locator_fn()

                locator.wait_for(state="visible", timeout=8000)
                locator.scroll_into_view_if_needed()
                page.wait_for_timeout(250)

                locator.click(force=True)
                return True

            except Exception as e:
                last_err = e
                log_safe(f"⚠️ Click failed ({label}) attempt {i+1}/{retries}: {e}")
                time.sleep(0.4)

        raise last_err

    # --------------------------------------------------------------------------
    # LIVEWIRE INPUT
    # --------------------------------------------------------------------------
    def fill_livewire(locator, value):
        locator.scroll_into_view_if_needed()
        locator.click()
        locator.fill(str(value or ""))

        locator.evaluate("""
            (el) => {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
            }
        """)

    # --------------------------------------------------------------------------
    # NORMALIZE DATE
    # --------------------------------------------------------------------------
    def normalize_date(value):
        if value is None or value == "":
            return ""

        try:
            if hasattr(value, "strftime"):
                return value.strftime("%m/%d/%Y")
        except Exception:
            pass

        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(str(value).strip(), fmt).strftime("%m/%d/%Y")
            except Exception:
                pass

        return str(value).strip()

    # --------------------------------------------------------------------------
    # WAIT: PEOPLE PAGE READY
    # --------------------------------------------------------------------------
    def wait_people_page_ready(page):
        page.wait_for_load_state("networkidle")

        page.wait_for_selector(
            'input[placeholder*="Search by name"]',
            state="visible",
            timeout=15000
        )

        page.wait_for_timeout(500)

    # --------------------------------------------------------------------------
    # LOAD FILE
    # --------------------------------------------------------------------------
    def load_records(file_path):
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".xlsx":
            import pandas as pd
            return pd.read_excel(file_path).fillna("").to_dict("records")

        with open(file_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f, delimiter="\t"))

    # --------------------------------------------------------------------------
    # GROUP OWNERS
    # --------------------------------------------------------------------------
    def group_by_owner(rows):
        grouped = defaultdict(list)

        for r in rows:
            key = (
                str(r.get("person_first_name") or "").strip(),
                str(r.get("person_last_name") or "").strip(),
                normalize_phone(r.get("phone")),
                str(r.get("address") or "").strip().lower(),
            )

            grouped[key].append(r)

        return grouped

    # ==========================================================================
    # PLAYWRIGHT START
    # ==========================================================================
    with sync_playwright() as p:

        # Initialize Combined Browser Context
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(
            no_viewport=True,
            storage_state=STORAGE_STATE_PATH if os.path.exists(STORAGE_STATE_PATH) else None
        )
        page = context.new_page()

        log_safe(f"📁 Shelterluv Storage file exists: {os.path.exists(STORAGE_STATE_PATH)}")

        # --------------------------------------------------------------------------
        # OPEN SHELTERLUV
        # --------------------------------------------------------------------------
        page.goto("https://new.shelterluv.com/dashboard?tab=people")
        page.wait_for_load_state("networkidle")

        # --------------------------------------------------------------------------
        # LOGIN HANDLING
        # --------------------------------------------------------------------------
        if "login" in page.url.lower():
            log_safe("🔑 Please log into Shelterluv manually...")

        wait_people_page_ready(page)

        context.storage_state(path=STORAGE_STATE_PATH)
        log_safe("💾 Shelterluv Session saved.")
        log_safe("✅ Logged into Shelterluv Dashboard Context")

        rows = load_records(input_file)
        groups = group_by_owner(rows)

        # ==========================================================================
        # MAIN LOOP
        # ==========================================================================
        for (first, last, phone, address), animals in groups.items():

            log_safe(f"\n👤 Processing owner entity: {first} {last} ({len(animals)} records)")

            is_new_person = False
            person_match = find_person(
                page,
                first,
                last,
                data=animals[0],
                log=log_safe
            )

            # --------------------------------------------------------------------------
            # CREATE PERSON IF MISSING
            # --------------------------------------------------------------------------
            if not person_match:
                is_new_person = True
                data = animals[0]

                create_person_if_missing(
                    page,
                    safe_click,
                    log_safe,
                    data
                )
                
                log_safe("📍 Verification: Session currently stabilized inside newly initialized profile.")

            else:
                # --------------------------------------------------------------------------
                # BASELINE NAV TO OWNER PROFILE SCREEN (ONLY FOR EXISTING PEOPLE)
                # --------------------------------------------------------------------------
                profile_url = person_match["profile_url"]

                owner_profile_url = (
                    profile_url
                    if profile_url.startswith("http")
                    else f"https://new.shelterluv.com{profile_url}"
                )
                page.goto(owner_profile_url)
                page.wait_for_load_state("networkidle")
                if person_match["needs_update"]:
                    update_person_profile(
                        page,
                        animals[0],
                        person_match["changes"],
                        log_safe
                    )

            # ==========================================================================
            # SUB-LOOP: ANIMAL PROCESSING
            # ==========================================================================
            for animal in animals:

                target_name = animal.get("animal_name", "")
                
                # Make sure base tab explicitly focuses the profile layout context
                page.bring_to_front()

                target_tab, already_exists = find_or_open_animal(
                    page,
                    context,
                    target_name,
                    log_safe,
                    is_new_person=is_new_person
                )

                should_register_fi = True

                if not already_exists:
                    # ------------------------------------------------------------------
                    # PATHWAY A: NEW ANIMAL INTAKE FORM ENCOUNTER
                    # ------------------------------------------------------------------
                    log_safe(f"✍️ Form layout detected. Injecting core fields for {target_name}.")
                    
                    complete_animal_form(target_tab, animal, log_safe)
                    add_microchip(target_tab, animal, log_safe)
                    
                    # Capture flag status from submission guard step (False if duplicate microchip intercepted)
                    should_register_fi = submit_animal(target_tab, log_safe)
                    
                    log_safe("🔄 Landing back on owner profile. Locating fresh link to open medical context...")
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(1000)
                    
                    fresh_links = page.locator("a[href*='/animal/']")
                    matched_link = None
                    for idx in range(fresh_links.count()):
                        lnk = fresh_links.nth(idx)
                        try:
                            if animal_name_matches(lnk.inner_text(), target_name):
                                matched_link = lnk
                                break
                        except:
                            continue
                    
                    if matched_link:
                        log_safe(f"🐾 Opening dedicated profile tab context for newly populated: {target_name}")
                        animal_profile_tab = open_animal(page, context, matched_link)
                    else:
                        log_safe(f"⚠️ Redirection link context discovery failed for {target_name}.")
                        continue
                else:
                    # ------------------------------------------------------------------
                    # PATHWAY B: EXISTING ANIMAL PROFILE VIEW
                    # ------------------------------------------------------------------
                    animal_profile_tab = target_tab
                    log_safe(f"🐾 Evaluating chip parameters inside isolation window for existing entity: {target_name}")
                    
                    # Capture flag status from profile reconciliation (False if it matches perfectly, True if changed)
                    should_register_fi = add_microchip_if_needed(
                        page=animal_profile_tab,
                        animal=animal,
                        safe_click=safe_click,
                        fill_livewire=fill_livewire,
                        normalize_date=normalize_date,
                        log=log_safe
                    )

                # ==========================================================================
                # SHARED UNIFIED TRACK: VACCINES (Runs inside separate animal profile tab)
                # ==========================================================================
                animal_profile_tab.bring_to_front()
                complete_vaccine(
                    page=animal_profile_tab,
                    animal=animal,
                    safe_click=safe_click,
                    fill_livewire=fill_livewire,
                    log=log_safe
                )

                # Explicitly close out the temporary animal tab context and return control to Owner context
                log_safe(f"🛡️ Closing animal tab context for {target_name}. Reverting tracking focus.")
                animal_profile_tab.close()
                page.bring_to_front()

                # ==========================================================================
                # CONDITIONAL PRODUCTION INTEGRATION STEP: FI NANO WIRE-UP
                # ==========================================================================
                chip_id = str(animal.get("microchip_number", "")).strip()
                chip_issuer = str(animal.get("microchip_issuer", "")).strip()

                should_register_with_fi = (
                    chip_id
                    and chip_id.lower() != "none"
                    and chip_issuer.lower() == "fi nano"
                    and should_register_fi
                )

                if should_register_with_fi:
                    log_safe(f"📡 Fi Nano workflow activated [{chip_id}]. Opening shared Fi Nano tab...")
                    try:
                        # Request the clean page tab in the shared window context
                        fi_page = finano.get_fi_page_in_shared_context(context)
                        fi_page.bring_to_front()

                        # Process registration form sequence
                        finano.register_single_pet(fi_page, animal)

                        # Close the tracking page tab context explicitly
                        log_safe(f"🛡️ Closing Fi Nano tab context for {target_name}.")
                        fi_page.close()

                    except Exception as fi_err:
                        log_safe(f"❌ Automation workflow failed or timed out on Fi Nano interface: {str(fi_err)}")

                    finally:
                        page.bring_to_front()

                else:
                    if not chip_id or chip_id.lower() == "none":
                        log_safe(f"ℹ️ No microchip data assigned for {target_name}. Bypassing Fi Nano tracking window.")

                    elif chip_issuer.lower() != "fi nano":
                        log_safe(
                            f"ℹ️ Microchip issuer is '{chip_issuer}'. Fi Nano registration not required."
                        )

                    elif not should_register_fi:
                        log_safe(
                            "🛑 Bypassing Fi Nano: Microchip already matched the existing record (or rejected as duplicate). No registration required."
                        )

            # --------------------------------------------------------------------------
            # CLEAN RETURN TO DASHBOARD AFTER ALL WORK ENTITIES COMPLETED FOR THIS PERSON
            # --------------------------------------------------------------------------
            log_safe("🏠 All scheduled animals processed for this owner. Returning to Dashboard.")
            page.goto("https://new.shelterluv.com/dashboard?tab=people")
            wait_people_page_ready(page)

        # --------------------------------------------------------------------------
        # SAVE SESSIONS AND CLOSE OUT CONTEXTS
        # --------------------------------------------------------------------------
        try:
            context.storage_state(path=STORAGE_STATE_PATH)
            log_safe(f"💾 Shelterluv Session successfully synced to {STORAGE_STATE_PATH}")
        except Exception as e:
            log_safe(f"⚠️ Failed Shelterluv session state update: {e}")

        log_safe("🎉 COMPLETE")
        browser.close()