from re import search
from selenium import webdriver
from webdriver_manager import chrome
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selectorlib import Extractor
import random as rand
import time
    

# BIAS DETERMINATION
####################
# Long review AND verified, US and foreign      - Move to final evaluation
# Short review AND unverified, US               - Check profile for stars, lengths, and badges
# Short review AND unverified, foreign          - Drop score

# Configurable constants to change scrape settings
PRODUCT_URL = 'https://www.amazon.com/Bose-QuietComfort-Noise-Cancelling-Earbuds/dp/B08C4KWM9T/ref=sr_1_2?dchild=1&qid=1635902902&refinements=p_89%3ABose%2Cp_n_feature_four_browse-bin%3A12097501011&s=aht&sr=1-2'
#PRODUCT_URL = 'https://www.amazon.com/dp/1736809504/ref=sspa_dk_detail_6?psc=1&pd_rd_i=1736809504&pd_rd_w=l2vJt&pf_rd_p=887084a2-5c34-4113-a4f8-b7947847c308&pd_rd_wg=CgNLk&pf_rd_r=EMPAR8EKSF4Z2F2GV8CQ&pd_rd_r=a137980c-1c04-44e6-b3bf-46aa1d7c6d54&spLa=ZW5jcnlwdGVkUXVhbGlmaWVyPUExS1VOM1U5MFJHQkpYJmVuY3J5cHRlZElkPUEwMzM5OTI1MUJIWTZLVVpWNjNRVCZlbmNyeXB0ZWRBZElkPUEwODk4MzQ4QUVLRlJFRllNSU5LJndpZGdldE5hbWU9c3BfZGV0YWlsJmFjdGlvbj1jbGlja1JlZGlyZWN0JmRvTm90TG9nQ2xpY2s9dHJ1ZQ=='
#PRODUCT_URL = 'https://www.amazon.com/Web-Design-HTML-JavaScript-jQuery/dp/1118907442/ref=cm_cr_arp_d_product_top?ie=UTF8'
MAX_REVIEW_PAGES = 400
REVIEW_LENGTH = 100
ACCEPTANCE_PERCENTAGE = 0.85

# Gloabal variables used by multiple functions
pages_checked = 0
driver = None

# Arrays used to store the scraped data of interest.
profile_links = []
ratings = []
reviews = []
vp_badges = []
check_profile = []
trusted_profiles = []

# Backups of the scraped data to handle incomplete page appending
profile_links_back = []
ratings_back = []
reviews_back = []
vp_badges_back = []



# Opens Chrome to the Amazon page for the product in PRODUCT_URL
def open_amazon_product_link():
    global driver
    chrome_service = Service(executable_path='./chromedriver')
    driver = webdriver.Chrome(service=chrome_service)
    driver.get(PRODUCT_URL)

# Navigates to the 'All Reviews' page for this product
def show_all_reviews():
    global driver
    driver.find_element(By.XPATH, '//a[@data-hook="see-all-reviews-link-foot"]').click()

# Returns True or False depending on whether there are more elements on the page
def check_more_elements(element: str) -> bool:
    global driver
    
    # Will try 3 times just in case an element isn't fully loaded
    tries = 3
    while tries > 0:
        try:
            driver.find_element(By.XPATH, element)
            return True
        
        # Element hasn't fully loaded yet
        except NoSuchElementException:
            print(f'No element found, trying {tries - 1} more times...')
            tries -= 1
            time.sleep(5)
    
    # If after 3 tries the element is not found, likely not on page
    return False

# Navigates each page of reviews, storing all necessary data
def store_all_reviews():
    global driver, pages_checked
    
    # While there are still pages to scrape, continue storing reviews
    while check_more_elements('//li[@class="a-last"]//a') and pages_checked < MAX_REVIEW_PAGES:
        
        # Stores all the desired data on the page
        store_current_page_data(False)
        print(f'Scraped page {pages_checked + 1} of reviews.')

        # Try clicking 'next page' forever: we know it exists from above
        while True:
            try:
                driver.find_element(By.XPATH, '//li[@class="a-last"]//a').click()
                break
            
            # Element is not yet clickable
            except ElementClickInterceptedException:
                print('Element not clickable: Retrying in 1 second...')
                time.sleep(1)
            
            # Page reloads before the click is complete
            except StaleElementReferenceException:
                print('Stale Element Exception: Retrying in 1 second...')
                time.sleep(1)

        # Important to wait before click to next page (random time from 1 - 2.8 seconds)
        pages_checked += 1
        time.sleep(rand.random() * 1.8 + 1)
    
    # 'No review' padding for the last page (rare)
    for i in range(len(profile_links) - len(reviews)):
        print('Padding blank reviews with \'None\'')
        reviews.append(None)

    # Report the end of scraping review pages
    if(pages_checked == MAX_REVIEW_PAGES):
        print(f'Checked the maximum number of requested pages ({MAX_REVIEW_PAGES})')
    else:
        store_current_page_data(True)
        print(f'Checked all {pages_checked + 1} pages for this product!')

