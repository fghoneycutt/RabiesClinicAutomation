# ==============================================================================
# Person Update Module (PROFILE RECONCILIATION ENGINE - 2026)
#
# Handles updating existing Shelterluv person profiles when:
#   - Name matches
#   - Identity verification succeeds
#   - Incoming data contains newer/different contact information
#
# ==============================================================================


def safe(v):
    return "" if v is None else str(v)


def clean_numeric_string(value):
    """
    Safely handles Excel-style numeric values.
    Prevents zip codes / phone numbers becoming 12345.0
    """
    raw_val = safe(value).strip()

    if not raw_val:
        return ""

    if raw_val.lower() in ["nan", "none"]:
        return ""

    try:
        return str(int(float(raw_val)))
    except ValueError:
        return raw_val

def fill_reactive(locator, value):
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


# ==============================================================================
# MAIN ENTRY
# ==============================================================================

def update_person_profile(
    page,
    data,
    changes,
    log
):
    """
    Reconciles an existing Shelterluv person profile.

    changes example:

    {
        "address": True,
        "phone": False,
        "email": True
    }

    """

    log("🔄 Beginning person profile reconciliation...")


    if changes.get("address"):
        update_address(
            page,
            data,
            log
        )


    if changes.get("phone"):
        update_phone(
            page,
            data,
            log
        )


    if changes.get("email"):
        update_email(
            page,
            data,
            log
        )


    log(
        "✅ Person profile reconciliation complete."
    )



# ==============================================================================
# ADDRESS UPDATE
# ==============================================================================

def update_address(
    page,
    data,
    log
):
    """
    Opens Shelterluv Edit Address modal and replaces
    existing address information with incoming data.
    """

    log("📍 Address difference detected. Updating address...")


    # --------------------------------------------------------------------------
    # OPEN ADDRESS MODAL
    # --------------------------------------------------------------------------

    address_button = page.locator(
        'button[wire\\:click="editAddress"]'
    )

    address_button.wait_for(
        state="visible",
        timeout=10000
    )

    address_button.click()


    # --------------------------------------------------------------------------
    # WAIT FOR MODAL
    # --------------------------------------------------------------------------

    page.wait_for_selector(
        '[data-cy="line_1"]',
        state="visible",
        timeout=10000
    )


    # --------------------------------------------------------------------------
    # FILL ADDRESS COMPONENTS
    # --------------------------------------------------------------------------

    street = safe(
        data.get("address")
    ).strip()

    city = safe(
        data.get("city")
    ).strip()

    county = safe(
        data.get("county")
    ).strip()

    state = safe(
        data.get("state")
    ).strip().upper()

    zip_code = clean_numeric_string(
        data.get("zip_code")
    )


    if street:
        fill_reactive(
            page.locator('[data-cy="line_1"]'),
            street
        )


    if county:
        page.locator(
            '[data-cy="county"]'
        ).fill(county)


    if city:
        page.locator(
            '[data-cy="city"]'
        ).fill(city)


    if state:
        page.locator(
            '[data-cy="state"]'
        ).select_option(state)


    if zip_code:
        page.locator(
            '[data-cy="zip"]'
        ).fill(zip_code)


    log(
        f"✍️ Address prepared: {street}, {city}, {state} {zip_code}"
    )


    # --------------------------------------------------------------------------
    # SAVE
    # --------------------------------------------------------------------------
    page.wait_for_timeout(1000)

    save_button = page.locator(
        '[data-cy="modal-save"]'
    )

    save_button.wait_for(
        state="visible",
        timeout=10000
    )

    save_button.click()


    page.wait_for_timeout(1500)


    log(
        "✅ Address successfully updated."
    )



# ==============================================================================
# PHONE UPDATE
# ==============================================================================

def update_phone(
    page,
    data,
    log
):
    """
    Opens Shelterluv Edit Phone modal and replaces
    existing phone number with incoming data.

    Always sets phone type to Cell.
    """

    log("📞 Phone difference detected. Updating phone...")


    # --------------------------------------------------------------------------
    # OPEN PHONE MODAL
    # --------------------------------------------------------------------------

    phone_button = page.locator(
        'button[wire\\:click="editPhone"]'
    )

    phone_button.wait_for(
        state="visible",
        timeout=10000
    )

    phone_button.click()


    # --------------------------------------------------------------------------
    # WAIT FOR PHONE MODAL
    # --------------------------------------------------------------------------

    page.wait_for_selector(
        '[data-cy="primary_number"]',
        state="visible",
        timeout=10000
    )


    # --------------------------------------------------------------------------
    # FORMAT PHONE
    # --------------------------------------------------------------------------

    raw_phone = safe(
        data.get("phone")
    )

    phone_digits = (
        raw_phone
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "")
        .strip()
    )


    if not phone_digits:
        log(
            "⚠️ No phone value supplied. Skipping phone update."
        )
        return


    # --------------------------------------------------------------------------
    # FILL PHONE NUMBER
    # --------------------------------------------------------------------------

    page.locator(
        '[data-cy="primary_number"]'
    ).fill(phone_digits)


    # --------------------------------------------------------------------------
    # ALWAYS SET CELL
    # --------------------------------------------------------------------------

    page.locator(
        '[data-cy="primary_type"]'
    ).select_option("Cell")


    log(
        f"✍️ Phone prepared: {phone_digits}"
    )


    # --------------------------------------------------------------------------
    # SAVE
    # --------------------------------------------------------------------------

    save_button = page.locator(
        '[data-cy="modal-save"]'
    )

    save_button.wait_for(
        state="visible",
        timeout=10000
    )

    save_button.click()


    page.wait_for_timeout(1500)


    log(
        "✅ Phone successfully updated."
    )


# ==============================================================================
# EMAIL UPDATE
# ==============================================================================

def update_email(
    page,
    data,
    log
):
    """
    Opens Shelterluv Edit Email modal and replaces
    existing email address with incoming data.
    """

    log("📧 Email difference detected. Updating email...")


    # --------------------------------------------------------------------------
    # OPEN EMAIL MODAL
    # --------------------------------------------------------------------------

    email_button = page.locator(
        'button[wire\\:click="editEmail"]'
    )

    email_button.wait_for(
        state="visible",
        timeout=10000
    )

    email_button.click()


    # --------------------------------------------------------------------------
    # WAIT FOR EMAIL MODAL
    # --------------------------------------------------------------------------

    page.wait_for_selector(
        '[data-cy="email"]',
        state="visible",
        timeout=10000
    )


    # --------------------------------------------------------------------------
    # FILL EMAIL
    # --------------------------------------------------------------------------

    email = safe(
        data.get("email")
    ).strip()


    if not email:
        log(
            "⚠️ No email value supplied. Skipping email update."
        )
        return


    page.locator(
        '[data-cy="email"]'
    ).fill(email)


    log(
        f"✍️ Email prepared: {email}"
    )


    # --------------------------------------------------------------------------
    # SAVE
    # --------------------------------------------------------------------------

    save_button = page.locator(
        '[data-cy="modal-save"]'
    )

    save_button.wait_for(
        state="visible",
        timeout=10000
    )

    save_button.click()


    page.wait_for_timeout(1500)


    log(
        "✅ Email successfully updated."
    )