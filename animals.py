# ==============================================================================
# Animals Module (UPDATED WITH SPECIFIC ALPINE INTERACTION SELECTION - 2026)
# ==============================================================================

import time


# ------------------------------------------------------------------------------
# NAME MATCHING
# ------------------------------------------------------------------------------
def animal_name_matches(existing, target):
    if not existing:
        return False

    e = existing.lower().strip()
    t = target.lower().strip()

    return e == t or t in e or e in t


# ------------------------------------------------------------------------------
# SAFE CLICK
# ------------------------------------------------------------------------------
def safe_click(locator, timeout=10000, log=None, label="element"):
    try:
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()
        return True
    except Exception as e:
        if log:
            log(f"⚠️ Click failed ({label}): {str(e)}")
        return False


# ------------------------------------------------------------------------------
# WAIT HELPERS
# ------------------------------------------------------------------------------
def wait_for_add_animal_event(page):
    page.wait_for_selector('[data-cy="add-animal-event"]', timeout=15000)


def wait_for_associated_animal(page):
    page.wait_for_selector('[data-cy="associated-animal"]', timeout=15000)


def wait_for_animal_intake(page):
    page.wait_for_selector('#animalInformation\\.animal_name', timeout=20000)
    page.wait_for_timeout(800)


# ------------------------------------------------------------------------------
# OPEN EXISTING ANIMAL
# ------------------------------------------------------------------------------
def open_animal(page, context, link_element):
    with context.expect_page() as new_page:
        link_element.click()

    animal_page = new_page.value
    animal_page.wait_for_load_state("domcontentloaded")
    animal_page.wait_for_timeout(800)
    return animal_page


# ------------------------------------------------------------------------------
# TYPEAHEAD
# ------------------------------------------------------------------------------
def select_typeahead(page, field_id, value, log=None):
    if not value or str(value).strip().lower() in ["nan", "", "none"]:
        return

    clean_value = str(value).strip()

    try:
        # 1. Scope all execution strictly within the specific wrapper element
        container = page.locator(f'[data-scroll-to="{field_id}"]')
        if container.count() == 0:
            # Fallback if field_id maps to an un-wrapped custom component context
            escaped_id = field_id.replace(".", "\\.")

            container = page.locator(
                f'div:has(> #{escaped_id}), fieldset:has(#{escaped_id})'
            ).first
            if container.count() == 0:
                container = page

        # 2. Find and click the trigger button inside this specific container
        dropdown_trigger = container.locator(f"button, [id='{field_id}']").first
        dropdown_trigger.wait_for(state="visible", timeout=10000)
        dropdown_trigger.click()
        page.wait_for_timeout(600)

        # 3. Target the search field specifically inside this container context
        search_input = container.locator('input[x-ref="searchBox"], input[type="search"]').first
        
        # Fallback to focused element if the modal/dropdown layer detaches dynamically
        if search_input.count() == 0 or not search_input.is_visible():
            search_input = page.locator('input[x-ref="searchBox"]:focus, input[type="search"]:focus').first

        if search_input.count() > 0 and search_input.is_visible():
            search_input.clear()
            search_input.fill(clean_value)
            page.wait_for_timeout(600)

        # 4. Extract options matching the clean text pattern inside the container context
        regex_pattern = f"/^\\s*{clean_value}\\s*$/i"

        option_match = container.locator(f'[role="option"] >> text={regex_pattern}').first
        if option_match.count() == 0 or not option_match.is_visible():
            option_match = container.locator(f'div >> text={regex_pattern}').first
            
        # Fallback to page level matching if Alpine opens a global portal layout layer
        if option_match.count() == 0 or not option_match.is_visible():
            option_match = page.locator(f'[role="option"] >> text={regex_pattern}').first

        # 5. Click option if explicitly visible; otherwise step select via keyboard route
        if option_match.count() > 0 and option_match.is_visible():
            option_match.click()
        else:
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(200)
            page.keyboard.press("Enter")
            
        page.wait_for_timeout(800)

    except Exception as e:
        if log:
            log(f"⚠️ Typeahead component selection fallback on {field_id} ('{clean_value}'): {str(e)}")
        try:
            page.keyboard.type(clean_value)
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(800)
        except:
            pass

