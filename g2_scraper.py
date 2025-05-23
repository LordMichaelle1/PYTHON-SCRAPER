from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException
import time
import re
import csv

# G2 Category URL to scrape
G2_URL = "https://www.g2.com/categories/marketing-automation"

# Your Bright Data Selenium HTTPS endpoint URL
YOUR_BRIGHTDATA_SELENIUM_URL = "https://brd-customer-hl_9b47d1b3-zone-scraping_browser2:xwd6horlvuqf@brd.superproxy.io:9515"

def extract_product_data_from_listing(listing_container):
    """
    Extract product data from a single G2 product listing container.
    Returns a dictionary with product name, G2 profile link, star rating, review count, and website URL.
    """
    product_data = {
        "product_name": "N/A",
        "g2_profile_link": "N/A",
        "average_rating": "N/A",
        "review_count": "N/A",
        "website_url": "N/A"
    }
    
    try:
        # Extract Product Name
        name_element = listing_container.find_element(By.CSS_SELECTOR, 'div[itemprop="name"]')
        product_data["product_name"] = name_element.text.strip()
        
        # Extract G2 Product Profile Link
        # Find the <a> tag that contains the product name div
        try:
            # Try to find the parent <a> tag of the name element
            profile_link_element = name_element.find_element(By.XPATH, ".//ancestor::a[contains(@href, '/products/')]")
            product_data["g2_profile_link"] = profile_link_element.get_attribute('href')
        except NoSuchElementException:
            # Alternative approach: find <a> tag within the listing container
            try:
                profile_link_element = listing_container.find_element(By.CSS_SELECTOR, 'a[href*="/products/"]')
                product_data["g2_profile_link"] = profile_link_element.get_attribute('href')
            except NoSuchElementException:
                print("    Could not find G2 profile link")
        
        # Extract Star Rating and Review Count
        try:
            # Find the ratings container
            rating_container = listing_container.find_element(By.CSS_SELECTOR, 'div.d-f.ai-c.fw-w')
            
            # Extract review count - look for text like (12,540)
            try:
                review_element = rating_container.find_element(By.CSS_SELECTOR, 'span.pl-4th')
                review_text = review_element.text.strip()
                # Extract number from parentheses
                review_match = re.search(r'\(([0-9,]+)\)', review_text)
                if review_match:
                    product_data["review_count"] = review_match.group(1)
            except NoSuchElementException:
                print("    Could not find review count")
            
            # Extract average rating - look for rating number
            try:
                rating_element = rating_container.find_element(By.CSS_SELECTOR, 'span.fw-semibold')
                rating_text = rating_element.text.strip()
                # Extract rating number (e.g., "4.4")
                rating_match = re.search(r'(\d+\.\d+)', rating_text)
                if rating_match:
                    product_data["average_rating"] = rating_match.group(1)
            except NoSuchElementException:
                print("    Could not find average rating")
                
        except NoSuchElementException:
            print("    Could not find rating container")
            
    except Exception as e:
        print(f"    Error extracting product data: {e}")
    
    # Extract Website URL if available
    try:
        website_url_input = listing_container.find_element(By.CSS_SELECTOR, 'input#secure_url')
        website_url = website_url_input.get_attribute('value')
        if website_url and website_url.strip():
            product_data["website_url"] = website_url.strip()
    except NoSuchElementException:
        print("    Could not find website URL")
    except Exception as e:
        print(f"    Error extracting website URL: {e}")
    
    return product_data

# def get_external_website_url(driver, g2_product_profile_url):
    """
    Navigate to G2 product profile page, click the 'Seller Details' tab,
    and extract the external company website URL from the hidden input field.
    Returns the external website URL or "N/A" if not found.
    """
    print(f"    Navigating to G2 profile: {g2_product_profile_url}")
    
    # Store original context
    original_window = driver.current_window_handle
    original_url = driver.current_url
    
    try:
        # Navigate to G2 Product Profile Page
        driver.get(g2_product_profile_url)
        
        # Wait for page to load - wait for a common element on G2 product pages
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .product-header, [data-testid='product-header']"))
        )
        print("    G2 product profile page loaded successfully")
        
        # Find and click the "Seller Details" tab
        try:
            # Use XPath to find the tab by text content for more reliability
            seller_details_tab_selector = "//li[contains(@class, 'product-card__tab') and normalize-space(.)='Seller Details']"
            
            seller_details_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, seller_details_tab_selector))
            )
            
            # Scroll the tab into view and click it
            driver.execute_script("arguments[0].scrollIntoView(true);", seller_details_tab)
            time.sleep(0.5)
            
            try:
                seller_details_tab.click()
            except ElementClickInterceptedException:
                print("      Standard click on 'Seller Details' tab intercepted, trying JavaScript click...")
                driver.execute_script("arguments[0].click();", seller_details_tab)
            
            print("    Clicked 'Seller Details' tab.")
            
            # Wait for the hidden input field containing the website URL to become present
            website_url_input_selector = "input#secure_url"
            website_url_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, website_url_input_selector))
            )
            
            # Extract the external URL from the input field's value attribute
            external_url = website_url_input.get_attribute('value')
            print(f"      Found external website URL from hidden input: {external_url}")
            
            if external_url and external_url.strip():
                return external_url
            else:
                print("      Hidden input field was empty or contained no URL")
                return "N/A"
                
        except TimeoutException:
            print("    Could not find 'Seller Details' tab or hidden input field within timeout")
            return "N/A"
        except Exception as e:
            print(f"    Error clicking 'Seller Details' tab or extracting URL: {e}")
            return "N/A"
            
    except Exception as e:
        print(f"    Error navigating to G2 profile page: {e}")
        return "N/A"
    finally:
        # Ensure we're back to the original page for continued scraping
        try:
            if driver.current_url != original_url:
                driver.get(original_url)
                # Wait for the listings to reload
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.product-card.x-software-component-card"))
                )
                print("    Successfully returned to G2 listings page")
        except Exception as e:
            print(f"    Warning: Could not return to original listings page: {e}")