# Stores 3 parts of each review: (1) link to user's profile, (2) user's
# product rating, (3) user's product review
def store_current_page_data(last_page: bool):
    global driver, profile_links, profile_links_back, ratings, ratings_back
    global reviews, reviews_back, vp_badges, vp_badges_back
    
    # Each of the following blocks of code is similar in its structure, so
    # comments are only provided for the first block, and special cases
    # will be added in the blocks below the first

    # Will only scrape the page if customer reviews are detected
    if check_more_elements('//div[contains(@id, "customer_review")]'):
        
        # Back up the profile_links array in case appending is interrupted
        profile_links_back = profile_links[:]
        
        # Continue trying to append until all profile links on page are appended
        while True:
            try:
                data = driver.find_elements(By.XPATH, '//div[contains(@id, "customer_review")]//a[@class="a-profile"] | //div[contains(@id, "customer_review_foreign")]//span[@class="a-profile-name"]')
                for value in data:
                    profile_links.append(value.get_attribute('href'))
                
                # Clear the backup each time to reduce the amount of data stored
                profile_links_back.clear()
                break
            
            # If the page is reloaded in the middle of the loop above, restore
            # from backup and try again after 1 second
            except StaleElementReferenceException:
                print('Stale element: profile link. Retrying in 1 second...')
                profile_links = profile_links_back[:]
                time.sleep(1)

        ratings_back = ratings[:]
        while True:
            try:
                data = driver.find_elements(By.XPATH, '//div[contains(@id, "customer_review")]//i[@data-hook="review-star-rating"] | //div[contains(@id, "customer_review")]//i[@data-hook="cmps-review-star-rating"]')
                for value in data:
                    ratings.append(value.get_attribute('class'))
                ratings_back.clear()
                break
            except StaleElementReferenceException:
                print('Stale element: star rating. Retrying in 1 second...')
                ratings = ratings_back[:]
                time.sleep(1)

        reviews_back = reviews[:]
        while True:
            try:
                data = driver.find_elements(By.XPATH, '//div[contains(@id, "customer_review")]//span[@data-hook="review-body"]/span[1]')
                num_reviews = len(data)
                for value in data:
                    reviews.append(value.text)
                
                # In the case of an empty review, we should 'pad' the space with
                # a 'None' value so that the arrays remain the same length
                if not last_page:
                    for i in range(10 - num_reviews):
                        print('Padding blank reviews with \'None\'')
                        reviews.append('')                    
                reviews_back.clear()
                break
            except StaleElementReferenceException:
                print('Stale element: text review. Retrying in 1 second...')
                reviews = reviews_back[:]
                time.sleep(1)
        
        vp_badges_back = vp_badges[:]
        while True:
            try:
                data = driver.find_elements(By.XPATH, '//div[contains(@id, "customer_review")]')
                for value in data:
                    if 'Verified Purchase' in value.text: 
                        vp_badges.append(True)
                    else:
                        vp_badges.append(False)
                vp_badges_back.clear()
                break
            except StaleElementReferenceException:
                print('Stale element: purchase badge. Retrying in 1 second...')
                vp_badges = vp_badges_back[:]
                time.sleep(1)

        # DEBUGGING: print the length of all arrays
        print(len(profile_links))
        print(len(ratings))
        print(len(reviews))
        print(len(vp_badges))

# Determine which profiles should be investigated further
def determine_profiles_to_investigate():
    global profile_links
    
    # Use the min length in the case that error occurred above
    for i in range(min(len(profile_links), len(reviews), len(vp_badges))):
        
        # If they have either a badge or a long review, don't check profile
        if vp_badges[i] and (reviews[i] and len(reviews[i]) >= REVIEW_LENGTH):
            check_profile.append(False)
            trusted_profiles.append(True)
        else:
            check_profile.append(True)
            trusted_profiles.append(False)
            print(f'Review number {i}')

# Returns the integer rating from a string
def get_int_rating(rating: str):
    return int(rating[26])

# Look through a single profile, return its final trustworthiness
def investigate_profile(link: str):
    print('Checking profile...')
    driver.get(link)
    
    # Keep track of the number of reviews
    num_reviews = 0.0
    one_star_reviews = 0
    five_star_reviews = 0
    if check_more_elements('//div[@class="desktop card profile-at-card profile-at-review-box"]'):
        while True:
            try:
                data = driver.find_elements(By.XPATH, '//div[@class="desktop card profile-at-card profile-at-review-box"]//i[contains(@class, "profile")]')
                for value in data:
                    rating = get_int_rating(value.get_attribute('class'))
                    if rating == 1:
                        one_star_reviews += 1
                    if rating == 5:
                        five_star_reviews += 1
                    num_reviews += 1

                # Determine if we will trust the profile
                print(num_reviews, one_star_reviews, five_star_reviews)
                return not ((one_star_reviews / num_reviews > ACCEPTANCE_PERCENTAGE) or (five_star_reviews / num_reviews > ACCEPTANCE_PERCENTAGE))

            except StaleElementReferenceException:
                print('Stale element: user review block. Retrying in 1 second...')
                time.sleep(1)

# Look through profiles of sussy users         
def verify_profiles():

    # Just checking US users and updating trustworthiness
    for i in range(len(profile_links)):
        if profile_links[i] and check_profile[i]:
            trusted_profiles[i] = investigate_profile(profile_links[i])
            print(trusted_profiles[i])
            time.sleep(rand.random() * 1.8 + 1)


open_amazon_product_link()
show_all_reviews()
store_all_reviews()
determine_profiles_to_investigate()
verify_profiles()
# print(f'Got {len(profile_links)} links!\n', profile_links)
# print(f'Got {len(ratings)} ratings!\n', ratings)
# print(f'Got {len(reviews)} reviews!\n', reviews)
# print(f'Got {len(vp_badges)} badges!\n', vp_badges)

# Count and display the links that should be investigated
count = 0
for i in range(len(profile_links)):
    if not profile_links[i] and check_profile[i]:
        count += 1
print(f'The number of profiles to check is {check_profile.count(True)}')
print(f'Out of these, {count} don\'t have links and should be thrown away.')

driver.close()

# a-icon a-icon-star a-star-4 review-rating
# a-icon a-icon-star a-star-2 profile-at-review-stars