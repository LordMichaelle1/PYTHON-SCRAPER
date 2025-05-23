from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException
import time
import re
import csv

def get_user_input():
    """Get G2 category URL, start page, and number of companies to scrape from user."""
    while True:
        # Get the base URL (without page parameter if it exists)
        url = input("Enter G2 category URL (e.g., https://www.g2.com/categories/marketing-automation): ").strip()
        
        # Remove any existing page parameter and fragment
        url = re.sub(r'[&?]page=\d+', '', url.split('#')[0])
        
        # Ensure it's a valid G2 category URL
        if not url.startswith('https://www.g2.com/categories/'):
            print("Error: URL must be a G2 category URL starting with 'https://www.g2.com/categories/'")
            continue
            
        # Add order parameter if not present (to ensure consistent sorting)
        if 'order=' not in url:
            url += '&' if '?' in url else '?'
            url += 'order=g2_score'
            
        try:
            start_page = int(input("Enter page number to start from (press Enter for page 1): ") or "1")
            if start_page < 1:
                print("Start page must be 1 or greater.")
                continue
                
            max_companies = int(input("Enter maximum number of companies to scrape (or press Enter for all): ") or "0")
            if max_companies < 0:
                print("Please enter a positive number or press Enter for all companies.")
                continue
                
            max_pages = int(input("Enter maximum number of pages to scrape (or press Enter for all): ") or "0")
            if max_pages < 0:
                print("Please enter a positive number or press Enter for all pages.")
                continue
                
            break
        except ValueError:
            print("Please enter valid numbers.")
    
    return url, start_page, max_companies, max_pages

# Get user input for G2 URL and scraping parameters
G2_URL, START_PAGE, MAX_COMPANIES, MAX_PAGES = get_user_input()

