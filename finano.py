# ==============================================================================
# Fi Nano Registration Module - Production System Integration Layer (UPDATED)
# ==============================================================================

import os
import time
from playwright.sync_api import sync_playwright
from breed_mapping import translate_breed  # External breed translation matrix

FI_STORAGE_STATE_PATH = "fi_nano_storage.json"

def log(msg):
    print(f"🌐 [Fi Nano System] {msg}")

def safe_str(val):
    """
    Guarantees any input data type is cleanly stripped and converted to a string
    to satisfy strict Playwright locator requirements.
    """
    if val is None or str(val).strip().lower() in ["nan", "none", ""]:
        return ""
    val_str = str(val).strip()
    if val_str.endswith('.0') and val_str[:-2].isdigit():
        return val_str[:-2]
    return val_str

def fill_and_blur(page, selector, value):
    clean_val = safe_str(value)
    if not clean_val:
        return
    element = page.locator(selector)
    element.wait_for(state="visible", timeout=10000)
    element.click()
    element.fill(clean_val)
    element.blur()
    page.wait_for_timeout(150)

# ------------------------------------------------------------------------------
# CALCULATE BIRTHDAY DROPDOWN SELECTIONS
# ------------------------------------------------------------------------------
def calculate_birth_year_and_month(age_years, age_months):
    try:
        current_year = 2026
        
        years_to_subtract = int(float(age_years)) if age_years else 0
        months_to_subtract = int(float(age_months)) if age_months else 0
        
        target_month = 1  # Default fallback to January
        target_year = current_year - years_to_subtract
        
        if months_to_subtract > 0:
            target_month = 12 - (months_to_subtract % 12)
            target_year -= (1 + (months_to_subtract // 12))
            
        return str(target_year), str(target_month)
    except Exception:
        return "2025", "1"

# ------------------------------------------------------------------------------
# CORE AUTOMATION FLOW
# ------------------------------------------------------------------------------
def register_single_pet(page, animal):
    """
    Executes form filling pipeline for a unique registration row on Fi Nano.
    Defends against non-registered microchips gracefully by closing the active tab context.
    """
    chip_id = safe_str(animal.get("microchip_number"))
    is_cat = safe_str(animal.get("species")).lower() == "cat"
    log(f"🔬 Querying chip ID tracker grid for: {chip_id}")
    
    # Step 1: Query the central search system table
    page.goto("https://nano.fitracking.com/vet/chips")
    page.wait_for_load_state("domcontentloaded")
    
    search_input = page.locator('input[name="search"]')
    search_input.wait_for(state="visible", timeout=10000)
    search_input.fill(chip_id)
    page.wait_for_timeout(1000)  # Give autocomplete and layout response ample room to resolve
    
    # --- NON-REGISTERED CHIP DETECTION GUARD ---
    empty_state_selector = 'section[class*="_emptyChipList_"], h2:has-text("No results found")'
    empty_state = page.locator(empty_state_selector)
    
    if empty_state.count() > 0 and empty_state.is_visible():
        log(f"🛑 [GUARD INTERCEPT] Microchip {chip_id} is not registered with Fi Nano organization pool. Closing tab context early.")
        try:
            page.close()
        except Exception as ce:
            log(f"⚠️ Warning encountered during early tab termination sequence: {str(ce)}")
        return  # Drop out cleanly.

    # Locate table row matching the chip string and click it
    matching_cell = page.locator(f"div:text('{chip_id}'), span:text('{chip_id}')").first
    try:
        matching_cell.wait_for(state="visible", timeout=5000)
        matching_cell.click()
    except Exception:
        log(f"⚠️ Could not resolve target selection row or empty state for {chip_id}. Terminating loop tab window.")
        try:
            page.close()
        except Exception:
            pass
        return
    
    # Step 2: Clear the "Continue" gate bridge intercept page
    log("Passing security landing verification stage...")
    continue_btn_1 = page.locator('button[type="submit"]:has-text("Continue")')
    continue_btn_1.wait_for(state="visible", timeout=10000)
    continue_btn_1.click()
    
    # Step 3: Populate Pet Specific Values Form View
    log(f"Filling pet metadata attributes for {animal.get('animal_name')}...")
    fill_and_blur(page, 'input[name="name"]', animal.get("animal_name"))
    
    # Select Gender Radio Group Element
    gender_label = "Female" if safe_str(animal.get("sex")).lower() == "female" else "Male"
    page.locator(f"span._radioText_4fvis_41:text-is('{gender_label}')").click()
    
    # Optional Color Mapping Selection
    fill_and_blur(page, 'input[name="color"]', animal.get("primary_color"))
    
    # Select Species Radio Group Element
    species_label = "Cat" if is_cat else "Dog"
    page.locator(f"span._radioText_4fvis_41:text-is('{species_label}')").click()
    
    # --- CONDITIONALLY HANDLE BREED SELECTION PIPELINE ---
    if is_cat:
        log("🐈 Species identified as Cat. Bypassing breed field assignment tracking completely.")
    else:
        # Determine Mixed vs Purebred radio buttons state variables
        breed_status = "Mixed" if safe_str(animal.get("secondary_breed")) else "Purebred"
        page.locator(f"span._radioText_4fvis_41:text-is('{breed_status}')").click()

        # Custom Breed Translation & Selection
        raw_shelterluv_breed = safe_str(animal.get("primary_breed"))
        target_fi_breed = translate_breed(raw_shelterluv_breed)
        log(f"🧬 Translating breed matrix: '{raw_shelterluv_breed}' maps to Fi Nano target: '{target_fi_breed}'")

        # Click custom trigger component element to show breed modal dialogue screen
        breed_trigger = page.locator('button:has-text("Breed")')
        breed_trigger.wait_for(state="visible", timeout=5000)
        breed_trigger.click()

        # Enter matched target variant sequence directly into active search filtering box inside overlay view
        breed_search = page.locator('div[class*="modal"] input, input[placeholder*="Search"], input[type="text"]').last
        breed_search.wait_for(state="visible", timeout=5000)
        breed_search.fill(target_fi_breed)
        page.wait_for_timeout(400)

        # Pick targeted exact list line matching text label variables inside DOM hierarchy elements 
        breed_option = page.locator(f"li._modalListItem_1389p_79:text-is('{target_fi_breed}')").first
        breed_option.wait_for(state="visible", timeout=5000)
        breed_option.click()
        page.wait_for_timeout(200)
    
    # Handle Dropdown Birthday Calculations Selectors
    birth_year, birth_month = calculate_birth_year_and_month(animal.get("age_years"), animal.get("age_months"))
    page.locator('select[aria-label="Birth year"]').select_option(value=birth_year)
    page.locator('select[aria-label="Birth month"]').select_option(value=birth_month)
    
    # Proceed to Contact Form Layer
    log("Advancing to contact data bindings view...")
    page.locator('button[type="submit"]:has-text("Continue")').click()
    
    # Step 4: Populate Owner Profile Values Form View
    log(f"Mapping contact details for {animal.get('person_first_name')} {animal.get('person_last_name')}...")
    fill_and_blur(page, 'input[name="firstName"]', animal.get("person_first_name"))
    fill_and_blur(page, 'input[name="lastName"]', animal.get("person_last_name"))
    fill_and_blur(page, 'input[name="primaryPhone"]', animal.get("phone"))
    
    email_val = safe_str(animal.get("email")) if safe_str(animal.get("email")) else "none@none.com"
    fill_and_blur(page, 'input[name="primaryEmail"]', email_val)
    
    fill_and_blur(page, 'input[name="line1"]', animal.get("address"))
    fill_and_blur(page, 'input[name="city"]', animal.get("city"))
    
    # Handle React-Select dropdown field element parameters
    state_input = page.locator('#react-select-2-input')
    state_input.wait_for(state="visible", timeout=5000)
    state_input.fill(safe_str(animal.get("state")))
    page.keyboard.press("Enter")
    
    fill_and_blur(page, 'input[name="zipcode"]', animal.get("zip_code"))
    
    log("🔘 Form sequence complete. Submitting final registration...")
    
    # Execute active click submission on the production environment layout
    final_continue_btn = page.locator('button[type="submit"]:has-text("Continue")')
    final_continue_btn.wait_for(state="visible", timeout=5000)
    final_continue_btn.click()
    
    page.wait_for_timeout(2500)
    log(f"✅ Microchip registration complete for tracking node: {chip_id}")

# ------------------------------------------------------------------------------
# LIFECYCLE MANAGEMENT LAYER
# ------------------------------------------------------------------------------
def get_fi_page_in_shared_context(context):
    """
    Spawns a single additional TAB inside the existing browser window context.
    """
    log("Opening new tab for Fi Nano in shared browser window...")
    fi_page = context.new_page()

    log("Navigating to partner gateway dashboard context...")
    fi_page.goto("https://nano.fitracking.com/vet/chips") 
    fi_page.wait_for_load_state("domcontentloaded")
    
    # Guard layer authentication check
    if "login" in fi_page.url or fi_page.locator('input[name="email"]').count() > 0:
        print("\n" + "="*80)
        print("   👉 MANUAL ACTION REQUIRED IN THE OPEN WINDOW 👈")
        print("   Please switch over to the Fi Nano tab, authenticate and log in.")
        print("   Once logged in, return to this terminal and press ENTER.")
        print("="*80 + "\n")
        input("Press Enter here in the terminal once your dashboard layout resolves...")
        
        try:
            context.storage_state(path="shelterluv_storage.json")
            log("💾 Shared cookie session context explicitly preserved.")
        except Exception as e:
            log(f"⚠️ Storage save notification note: {e}")
    else:
        log("🔓 Valid session state found or context inherited. Bypassing manual sign-in step.")
        
    return fi_page