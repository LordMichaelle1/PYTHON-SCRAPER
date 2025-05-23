from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
import time
import re
import csv

# The Capterra category URL you want to scrape
URL = "https://www.capterra.com/customer-relationship-management-software/"

# !!! IMPORTANT: USE THE CORRECT HTTPS URL FOR SELENIUM FROM YOUR BRIGHT DATA DASHBOARD !!!
# This is the one you just provided:
YOUR_BRIGHTDATA_SELENIUM_URL = "https://brd-customer-hl_9b47d1b3-zone-scraping_browser2:xwd6horlvuqf@brd.superproxy.io:9515"

def parse_rating_text(rating_text_str):
    """Parse rating text to extract average rating and review count"""
    if rating_text_str == "N/A" or not rating_text_str:
        return None, None
    match = re.search(r'([\d\.]+)\s*\((\d+)\)', rating_text_str)
    if match:
        try:
            average_rating = float(match.group(1))
            review_count = int(match.group(2))
            return average_rating, review_count
        except ValueError:
            return None, None
    else:
        try:
            average_rating = float(rating_text_str.split()[0])
            return average_rating, None
        except ValueError:
            return None, None

# TEMPORARILY DISABLED FOR DEBUGGING - Website URL extraction function
# This function is commented out to test if window/tab handling is causing CDP errors
# def extract_website_url(driver, listing_container, index):
#     """Extract website URL by clicking the 'VISIT WEBSITE' button"""
#     website_url = "N/A"
#     
#     try:
#         # Store the current window handle
#         original_window = driver.current_window_handle
#         original_window_count = len(driver.window_handles)
#         
#         # Find and click the "VISIT WEBSITE" button
#         visit_website_button = listing_container.find_element(By.CSS_SELECTOR, "button[data-testid='upgraded-product-button']")
#         print(f"  Found 'VISIT WEBSITE' button for listing {index + 1}. Clicking...")
#         
#         visit_website_button.click()
#         
#         # Wait for new window to open
#         try:
#             WebDriverWait(driver, 10).until(
#                 EC.number_of_windows_to_be(original_window_count + 1)
#             )
#             
#             # Find the new window handle
#             new_window_handle = None
#             for handle in driver.window_handles:
#                 if handle != original_window:
#                     new_window_handle = handle
#                     break
#             
#             if new_window_handle:
#                 # Switch to the new window
#                 driver.switch_to.window(new_window_handle)
#                 
#                 # Get the URL of the new window
#                 website_url = driver.current_url
#                 print(f"  Captured website URL: {website_url}")
#                 
#                 # Close the new window
#                 driver.close()
#                 
#                 # Switch back to the original window
#                 driver.switch_to.window(original_window)
#                 
#                 # Brief pause to ensure context is stable
#                 time.sleep(1)
#             else:
#                 print(f"  Could not find new window handle for listing {index + 1}")
#                 
#         except TimeoutException:
#             print(f"  New window did not open within timeout for listing {index + 1}")
#             # Ensure we're back on the original window
#             driver.switch_to.window(original_window)
#             
#     except NoSuchElementException:
#         print(f"  'VISIT WEBSITE' button not found for listing {index + 1}")
#     except Exception as e:
#         print(f"  Error extracting website URL for listing {index + 1}: {e}")
#         # Ensure we're back on the original window in case of any error
#         try:
#             driver.switch_to.window(original_window)
#         except:
#             pass
#     
#     return website_url

