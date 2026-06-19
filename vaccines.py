# ==============================================================================
# Vaccines Module (UPDATED WITH INTEGER STRING CLEANUP - 2026)
# ==============================================================================

from datetime import datetime


def safe(v):
    return "" if v is None else str(v)


def clean_int_string(value):
    """
    Safely strips away trailing floating-point decimals (.0) added by Excel parsers,
    returning a clean numerical string.
    """
    raw_val = safe(value).strip()
    if not raw_val or raw_val.lower() in ["nan", "none"]:
        return ""
    try:
        # Cast float to int first to clean out '.0' without losing string format safety
        return str(int(float(raw_val)))
    except ValueError:
        # Fallback split if there's an unexpected non-numeric character string
        return raw_val.split('.')[0]


def normalize_date(value):
    if value is None or value == "":
        return ""

    try:
        if hasattr(value, "strftime"):
            return value.strftime("%m/%d/%Y")
    except:
        pass

    for fmt in (
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(str(value).strip(), fmt).strftime("%m/%d/%Y")
        except:
            pass

    return str(value).strip()


def complete_vaccine(
    page,
    animal,
    safe_click,
    fill_livewire,
    log
):
    """
    Full vaccine modal flow (Resilient to blank data rows and trailing decimals)
    """
    vaccine_product = safe(animal.get("product")).strip()
    date_vacc = safe(animal.get("date_vaccinated")).strip()

    # --------------------------------------------------------------------------
    # GUARD CLAUSE FOR BLANK DATA RECORDS (Skip if microchip-only visit)
    # --------------------------------------------------------------------------
    if not vaccine_product or vaccine_product.lower() in ["nan", "", "nat", "none"]:
        log("ℹ️ Skipping vaccine entry: No product data specified for this record line item.")
        return page

    log("💉 Opening vaccine flow")

    # -------------------------
    # NAVIGATION
    # -------------------------
    safe_click(page, lambda: page.locator('[data-cy="medical-tab"]'), "medical")
    safe_click(page, lambda: page.locator('button[tabname="vaccines"]'), "vaccines")
    safe_click(page, lambda: page.locator('button:has-text("Complete Vaccine")'), "open vaccine modal")

    modal = page.locator('#modal-container').filter(has_text="Complete Vaccine")
    modal.wait_for(state="visible", timeout=15000)

    log(f"📅 date_vaccinated raw: {animal.get('date_vaccinated')}")
    log(f"📅 vaccination_expires raw: {animal.get('vaccination_expires')}")

    def clear_and_fill(locator, value):
        locator.click()
        locator.fill("")
        fill_livewire(locator, value)

    # -------------------------
    # DATES
    # -------------------------
    clear_and_fill(
        modal.locator('[data-cy="completed_vaccinationsdata0completed_at"]'),
        f"{normalize_date(animal.get('date_vaccinated'))} 12:00 AM"
    )

    clear_and_fill(
        modal.locator('[data-cy="completed_vaccinationsdata0next_due_at"]'),
        f"{normalize_date(animal.get('vaccination_expires'))} 12:00 AM"
    )

    clear_and_fill(
        modal.locator('[data-cy="completed_vaccinationsdata0vaccine_expiration"]'),
        normalize_date(animal.get("product_expiration_date"))
    )

    # -------------------------
    # VACCINE TYPEAHEAD (FIXED SELECTION LOGIC)
    # -------------------------
    vaccine_value = vaccine_product.lower()

    vaccine_box = modal.locator('[data-cy="completed_vaccinations.data.0.vaccine_id"]')

    vaccine_box.click()
    page.wait_for_timeout(200)

    page.keyboard.type(vaccine_product, delay=60)
    page.wait_for_timeout(600)

    options = page.locator("div[role='option'], li[role='option']")

    best_match = None
    fallback_match = None

    for i in range(options.count()):
        text = options.nth(i).inner_text().strip()
        norm = text.lower().replace(".", "")

        # EXACT logical match (no punctuation noise)
        if norm == vaccine_value:
            best_match = options.nth(i)
            break

        # partial fallback (base name match)
        if vaccine_value in norm:
            fallback_match = options.nth(i)

    if best_match:
        best_match.click()
        log(f"🧬 Selected exact match: {best_match.inner_text().strip()}")

    elif fallback_match:
        fallback_match.click()
        log(f"🧬 Selected fallback match: {fallback_match.inner_text().strip()}")

    else:
        log("⚠️ No matching vaccine found — selecting first option as fallback")
        if options.count() > 0:
            options.first.click()

    # -------------------------
    # OTHER FIELDS (NOW USING SANITIZED INT STRINGS)
    # -------------------------
    tag_str = clean_int_string(animal.get("rabies_tag_number"))
    lot_str = clean_int_string(animal.get("lot_number"))

    fill_livewire(
        modal.locator('[data-cy="completed_vaccinations.data.0.rabies_tag_number"]'),
        tag_str
    )

    fill_livewire(
        modal.locator('[data-cy="completed_vaccinations.data.0.vaccine_lot_number"]'),
        lot_str
    )

    fill_livewire(
        modal.locator('[data-cy="completed_vaccinations.data.0.vaccinated_by"]'),
        animal.get("vaccinated_by_name")
    )

    # -------------------------
    # STAFF SELECTION
    # -------------------------
    staff = modal.locator('[data-cy="completed_vaccinations.data.0.staff_id"]')

    vet = safe(animal.get("supervising_veterinarian")).lower()
    selected = False

    for i in range(staff.locator("option").count()):
        opt = staff.locator("option").nth(i)
        label = opt.inner_text().strip()

        if vet and vet in label.lower():
            staff.select_option(label=label)
            selected = True
            break

    if not selected:
        staff.select_option(label="Community Veterinarian")

    # -------------------------
    # SUBMIT
    # -------------------------
    save_btn = modal.locator('button[data-cy="modal-save"]')
    save_btn.wait_for(state="visible", timeout=15000)
    save_btn.click(force=True)

    page.wait_for_timeout(1200)

    log("✅ Vaccine completed")

    return page