def parse_g2_rating_reviews(rating_text, review_text):
    """
    Helper function to parse rating and review text if needed.
    """
    rating = "N/A"
    review_count = "N/A"
    
    if rating_text:
        rating_match = re.search(r'(\d+\.\d+)', rating_text)
        if rating_match:
            rating = rating_match.group(1)
    
    if review_text:
        review_match = re.search(r'\(([0-9,]+)\)', review_text)
        if review_match:
            review_count = review_match.group(1)
    
    return rating, review_count

print("Setting up G2 scraper web driver to connect to Bright Data...")
options = ChromeOptions()
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = None
all_g2_product_data = []

try:
    print(f"Attempting to connect to remote browser at: {YOUR_BRIGHTDATA_SELENIUM_URL}")
    driver = webdriver.Remote(
        command_executor=YOUR_BRIGHTDATA_SELENIUM_URL,
        options=options
    )
    
    # Set user agent to avoid detection
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print(f"Successfully connected. Navigating to G2 URL: {G2_URL}...")
    driver.get(G2_URL)
    page_title = driver.title
    print(f"Page '{page_title}' loaded. Waiting for G2 product listings...")

    # Basic check for immediate blocks
    if "Access Denied" in page_title or "Human Verification" in page_title or "are you a robot" in driver.page_source.lower():
        print("Access Denied or Human Verification Required by G2. Exiting.")
        try:
            denied_screenshot_path = "g2_access_denied.png"
            driver.save_screenshot(denied_screenshot_path)
            print(f"Screenshot of denied page saved to: {denied_screenshot_path}")
        except Exception as screenshot_e:
            print(f"Could not save G2 denied page screenshot: {screenshot_e}")
        raise Exception("G2 denied access or requires human verification via Bright Data.")

    wait = WebDriverWait(driver, 30)

    # Handle potential cookie banner
    try:
        # Common cookie banner selectors for G2
        cookie_selectors = [
            "button[data-testid='accept-cookies']",
            ".cookie-banner button",
            "[id*='cookie'] button",
            ".gdpr-banner button"
        ]
        
        for selector in cookie_selectors:
            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                print("G2 Cookie consent button found. Clicking it.")
                cookie_button.click()
                time.sleep(2)
                break
            except TimeoutException:
                continue
                
    except Exception as e_cookie:
        print(f"No cookie banner found or error handling cookies: {e_cookie}")

    # Selector for the container of each product listing on G2
    product_container_selector_g2 = "div.product-card.x-software-component-card"
    current_page_g2 = 1
    
    # Pagination loop
    while True:
        print(f"\n{'='*50}")
        print(f"SCRAPING G2 PAGE {current_page_g2}")
        print(f"{'='*50}")
        
        print(f"Attempting to find G2 product listings using selector: {product_container_selector_g2}")
        
        # Wait for product listings to load
        try:
            product_listings_g2 = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_container_selector_g2)))
        except TimeoutException:
            print(f"No product listings found on page {current_page_g2}. Ending pagination.")
            break

        if not product_listings_g2:
            print(f"No G2 product listings found on page {current_page_g2}.")
            break
        else:
            print(f"Found {len(product_listings_g2)} G2 product listings on page {current_page_g2}.")
            
            # Re-fetch product listings immediately before processing to avoid StaleElementReferenceException
            print("Re-fetching product listings for the current page to ensure element freshness...")
            try:
                product_listings_g2 = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_container_selector_g2)))
                print(f"Successfully re-fetched {len(product_listings_g2)} listings for page {current_page_g2}.")
            except TimeoutException:
                print(f"Could not re-fetch product listings on page {current_page_g2}. Ending pagination.")
                break
            
            if not product_listings_g2:
                print(f"No G2 product listings found on page {current_page_g2} after re-fetch. Ending.")
                break
            
            print("-" * 40)

            # Process each product listing
            for index, listing_container in enumerate(product_listings_g2):
                print(f"Processing G2 listing {index + 1} on page {current_page_g2}...")
                
                # Extract product data (including website URL)
                product_data = extract_product_data_from_listing(listing_container)
                
                # Display extracted data
                print(f"  Product Name: {product_data['product_name']}")
                print(f"  G2 Profile Link: {product_data['g2_profile_link']}")
                print(f"  Average Rating: {product_data['average_rating']}")
                print(f"  Review Count: {product_data['review_count']}")
                print(f"  Company Website: {product_data['website_url']}")
                print("-" * 40)
                
                # Store complete product data
                all_g2_product_data.append({
                    "Product Name": product_data['product_name'],
                    "G2 Profile Link": product_data['g2_profile_link'],
                    "Average Rating": product_data['average_rating'],
                    "Review Count": product_data['review_count'],
                    "Company Website URL": product_data['website_url'],
                    "Other Details": "N/A"
                })
                
                # Small delay between products to be respectful
                time.sleep(1)

        # Attempt to find and click the "Next" pagination button
        print(f"\nLooking for 'Next' pagination button on page {current_page_g2}...")
        try:
            # Try multiple selectors for the Next button
            next_button_selectors = [
                "a.pagination__named-link[href*='page=']",
                "a[href*='page=']:contains('Next')",
                "//a[@class='pagination__named-link' and contains(text(),'Next')]",
                "//a[contains(@class,'pagination') and contains(text(),'Next')]"
            ]
            
            next_button = None
            for selector in next_button_selectors:
                try:
                    if selector.startswith("//"):
                        # XPath selector
                        next_button = driver.find_element(By.XPATH, selector)
                    else:
                        # CSS selector
                        next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Verify it's actually the next button
                    if 'next' in next_button.text.lower() or '›' in next_button.text:
                        break
                    else:
                        next_button = None
                except NoSuchElementException:
                    continue
            
            if next_button:
                print(f"Found 'Next' button. Navigating to page {current_page_g2 + 1}...")
                
                # Scroll to next button and click
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(1)
                
                try:
                    next_button.click()
                except WebDriverException:
                    # Try JavaScript click as fallback
                    driver.execute_script("arguments[0].click();", next_button)
                
                current_page_g2 += 1
                
                # Wait for new page to load
                expected_url_pattern = f"page={current_page_g2}"
                try:
                    WebDriverWait(driver, 15).until(
                        lambda d: expected_url_pattern in d.current_url
                    )
                    print(f"Successfully navigated to page {current_page_g2}")
                    
                    # Wait for new product listings to load with improved robustness
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_container_selector_g2))
                    )
                    
                    # Additional wait to ensure page content is fully loaded
                    time.sleep(2)
                    print(f"Page {current_page_g2} loaded successfully")
                    
                except TimeoutException:
                    print(f"Timeout waiting for page {current_page_g2} to load properly")
                    break
                    
            else:
                print("No 'Next' pagination button found. Reached the last page.")
                break
                
        except Exception as e:
            print(f"Error during pagination: {e}")
            break

    # Save data to CSV
    if all_g2_product_data:
        csv_filename = "g2_data.csv"
        print(f"\nSaving {len(all_g2_product_data)} products to {csv_filename}...")
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Product Name', 'G2 Profile Link', 'Average Rating', 'Review Count', 'Company Website URL', 'Other Details']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for product in all_g2_product_data:
                writer.writerow(product)
        
        print(f"Data successfully saved to {csv_filename}")
        print("Note: External website URL extraction enabled only for the first product on the first page using 'Seller Details' tab method")
    else:
        print("No data collected to save.")