def process_page_listings(driver, wait, product_container_selector):
    """Process all product listings on the current page"""
    print("Attempting to find product listings on current page...")
    
    try:
        product_listings = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_container_selector)))
    except TimeoutException:
        print("No product listings found on this page or timeout occurred.")
        return []

    if not product_listings:
        print("No product listings found. Check the selector or page content.")
        return []
    
    print(f"Found {len(product_listings)} product listings on this page.")
    print("-" * 30)

    page_data = []

    for index, listing_container in enumerate(product_listings):
        print(f"Processing listing {index + 1}...")
        company_name = "N/A"
        star_rating_raw_text = "N/A"
        average_rating = None
        review_count = None
        website_url = "N/A"

        # Extract company name
        name_found = False
        try:
            company_name_element = listing_container.find_element(By.CSS_SELECTOR, "h2[data-testid^='product-header-upgraded-link-']")
            company_name = company_name_element.text.strip()
            name_found = True
        except Exception:
            try:
                company_name_element = listing_container.find_element(By.CSS_SELECTOR, "h2[data-testid^='product-header-profile-link-']")
                company_name = company_name_element.text.strip()
                name_found = True
            except Exception:
                try:
                    company_name_element = listing_container.find_element(By.CSS_SELECTOR, "a[data-testid^='product-header-']")
                    company_name = company_name_element.text.strip()
                    if company_name:
                         name_found = True
                except Exception:
                    print(f"  Could not find company name for listing {index + 1} using known patterns.")

        # Clean up company name
        if "outbound" in company_name.lower() and '\n' in company_name:
            company_name = company_name.split('\n')[0].strip()
        elif not company_name.strip() and name_found:
             try:
                 general_name_area = listing_container.find_element(By.CSS_SELECTOR, "[class*='ProductCard__Header']")
                 company_name = general_name_area.text.splitlines()[0].strip()
             except:
                 company_name = "N/A (empty but found)"

        # Extract star rating
        try:
            star_rating_element = listing_container.find_element(By.CSS_SELECTOR, "span.sb.type-40.star-rating-label")
            star_rating_raw_text = star_rating_element.text.strip()
            average_rating, review_count = parse_rating_text(star_rating_raw_text)
        except Exception as e:
            print(f"  Could not find star rating for listing {index + 1}: {e}")

        # Extract website URL - TEMPORARILY DISABLED FOR DEBUGGING
        # Commenting out website URL extraction to test if window/tab handling causes CDP errors
        # website_url = extract_website_url(driver, listing_container, index)
        print(f"  Website URL extraction temporarily disabled for debugging (set to N/A)")

        # TODO: User to define specific 'other details' to extract here
        other_details = "N/A"

        # Store extracted data
        listing_data = {
            "company_name": company_name,
            "average_rating": average_rating,
            "review_count": review_count,
            "star_rating_raw_text": star_rating_raw_text,
            "website_url": website_url,
            "other_details": other_details
        }
        
        page_data.append(listing_data)

        print(f"  Name: {company_name}")
        print(f"  Average Rating: {average_rating}")
        print(f"  Review Count: {review_count}")
        print(f"  Website URL: {website_url}")
        print("-" * 30)

    return page_data

def save_to_csv(data_list, filename="capterra_data.csv"):
    """Save extracted data to CSV file"""
    csv_headers = ['Company Name', 'Average Rating', 'Review Count', 'Website URL', 'Other Details']
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
            writer.writeheader()
            
            for data_row in data_list:
                # Ensure all keys are present, defaulting if necessary
                row_to_write = {
                    'Company Name': data_row.get('company_name', 'N/A'),
                    'Average Rating': data_row.get('average_rating', 'N/A'),
                    'Review Count': data_row.get('review_count', 'N/A'),
                    'Website URL': data_row.get('website_url', 'N/A'),
                    'Other Details': data_row.get('other_details', 'N/A')
                }
                writer.writerow(row_to_write)
        
        print(f"Data successfully written to {filename}")
        return True
    except Exception as e:
        print(f"Error writing to CSV file: {e}")
        return False

# Main execution
print("Setting up web driver to connect to Bright Data Scraping Browser via HTTPS endpoint...")
options = ChromeOptions()
options.add_argument('--disable-gpu')  # Often recommended for remote/headless
options.add_argument('--window-size=1920,1080')

driver = None
extracted_data_list = []