# Initialize the current page
current_page_g2 = START_PAGE - 1  # Will be incremented to START_PAGE in the first iteration

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
    visited_urls = set()  # Track visited URLs to prevent duplicates
    
    # Pagination loop
    page_count = 0
    
    # Main pagination loop
    while True:
        # Check if we've reached the maximum number of pages or companies
        if (MAX_PAGES > 0 and page_count >= MAX_PAGES) or \
           (MAX_COMPANIES > 0 and len(all_g2_product_data) >= MAX_COMPANIES):
            if MAX_PAGES > 0 and page_count >= MAX_PAGES:
                print(f"\nReached the maximum of {MAX_PAGES} pages. Stopping...")
            if MAX_COMPANIES > 0 and len(all_g2_product_data) >= MAX_COMPANIES:
                print(f"\nReached the maximum of {MAX_COMPANIES} companies. Stopping...")
            break
            
        page_count += 1
        current_page_g2 = (START_PAGE - 1) + page_count  # Calculate current page number
        
        # Construct the page URL
        separator = '&' if '?' in G2_URL else '?'
        page_url = f"{G2_URL}{separator}page={current_page_g2}#product-list"
        
        print(f"\n{'='*50}")
        print(f"SCRAPING G2 PAGE {current_page_g2}")
        print(f"{'='*50}")
        print(f"URL: {page_url}")
        
        # Navigate to the specific page
        try:
            driver.get(page_url)
            
            # Wait for the page to load and check for product listings
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_container_selector_g2))
                )
                # Additional check to ensure products are loaded
                listings = driver.find_elements(By.CSS_SELECTOR, product_container_selector_g2)
                if not listings:
                    print(f"No product listings found on page {current_page_g2}. This might be the last page.")
                    break
                    
                print(f"Successfully loaded page {current_page_g2} with {len(listings)} listings")
                
            except TimeoutException:
                print(f"Timed out waiting for page {current_page_g2} to load. It might not exist or the page structure is different.")
                # Try to check if we've reached the end of results
                if "No results match" in driver.page_source:
                    print("Reached the end of search results.")
                break
                
            except Exception as e:
                print(f"Error loading page {current_page_g2}: {str(e)}")
                # Take a screenshot for debugging
                try:
                    driver.save_screenshot(f"error_page_{current_page_g2}.png")
                    print(f"Screenshot saved as error_page_{current_page_g2}.png")
                except:
                    pass
                break
                
        except Exception as e:
            print(f"Error navigating to page {current_page_g2}: {str(e)}")
            break
        current_url = driver.current_url
        if current_url in visited_urls:
            print(f"Already visited this URL: {current_url}. Stopping pagination.")
            break
            
        visited_urls.add(current_url)
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
            for index in range(len(product_listings_g2)):
                try:
                    # Refresh the listing containers to avoid stale elements
                    listing_containers = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_container_selector_g2)))
                    if index >= len(listing_containers):
                        print(f"Warning: Listing container at index {index} not found. Skipping...")
                        continue
                        
                    listing_container = listing_containers[index]
                    
                    # Scroll the listing into view to ensure it's fully loaded
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", listing_container)
                    time.sleep(0.5)  # Small delay for any lazy loading
                    
                    print(f"Processing G2 listing {index + 1} on page {current_page_g2}...")
                    
                    # Extract product data with error handling
                    try:
                        product_data = extract_product_data_from_listing(listing_container)
                        
                        # Display extracted data
                        print(f"  Product Name: {product_data['product_name']}")
                        print(f"  G2 Profile Link: {product_data['g2_profile_link']}")
                        print(f"  Average Rating: {product_data['average_rating']}")
                        print(f"  Review Count: {product_data['review_count']}")
                        print(f"  Company Website: {product_data['website_url']}")
                        print("-" * 40)
                        
                        # Check for duplicates before adding
                        product_url = product_data.get('g2_profile_link', '')
                        if any(p.get('G2 Profile Link') == product_url for p in all_g2_product_data):
                            print(f"Skipping duplicate product: {product_data.get('product_name')}")
                            continue
                            
                        # Store complete product data
                        all_g2_product_data.append({
                            "Product Name": product_data['product_name'],
                            "G2 Profile Link": product_data['g2_profile_link'],
                            "Average Rating": product_data['average_rating'],
                            "Review Count": product_data['review_count'],
                            "Company Website URL": product_data['website_url'],
                            "Other Details": "N/A"
                        })
                        
                        # Check if we've reached the maximum number of companies
                        if MAX_COMPANIES > 0 and len(all_g2_product_data) >= MAX_COMPANIES:
                            print(f"\nReached the maximum of {MAX_COMPANIES} companies. Stopping...")
                            break
                            
                    except Exception as e:
                        print(f"Error processing listing {index + 1}: {str(e)}")
                        continue
                        
                    # Small delay between products to be respectful
                    time.sleep(1.5)  # Reduced from 2 to 1.5 seconds to be faster but still gentle
                    
                except Exception as e:
                    print(f"Error getting listing container {index + 1}: {str(e)}")
                    continue

        # After processing the page, check if we've reached the maximum number of companies
        if MAX_COMPANIES > 0 and len(all_g2_product_data) >= MAX_COMPANIES:
            print(f"\nReached the maximum of {MAX_COMPANIES} companies. Stopping...")
            break
            
        # Check if we've reached the last page by looking for "No results" message
        if "No results match" in driver.page_source:
            print("\nReached the end of search results.")
            break
            
        # Check if the current page has fewer items than expected (might be the last page)
        try:
            listings = driver.find_elements(By.CSS_SELECTOR, product_container_selector_g2)
            if not listings:
                print("\nNo more product listings found. Reached the end of results.")
                break
        except:
            pass
            
        # Small delay before loading the next page
        time.sleep(1)
            
except Exception as e:
    print(f"Error during pagination: {e}")

    # Save data to CSV
    if all_g2_product_data:
        # Generate filename from category name
        category_name = G2_URL.rstrip('/').split('/')[-1]
        csv_filename = f"g2_{category_name}_{int(time.time())}.csv"
        
        # Limit the number of companies if MAX_COMPANIES is set
        companies_to_save = all_g2_product_data
        if MAX_COMPANIES > 0 and len(all_g2_product_data) > MAX_COMPANIES:
            companies_to_save = all_g2_product_data[:MAX_COMPANIES]
            print(f"\nLimiting to {MAX_COMPANIES} companies as requested...")
        
        print(f"\nSaving {len(companies_to_save)} products to {csv_filename}...")
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Product Name', 'G2 Profile Link', 'Average Rating', 'Review Count', 'Company Website URL', 'Other Details']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for product in companies_to_save:
                writer.writerow(product)
        
        print(f"Data successfully saved to {csv_filename}")
        print(f"Scraped {len(companies_to_save)} out of {len(all_g2_product_data)} available companies")
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