# ------------------------------------------------------------------------------
# WEIGHT AND DOG SIZE
# ------------------------------------------------------------------------------
def enter_animal_weight(page, animal, log):
    raw_weight = animal.get("weight")

    # Weight is optional.
    if raw_weight is None or str(raw_weight).strip().lower() in [
        "", "nan", "none"
    ]:
        log("⚖️ No weight provided. Skipping weight entry.")
        return

    try:
        weight = float(raw_weight)

        if weight < 0 or weight > 999999:
            log(f"⚠️ Weight out of range: {raw_weight}. Skipping weight entry.")
            return

        # Enter weight.
        weight_field = page.locator(
            '#animalInformation\\.weight_amount'
        )
        weight_field.wait_for(state="visible", timeout=8000)
        weight_field.fill(str(weight))

        # Always select pounds.
        weight_units = page.locator('#unit')
        weight_units.wait_for(state="visible", timeout=8000)
        weight_units.select_option("lbs")

        log(f"⚖️ Entered animal weight: {weight:g} lbs")

    except (ValueError, TypeError):
        log(f"⚠️ Invalid weight value '{raw_weight}'. Skipping weight entry.")
        return
    except Exception as e:
        log(f"⚠️ Could not enter animal weight: {e}")
        return

    # Calculate dog size from weight, only for dogs.
    species = str(animal.get("species") or "").strip().lower()

    if species != "dog":
        return

    if weight <= 24:
        dog_size = "Small (0-24)"
    elif weight <= 59:
        dog_size = "Medium (25-59)"
    elif weight <= 99:
        dog_size = "Large (60-99)"
    else:
        dog_size = "Extra-Large (100+)"

    try:
        size_field = page.locator(
            '#animalInformation\\.dog_size_group'
        )
        size_field.wait_for(state="visible", timeout=8000)
        size_field.select_option(label=dog_size)

        log(f"🐕 Calculated dog size: {dog_size} ({weight:g} lbs)")

    except Exception as e:
        log(f"⚠️ Could not select dog size '{dog_size}': {e}")

# ------------------------------------------------------------------------------
# MAIN FIND OR CREATE FLOW
# ------------------------------------------------------------------------------
def find_or_open_animal(page, context, animal_name, log, is_new_person=False):
    log("🚀 [VERIFICATION] Running animals.py v4.2 - Strict Attribute Match Active.")
    
    if is_new_person:
        log(f"🆕 Brand new owner profile context. Skipping initial system scraping.")
    else:
        log(f"🐾 Searching for existing links matching: {animal_name}")
        links = page.locator("a[href*='/animal/']")

        for i in range(links.count()):
            a = links.nth(i)
            try:
                text = a.inner_text().strip()
            except:
                continue

            if animal_name_matches(text, animal_name):
                log(f"✅ Matched existing link: {text}. Spawning separate tab context...")
                return open_animal(page, context, a), True

    # CREATE FLOW
    log(f"➕ Initiating animal intake submission sequence for: {animal_name}")
    wait_for_add_animal_event(page)
    safe_click(page.locator('[data-cy="add-animal-event"]').first, log=log, label="Add Animal Event")

    wait_for_associated_animal(page)
    safe_click(page.locator('[data-cy="associated-animal"]').first, log=log, label="Associated Animal")

    wait_for_animal_intake(page)
    return page, False


# ------------------------------------------------------------------------------
# CORE FORM FILL
# ------------------------------------------------------------------------------
def complete_animal_form(page, animal, log):
    log("✍️ Filling animal core fields")
    wait_for_animal_intake(page)

    if animal.get("animal_name"):
        page.locator('#animalInformation\\.animal_name').fill(animal["animal_name"])
        page.wait_for_timeout(200)

    if animal.get("species"):
        select_typeahead(page, "animalInformation.species_id", animal["species"], log)
        page.wait_for_timeout(500)

    if animal.get("primary_breed"):
        log(f"🧬 Selecting primary breed: {animal['primary_breed']}")
        select_typeahead(page, "animalInformation.primary_breed_id", animal["primary_breed"], log)
        page.wait_for_timeout(1000)

    if animal.get("secondary_breed"):
        log(f"🧬 Selecting secondary breed: {animal['secondary_breed']}")
        select_typeahead(page, "animalInformation.secondary_breed_id", animal["secondary_breed"], log)
        page.wait_for_timeout(800)

    sex = (animal.get("sex") or "").lower().strip()
    if sex == "male":
        page.locator('[data-cy="animalInformation.sex-Male"]').check()
    elif sex == "female":
        page.locator('[data-cy="animalInformation.sex-Female"]').check()

    # ALTERED STATUS
    altered_status = animal.get("altered_status")

    if altered_status is not None:
        status = str(altered_status).strip().lower()

        if status in ("true", "1", "yes"):
            page.locator(
                '[data-cy="animalInformation.altered_before_arrival-Yes"]'
            ).check()
            log("✅ Altered Before Arrival: Yes")

        elif status in ("false", "0", "no"):
            page.locator(
                '[data-cy="animalInformation.altered_before_arrival-No"]'
            ).check()
            log("✅ Altered Before Arrival: No")

        else:
            log(
                f"ℹ️ Unrecognized altered_status '{altered_status}'. "
                "Leaving Unknown selected."
            )
    else:
        log("ℹ️ No altered_status provided. Leaving Unknown selected.")

    enter_animal_weight(page, animal, log)

    if animal.get("primary_color"):
        page.locator('#animalInformation\\.primary_color').select_option(animal["primary_color"])

    if animal.get("secondary_color"):
        page.locator('#animalInformation\\.secondary_color').select_option(animal["secondary_color"])

    if animal.get("pattern"):
        page.locator('#animalInformation\\.pattern').select_option(animal["pattern"])

    if animal.get("age_years") is not None and str(animal.get("age_years")) != "":
        try:
            years_val = str(int(float(animal["age_years"])))
            page.locator('#age_today_years').fill(years_val)
        except ValueError:
            pass

    if animal.get("age_months") is not None and str(animal.get("age_months")) != "":
        try:
            months_val = str(int(float(animal["age_months"])))
            page.locator('#age_today_months').fill(months_val)
        except ValueError:
            pass

    log("✅ Core fields complete")


