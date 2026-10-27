# ==============================================================================
# Shelterluv Rabies Certificate Email
# Selects and emails the most recent rabies certificate for an animal.
# ==============================================================================

import re
from datetime import datetime
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def email_latest_rabies_certificate(page, email, log=print):
    """
    Opens the Files tab, finds the most recent Rabies Certificate,
    selects it, and emails it to the supplied address.

    Returns:
        True  - email workflow completed
        False - no email, no certificate, or email was rejected
    """

    # --------------------------------------------------------------------------
    # VALIDATE EMAIL
    # --------------------------------------------------------------------------
    email = str(email or "").strip()

    if not email or email.lower() in ("nan", "none", "nat"):
        log("ℹ️ No owner email provided. Skipping certificate email.")
        return False

    # --------------------------------------------------------------------------
    # OPEN FILES TAB
    # --------------------------------------------------------------------------
    log("📂 Opening animal Files tab...")

    files_tab = page.locator('[data-cy="files-tab"]')
    files_tab.wait_for(state="visible", timeout=15000)
    files_tab.click()

    page.wait_for_timeout(800)

    # --------------------------------------------------------------------------
    # FIND ALL RABIES CERTIFICATES AND THEIR DATES
    # --------------------------------------------------------------------------
    certificate_links = page.locator(
        'a[href*="/animals/documents/rabies-certificate"]'
    )

    candidates = []

    for i in range(certificate_links.count()):
        link = certificate_links.nth(i)

        try:
            title = link.inner_text().strip()

            match = re.search(
                r"Rabies Certificate.*?(\d{1,2}/\d{1,2}/\d{4})",
                title,
                re.IGNORECASE
            )

            if not match:
                log(f"⚠️ Could not read certificate date: {title}")
                continue

            certificate_date = datetime.strptime(
                match.group(1),
                "%m/%d/%Y"
            )

            # Find the enclosing row containing this certificate link.
            row = link.locator(
                'xpath=ancestor::div[contains(@class, "grid-cols-10")][1]'
            )

            checkbox = row.locator('input[type="checkbox"]')

            if checkbox.count() == 0:
                log(f"⚠️ No checkbox found for: {title}")
                continue

            candidates.append({
                "date": certificate_date,
                "title": title,
                "checkbox": checkbox
            })

        except Exception as err:
            log(f"⚠️ Error inspecting certificate row: {err}")

    if not candidates:
        log("⚠️ No dated Rabies Certificate was found. Skipping email.")
        return False

    # --------------------------------------------------------------------------
    # SELECT THE MOST RECENT CERTIFICATE
    # --------------------------------------------------------------------------
    latest = max(candidates, key=lambda item: item["date"])

    log(f"📄 Most recent certificate: {latest['title']}")

    # Ensure only the newest Rabies Certificate is selected.
    for candidate in candidates:
        checkbox = candidate["checkbox"]

        if checkbox.is_checked():
            checkbox.uncheck()

    latest["checkbox"].check()

    # --------------------------------------------------------------------------
    # CLICK EMAIL SELECTED
    # --------------------------------------------------------------------------
    email_button = page.locator(
        'button[data-cy="secondary-button"]'
    ).filter(has_text="Email Selected")

    email_button.wait_for(state="visible", timeout=10000)

    # Wait until the selected-file action is enabled.
    page.wait_for_function(
        """() => {
            const buttons = Array.from(
                document.querySelectorAll(
                    'button[data-cy="secondary-button"]'
                )
            );

            const button = buttons.find(
                el => el.innerText.includes("Email Selected")
            );

            return button && !button.disabled;
        }""",
        timeout=10000
    )

    email_button.click()

    # --------------------------------------------------------------------------
    # ENTER OWNER EMAIL
    # --------------------------------------------------------------------------
    email_input = page.locator('input[data-cy="email"]')
    email_input.wait_for(state="visible", timeout=10000)
    email_input.fill(email)

    # --------------------------------------------------------------------------
    # SEND CERTIFICATE AND HANDLE EMAIL VALIDATION ERRORS
    # --------------------------------------------------------------------------
    send_button = page.locator('button[data-cy="modal-save"]')
    send_button.wait_for(state="visible", timeout=10000)
    send_button.click()

    email_error = page.locator("#email-error")

    try:
        # Give Shelterluv time to display its validation message.
        email_error.wait_for(state="visible", timeout=2500)

    except PlaywrightTimeoutError:
        # No email validation message appeared.
        # Require the dialog to close; if it stays open, let the failure
        # surface rather than incorrectly reporting a successful send.
        email_input.wait_for(state="hidden", timeout=15000)

        log(f"📧 Certificate email submitted for {email}")
        return True

    # The email was rejected by Shelterluv.
    error_text = email_error.inner_text().strip()

    log(f"⚠️ Shelterluv rejected email '{email}': {error_text}")
    log("➡️ Cancelling certificate email and continuing automation.")

    cancel_button = page.locator('button[data-cy="modal-cancel"]')
    cancel_button.wait_for(state="visible", timeout=5000)
    cancel_button.click()

    email_input.wait_for(state="hidden", timeout=10000)

    log("↩️ Certificate email cancelled. Continuing with remaining automation.")
    return False
