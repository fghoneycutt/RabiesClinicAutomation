# ==============================================================================
# Microchip Module (FIXED v5 - STREAMLINED COALESCE PIPELINE)
# ==============================================================================

import time


def safe(v):
    if v is None:
        return ""
    return str(v).strip()


def add_microchip_if_needed(page, animal, safe_click, fill_livewire, normalize_date, log):

    raw_chip = animal.get("microchip_number")
    
    # Process and sanitize Excel float strings (e.g., '900262007514220.0' -> '900262007514220')
    microchip = ""
    if raw_chip and str(raw_chip).strip().lower() not in ["nan", "", "none"]:
        try:
            microchip = str(int(float(raw_chip)))
        except ValueError:
            microchip = str(raw_chip).strip().split('.')[0]

    if not microchip:
        return page

    # =================================================
    # 1. CHECK FOR MICROCHIP SECTION EXISTENCE
    # =================================================
    microchip_section = page.locator("text=Microchip Number")

    if microchip_section.count() > 0:
        container = microchip_section.first.locator("xpath=ancestor::*[1]")
        existing_text = safe(container.inner_text())

        if existing_text:
            log(f"🔍 Existing microchip block found: {existing_text}")
            digits = "".join([c for c in existing_text if c.isdigit()])

            if digits and microchip in digits:
                log("🧬 Microchip already exists — skipping modal")
                return page

    # =================================================
    # 2. OPEN MICROCHIP MODAL
    # =================================================
    log(f"🔬 Adding microchip to existing profile: {microchip}")

    safe_click(
        page,
        lambda: page.locator('[data-cy="addMicrochip"]'),
        "microchip"
    )

    modal = page.locator("#modal-container")
    modal.wait_for(state="visible", timeout=15000)

    # =================================================
    # 3. SELECT ISSUER (Fi Nano)
    # =================================================
    issuer = modal.locator('[data-cy="form.issuer"]')
    options = issuer.locator("option")
    selected = False

    for i in range(options.count()):
        label = safe(options.nth(i).inner_text())
        if "fi nano" in label.lower():
            issuer.select_option(label=label)
            selected = True
            break

    if not selected and options.count() > 1:
        issuer.select_option(label=safe(options.nth(1).inner_text()))

    # =================================================
    # 4. MICROCHIP NUMBER (DIRECT FILL)
    # =================================================
    number_input = modal.locator('[data-cy="form.number"]')
    number_input.click()
    number_input.fill(microchip)
    number_input.blur()

    # =================================================
    # 5. IMPLANT DATE (GUARANTEED EXCEL DATE PIPELINE)
    # =================================================
    # COALESCE ensures this cell always contains a real date (Vaccination or Clinic date)
    implant_date = normalize_date(animal.get("date_vaccinated"))

    date_input = modal.locator('[data-cy="forminserted_at"]')
    date_input.click()
    date_input.fill(implant_date)
    date_input.blur()
    page.wait_for_timeout(400)

    log(f"📅 Implant date filled and blurred: {implant_date}")

    # =================================================
    # 6. SAVE - WITH TIMEOUT BUFFERS
    # =================================================
    save_btn = modal.locator('button[data-cy="modal-save"]')
    save_btn.wait_for(state="visible", timeout=15000)
    
    # A tiny wait allows the component's change/blur events to finish syncing
    page.wait_for_timeout(400) 
    
    save_btn.click(force=True)
    
    # CHANGE THIS LINE: Wait for the modal wrapper to become HIDDEN, not detached
    modal.wait_for(state="hidden", timeout=15000)
    log("✅ Microchip successfully validated and saved")

    return page