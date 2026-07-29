# ==============================================================================
# Microchip Module - Existing Animal Reconciliation
# Supports:
# - Existing chip detection
# - Non-Fi manufacturers
# - Add Microchip modal workflow
# ==============================================================================

def safe(v):
    if v is None:
        return ""
    return str(v).strip()


# ------------------------------------------------------------------------------
# NORMALIZE MICROCHIP NUMBER
# ------------------------------------------------------------------------------
def normalize_microchip(value):
    if not value:
        return ""

    raw = str(value).strip()

    if raw.lower() in ["nan", "", "none"]:
        return ""

    try:
        return str(int(float(raw)))
    except Exception:
        return raw.split(".")[0]


# ------------------------------------------------------------------------------
# FIND EXISTING MICROCHIP
# ------------------------------------------------------------------------------
def get_existing_microchip(page, log):

    try:
        chip_buttons = page.locator(
            'button.inline-editable'
        )

        for i in range(chip_buttons.count()):
            text = chip_buttons.nth(i).inner_text().strip()

            digits = "".join(
                c for c in text
                if c.isdigit()
            )

            # Microchips are typically 9-15 digits
            if len(digits) >= 9:
                log(
                    f"🔍 Existing Shelterluv microchip detected: {digits}"
                )
                return digits

    except Exception as e:
        log(
            f"⚠️ Existing microchip lookup failed: {str(e)}"
        )

    return ""


# ------------------------------------------------------------------------------
# ADD MICROCHIP MODAL
# ------------------------------------------------------------------------------
def add_microchip_modal(
    page,
    animal,
    normalize_date,
    log
):

    microchip = normalize_microchip(
        animal.get("microchip_number")
    )

    if not microchip:
        return False


    log(
        f"🔬 Opening Add Microchip modal for {microchip}"
    )


    # ----------------------------------------------------------
    # OPEN MODAL
    # ----------------------------------------------------------

    add_button = page.locator(
        '[data-cy="addMicrochip"]'
    )

    add_button.wait_for(
        state="visible",
        timeout=10000
    )

    add_button.click(
        force=True
    )


    modal = page.locator(
        "#modal-container"
    )

    modal.wait_for(
        state="visible",
        timeout=15000
    )


    # ----------------------------------------------------------
    # SELECT ISSUER
    # ----------------------------------------------------------

    issuer_value = safe(
        animal.get("microchip_issuer")
    )


    issuer = modal.locator(
        '[data-cy="form.issuer"]'
    )

    issuer.wait_for(
        state="visible",
        timeout=10000
    )


    selected = False


    if issuer_value:

        options = issuer.locator("option")

        for i in range(options.count()):

            label = safe(
                options.nth(i).inner_text()
            )

            if label.lower() == issuer_value.lower():

                issuer.select_option(
                    label=label
                )

                selected = True

                log(
                    f"🧬 Selected microchip issuer: {label}"
                )

                break


    if not selected:

        log(
            "⚠️ Microchip issuer not found. Selecting Other."
        )

        try:
            issuer.select_option(
                label="Other"
            )
        except:
            pass



    # ----------------------------------------------------------
    # MICROCHIP NUMBER
    # ----------------------------------------------------------

    number_input = modal.locator(
        '[data-cy="form.number"]'
    )

    number_input.wait_for(
        state="visible",
        timeout=10000
    )

    number_input.fill(
        microchip
    )

    number_input.blur()



    # ----------------------------------------------------------
    # IMPLANT DATE
    # ----------------------------------------------------------

    implant_date = normalize_date(
        animal.get("date_vaccinated")
    )


    date_input = modal.locator(
        '[data-cy="forminserted_at"]'
    )

    if date_input.count():

        date_input.fill(
            implant_date
        )

        date_input.blur()


    log(
        f"📅 Implant date entered: {implant_date}"
    )


    # ----------------------------------------------------------
    # SAVE
    # ----------------------------------------------------------

    save_btn = modal.locator(
        'button[data-cy="modal-save"]'
    )

    save_btn.wait_for(
        state="visible",
        timeout=15000
    )

    page.wait_for_timeout(
        500
    )

    save_btn.click(
        force=True
    )


    modal.wait_for(
        state="hidden",
        timeout=15000
    )


    log(
        "✅ Microchip successfully added to existing animal"
    )

    return True



# ------------------------------------------------------------------------------
# MAIN ENTRY
# ------------------------------------------------------------------------------
def add_microchip_if_needed(
    page,
    animal,
    safe_click,
    fill_livewire,
    normalize_date,
    log
):

    target_chip = normalize_microchip(
        animal.get("microchip_number")
    )


    # No chip in incoming data
    if not target_chip:

        log(
            "ℹ️ No microchip provided. Skipping."
        )

        return False



    existing_chip = get_existing_microchip(
        page,
        log
    )


    # ----------------------------------------------------------
    # EXISTING CHIP MATCH
    # ----------------------------------------------------------

    if existing_chip:

        if existing_chip == target_chip:

            log(
                "✅ Existing microchip matches input. No update needed."
            )

            return False


        log(
            f"⚠️ Microchip mismatch. Existing={existing_chip}, Incoming={target_chip}"
        )

        # Future reconciliation update path
        return True



    # ----------------------------------------------------------
    # NO CHIP EXISTS
    # ----------------------------------------------------------

    log(
        "🔍 No existing microchip found. Checking Add Microchip button."
    )


    if page.locator(
        '[data-cy="addMicrochip"]'
    ).count():

        add_microchip_modal(
            page,
            animal,
            normalize_date,
            log
        )

        return True


    log(
        "⚠️ No existing chip and Add Microchip button unavailable."
    )

    return False