try:
    print(f"Attempting to connect to remote browser at: {YOUR_BRIGHTDATA_SELENIUM_URL}")
    driver = webdriver.Remote(
        command_executor=YOUR_BRIGHTDATA_SELENIUM_URL,
        options=options
    )
    print(f"Successfully connected to Bright Data remote browser. Navigating to {URL}...")

    driver.get(URL)

    print(f"Page '{driver.title}' loaded. Waiting for product listings to appear...")

    # Check for access denied or human verification
    if "Access to this page has been denied" in driver.title or "verify you are human" in driver.page_source.lower():
        print("Access Denied or Human Verification Required by Capterra, even with Bright Data.")
        try:
            denied_screenshot_path = "capterra_access_denied_via_brightdata.png"
            driver.save_screenshot(denied_screenshot_path)
            print(f"Screenshot of denied page saved to: {denied_screenshot_path}")
        except Exception as screenshot_e:
            print(f"Could not save screenshot: {screenshot_e}")
        raise Exception("Capterra denied access or requires human verification via Bright Data.")

    product_container_selector = "div[data-testid^='product-card-container-']"
    wait = WebDriverWait(driver, 30)

    # Handle cookie consent if present
    try:
        cookie_accept_button_selector = "//button[contains(text(), 'Accept All Cookies') or contains(text(), 'Allow All') or contains(text(), 'Accept')]"
        short_wait = WebDriverWait(driver, 10)
        cookie_button = short_wait.until(EC.element_to_be_clickable((By.XPATH, cookie_accept_button_selector)))
        print("Cookie consent button found. Clicking it.")
        cookie_button.click()
        time.sleep(3)
    except Exception as e:
        print(f"Cookie consent button not found/not clickable within 10s, or already handled: No action taken on cookie banner.")

    # Main pagination loop
    page_number = 1
    while True:
        print(f"\n=== Processing Page {page_number} ===")
        
        # Process all listings on current page
        page_data = process_page_listings(driver, wait, product_container_selector)
        extracted_data_list.extend(page_data)
        
        print(f"Completed processing page {page_number}. Total listings collected so far: {len(extracted_data_list)}")
        
        # Look for "Next Page" button
        try:
            next_page_selector = "a[data-testid='go-to-next-page']"
            next_page_wait = WebDriverWait(driver, 10)
            next_page_button = next_page_wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, next_page_selector))
            )
            
            print("Navigating to next page...")
            
            # Scroll the button into view to avoid click interception
            print("Scrolling 'Next Page' button into view...")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_page_button)
            time.sleep(0.5)  # Brief pause to ensure scrolling completes
            
            # Attempt to click with fallback to JavaScript click if intercepted
            try:
                print("Attempting standard click on 'Next Page' button...")
                next_page_button.click()
            except ElementClickInterceptedException:
                print("Standard click intercepted. Attempting JavaScript click on 'Next Page' button...")
                driver.execute_script("arguments[0].click();", next_page_button)
            
            # Wait for next page content to load
            print("Waiting for next page to load...")
            
            # DEBUG: Capture browser state after "Next Page" click
            time.sleep(3)  # Allow a few seconds for any immediate page transition or URL update
            current_url_after_click = driver.current_url
            print(f"  URL after 'Next Page' click (expected page {page_number + 1}): {current_url_after_click}")

            try:
                screenshot_filename = f"capterra_page_{page_number + 1}_after_next_click.png"
                driver.save_screenshot(screenshot_filename)
                print(f"  Screenshot saved: {screenshot_filename}")
            except Exception as e_screenshot:
                print(f"  Could not save screenshot after 'Next Page' click: {e_screenshot}")
            
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_container_selector))
                )
                time.sleep(2)  # Additional brief pause for stability
                page_number += 1
            except TimeoutException:
                print("Next page did not load properly within timeout. Ending pagination.")
                break
                
        except (NoSuchElementException, TimeoutException):
            print("No more pages found or 'Next Page' button not found. Ending pagination.")
            break
        except Exception as e:
            print(f"Error during pagination: {e}. Ending pagination.")
            break

    print(f"\n=== Scraping Complete ===")
    print(f"Total listings collected: {len(extracted_data_list)}")
    print(f"Total pages processed: {page_number}")

    # Save data to CSV
    if extracted_data_list:
        csv_filename = "capterra_data.csv"
        print(f"\nSaving data to {csv_filename}...")
        save_to_csv(extracted_data_list, csv_filename)
    else:
        print("No data was collected to save.")

except Exception as e:
    print(f"An overall error occurred: {e}")
    # If an error occurs, try to take a screenshot for debugging
    if driver:
        try:
            error_screenshot_path = "capterra_error_screenshot.png"
            driver.save_screenshot(error_screenshot_path)
            print(f"Screenshot of error page saved to: {error_screenshot_path}")
        except Exception as screenshot_e:
            print(f"Could not save error screenshot: {screenshot_e}")

finally:
    if driver:
        print("Script finished. Closing the connection to the remote browser...")
        driver.quit()
        print("Session with remote browser closed.")
        
    # Final summary
    if extracted_data_list:
        print(f"\nFinal Summary:")
        print(f"- Total products scraped: {len(extracted_data_list)}")
        print(f"- Data saved to: capterra_data.csv")
        print(f"- Columns: Company Name, Average Rating, Review Count, Website URL, Other Details")