# ------------------------------------------------------------------------------
# MICROCHIP INTAKE SUBMISSION (PATHWAY A)
# ------------------------------------------------------------------------------
def add_microchip(page, animal, log):
    raw_chip = animal.get("microchip_number")
    raw_issuer = animal.get("microchip_issuer")

    chip_str = ""
    if raw_chip and str(raw_chip).strip().lower() not in ["nan", "", "none"]:
        try:
            chip_str = str(int(float(raw_chip)))
        except ValueError:
            chip_str = str(raw_chip).strip().split(".")[0]

    issuer_name = ""
    if raw_issuer and str(raw_issuer).strip().lower() not in ["nan", "", "none"]:
        issuer_name = str(raw_issuer).strip()

    try:
        issuer = page.locator('#identifyingInformation\\.microchip_issuer')
        issuer.wait_for(state="visible", timeout=8000)

        if chip_str:

            # Default to Fi Nano if spreadsheet has no issuer
            if not issuer_name:
                issuer_name = "Fi Nano"

            log(f"🔬 Microchip found: {chip_str}. Issuer: {issuer_name}")

            try:
                issuer.select_option(label=issuer_name)
            except Exception:
                log(f"⚠️ Unknown microchip issuer '{issuer_name}'. Selecting 'Other'.")
                issuer.select_option(label="Other")

            chip_field = page.locator('#identifyingInformation\\.microchip_number')
            chip_field.wait_for(state="visible", timeout=8000)
            chip_field.fill(chip_str)
            chip_field.blur()

        else:
            log("🔬 No microchip found. Defaulting issuer to [Did Not Attempt to Scan].")
            issuer.select_option("[Did Not Attempt to Scan]")

    except Exception as e:
        log(f"⚠️ Microchip block interaction failed: {str(e)}")


# ------------------------------------------------------------------------------
# INTAKE NEW SUBMITTER LAYER (PATHWAY A)
# ------------------------------------------------------------------------------
def submit_animal(page, log):
    log("🚀 Submitting animal intake parameters")

    btn = page.locator('[data-cy="submit-form"]')
    btn.wait_for(state="visible", timeout=15000)
    btn.click()

    duplicate_alert = page.locator(
        'div[role="alert"]:has-text("This microchip number already exists on another animal record")'
    )

    microchip_error = page.locator(
        '#identifyingInformation\\.microchip_number-error'
    )

    form_anchor = page.locator('#animalInformation\\.animal_name')

    should_register_fi = True
    microchip_length_retry_used = False
    duplicate_retry_used = False

    for _ in range(100):
        # Successful submission: the animal intake form has disappeared.
        if form_anchor.count() == 0 or not form_anchor.is_visible():
            log("🎉 Animal intake submitted successfully (Form closed)")
            return should_register_fi

        # --------------------------------------------------------------
        # INVALID MICROCHIP LENGTH
        # --------------------------------------------------------------
        if (
            not microchip_length_retry_used
            and microchip_error.count() > 0
            and microchip_error.is_visible()
        ):
            error_text = microchip_error.inner_text().strip()

            if "Microchips must be 9, 10, or 15 digits" in error_text:
                log(f"⚠️ Invalid microchip number: {error_text}")
                log("➡️ Changing Microchip Issuer to [None Found].")

                issuer = page.locator(
                    '#identifyingInformation\\.microchip_issuer'
                )
                issuer.wait_for(state="visible", timeout=8000)
                issuer.select_option(label="[None Found]")

                page.wait_for_timeout(300)

                microchip_length_retry_used = True
                should_register_fi = False

                log("🚀 Retrying animal submission without a registered microchip.")
                btn.wait_for(state="visible", timeout=10000)
                btn.click()
                page.wait_for_timeout(300)
                continue

        # --------------------------------------------------------------
        # DUPLICATE MICROCHIP
        # --------------------------------------------------------------
        if (
            not duplicate_retry_used
            and duplicate_alert.count() > 0
            and duplicate_alert.is_visible()
        ):
            log("⚠️ System Collision Guard: Duplicate microchip detected.")
            log("🔘 Changing Microchip Issuer to [Did Not Attempt to Scan].")

            issuer = page.locator(
                '#identifyingInformation\\.microchip_issuer'
            )
            issuer.select_option(label="[Did Not Attempt to Scan]")
            page.wait_for_timeout(300)

            should_register_fi = False
            duplicate_retry_used = True

            log("🚀 Retrying animal submission after duplicate-microchip guard.")
            btn.wait_for(state="visible", timeout=10000)
            btn.click()
            page.wait_for_timeout(300)
            continue

        page.wait_for_timeout(200)

    # Do not silently treat a form that remains open as a successful submission.
    if form_anchor.count() > 0 and form_anchor.is_visible():
        raise TimeoutError(
            "Animal intake form remained open after submission attempts. "
            "Check Shelterluv for validation errors."
        )

    log("🎉 Animal intake finalized successfully.")
    return should_register_fi