except TimeoutException:
    print(f"A timeout occurred on G2. The page might not have loaded as expected or elements were not found in time.")
    if driver:
        try:
            timeout_screenshot_path = "g2_timeout_screenshot.png"
            driver.save_screenshot(timeout_screenshot_path)
            print(f"Screenshot of G2 timeout page saved to: {timeout_screenshot_path}")
        except Exception as screenshot_e:
            print(f"Could not save G2 timeout screenshot: {screenshot_e}")
except Exception as e:
    print(f"An overall error occurred in the G2 scraper: {e}")
    if driver:
        try:
            error_screenshot_path = "g2_error_screenshot.png"
            driver.save_screenshot(error_screenshot_path)
            print(f"Screenshot of G2 error page saved to: {error_screenshot_path}")
        except Exception as screenshot_e:
            print(f"Could not save G2 error screenshot: {screenshot_e}")
finally:
    if driver:
        print("G2 script finished. Closing the connection to the remote browser...")
        driver.quit()
        print("Session with G2 remote browser closed.")
    
    if all_g2_product_data:
        print(f"\nSUMMARY: Successfully scraped {len(all_g2_product_data)} products from G2 across {current_page_g2} page(s).")
        print("Data includes: Product Names, G2 Profile Links, Ratings, and Review Counts")
        print("Note: External website URL extraction was attempted only for the first product on the first page using 'Seller Details' tab method")
    else:
        print("\nNo data was scraped from G2 in this run.")