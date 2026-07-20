# ==============================================================================
# People Module (MULTI-POINT COLLISION DEDUPLICATION ENGINE - 2026)
# ==============================================================================

def safe(v):
    return "" if v is None else str(v)


def clean_numeric_string(value):
    """
    Safely handles numbers from Excel data sources, ensuring zip codes,
    phones, and tags drop trailing '.0' values without string conversion failure.
    """
    raw_val = safe(value).strip()
    if not raw_val or raw_val.lower() in ["nan", "none"]:
        return ""
    try:
        return str(int(float(raw_val)))
    except ValueError:
        return raw_val.split('.')[0]


def normalize_comparison_string(value):
    """
    Strips out casing, whitespace, and punctuation noise (dots, commas, hyphens, 
    parentheses) to guarantee accurate structural comparisons.
    """
    val_str = safe(value).lower()
    for char in [" ", "-", "(", ")", ",", ".", "\n", "\t"]:
        val_str = val_str.replace(char, "")
    return val_str.strip()


def find_person(page, first, last, data, log):
    """
    Searches for a person and reconciles their identity using name plus a 
    multi-attribute validation check (Address OR Phone OR Email). Prevents
    false duplicate merges on identical common names.
    """
    first_clean = safe(first).strip()
    last_clean = safe(last).strip()
    search_query = f"{first_clean} {last_clean}".strip()
    target_name_lower = search_query.lower()
    
    # 1. Normalize our incoming target verification values
    target_address = normalize_comparison_string(data.get("address"))
    target_phone = normalize_comparison_string(data.get("phone"))
    target_email = normalize_comparison_string(data.get("email"))

    log(f"🔍 Identity Verification: Scanning system for: '{search_query}'")
    
    search_bar = page.locator('input[placeholder*="Search by name"]')
    search_bar.wait_for(state="visible", timeout=10000)
    search_bar.click()
    search_bar.fill(search_query)
    page.keyboard.press("Enter")
    
    # Wait for the search grid update to settle completely
    page.wait_for_timeout(1500)

    # 2. Locate all container blocks representing database search result rows
    row_locator = page.locator('[data-cy^="people-table-row-"]')
    count = row_locator.count()
    
    for i in range(count):
        row = row_locator.nth(i)
        try:
            # Locate the explicit name link wrapper inside this specific row context
            link = row.locator("a.link.font-bold")
            if not link.count() or link.inner_text().strip().lower() != target_name_lower:
                continue  # Name doesn't match perfectly, bypass row immediately.

            # Name matches perfectly. Fetch the raw textual block content of this individual row.
            row_text = normalize_comparison_string(row.inner_text())
            
            # Evaluate conditional matching flags
            address_matched = target_address and (target_address in row_text)
            phone_matched = target_phone and (target_phone in row_text)
            email_matched = target_email and (target_email in row_text)

            # 3. Apply validation guard rule: Name AND (Address OR Phone OR Email)
            if address_matched or phone_matched or email_matched:

                profile_url = link.get_attribute("href")

                changes = {
                    "address": (
                        target_address != "" and
                        not address_matched
                    ),

                    "phone": (
                        target_phone != "" and
                        not phone_matched
                    ),

                    "email": (
                        target_email != "" and
                        not email_matched
                    )
                }

                needs_update = any(changes.values())

                log(
                    f"🎯 Identity confirmed. "
                    f"Updates required: {changes}"
                )

                return {
                    "profile_url": profile_url,
                    "needs_update": needs_update,
                    "changes": changes
                }
            else:
                log(f"⚠️ Common-Name Collision Detected: A row matches '{search_query}' but contact metadata points differ. Evaluating next result...")
        except Exception as e:
            continue

    log("ℹ️ Identity check complete. No matching profile exists in system indices.")
    return None


# ==============================================================================
# MODAL STABILITY HELPERS
# ==============================================================================

def wait_for_modal_stable(page):
    """
    Ensures Livewire has finished re-rendering and modal is not mid-destroy/recreate cycle.
    """
    page.wait_for_function("""
        () => {
            const modal = document.querySelector('#modal-container');
            const input = document.querySelector('[data-cy="first_name"]');

            return modal &&
                   input &&
                   document.visibilityState === 'visible' &&
                   modal.offsetParent !== null;
        }
    """, timeout=10000)

    page.wait_for_timeout(600)


# ==============================================================================
# OPEN MODAL
# ==============================================================================

def open_add_person_modal(page, safe_click, log):
    log("➕ Target record missing. Opening Add Person modal template...")

    btn = page.locator('[data-cy="openAddPersonModalBtn"]')
    btn.wait_for(state="visible", timeout=10000)
    btn.click()

    page.wait_for_selector("#modal-container", state="attached", timeout=10000)
    wait_for_modal_stable(page)
    page.wait_for_selector('[data-cy="first_name"]', state="visible", timeout=10000)

    log("🧩 Modal stable and ready")


# ==============================================================================
# FORM FILLING
# ==============================================================================

def fill_add_person_modal(page, data, log):
    log("✍️ Filling Add Person form fields...")

    wait_for_modal_stable(page)

    first = data.get("person_first_name", "") or ""
    last = data.get("person_last_name", "") or ""

    page.locator('[data-cy="first_name"]').fill(safe(first).strip())
    page.locator('[data-cy="last_name"]').fill(safe(last).strip())
    page.wait_for_timeout(300)

    page.locator('[data-cy="address_1"]').fill(safe(data.get("address")).strip())
    page.locator('[data-cy="city"]').fill(safe(data.get("city")).strip())
    page.locator('[data-cy="county"]').fill(safe(data.get("county")).strip())

    state = safe(data.get("state")).strip().upper()
    if state:
        page.locator('[data-cy="state"]').select_option(state)

    clean_zip = clean_numeric_string(data.get("zip_code"))
    page.locator('[data-cy="zip"]').fill(clean_zip)

    email = safe(data.get("email")).strip()
    phone = clean_numeric_string(data.get("phone"))

    if email:
        page.locator('[data-cy="email"]').fill(email)
    else:
        cb = page.locator('#emailRefused-input')
        if cb.count() and not cb.is_checked():
            cb.check()

    page.wait_for_timeout(200)

    if phone:
        page.locator('[data-cy="primary_phone.number"]').fill(phone)
        page.locator('[data-cy="primary_phone.subtype"]').select_option("Cell")
    else:
        cb = page.locator('#phoneRefused-input')
        if cb.count() and not cb.is_checked():
            cb.check()

    page.wait_for_timeout(600)
    log("✅ Form completely filled.")


# ==============================================================================
# SUBMIT
# ==============================================================================

def submit_add_person(page, log):
    log("🚀 Submitting Add Person form parameters...")

    btn = page.locator('[data-cy="addPersonSubmitBtn"]')
    btn.wait_for(state="visible", timeout=10000)
    btn.click()

    page.wait_for_selector("#modal-container", state="hidden", timeout=20000)

    page.wait_for_function("""
        () => {
            return document.querySelector('[data-cy="associated-animal"]')
                || window.location.href.includes('/person')
                || window.location.href.includes('/people')
        }
    """, timeout=20000)

    log("🎉 Person created successfully and page stabilized.")


# ==============================================================================
# HIGH LEVEL FLOW
# ==============================================================================

def create_person_if_missing(page, safe_click, log, data):
    open_add_person_modal(page, safe_click, log)
    fill_add_person_modal(page, data, log)
    submit_add_person(page, log)