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
    

# SUS POINTS (3 and you're out)
# And weighted average based on num reviews
##############################################
# 90% 5 stars           - 1 sus point
# 90% 1 stars           - 1 sus point
# review is short       - 1 sus point
# unverified review     - 2 sus point

# LATER...
# helpful votes


PRODUCT_URL = 'https://www.amazon.com/Bose-QuietComfort-Noise-Cancelling-Earbuds/dp/B08C4KWM9T/ref=sr_1_2?dchild=1&qid=1635902902&refinements=p_89%3ABose%2Cp_n_feature_four_browse-bin%3A12097501011&s=aht&sr=1-2'
#PRODUCT_URL = 'https://www.amazon.com/dp/1736809504/ref=sspa_dk_detail_6?psc=1&pd_rd_i=1736809504&pd_rd_w=l2vJt&pf_rd_p=887084a2-5c34-4113-a4f8-b7947847c308&pd_rd_wg=CgNLk&pf_rd_r=EMPAR8EKSF4Z2F2GV8CQ&pd_rd_r=a137980c-1c04-44e6-b3bf-46aa1d7c6d54&spLa=ZW5jcnlwdGVkUXVhbGlmaWVyPUExS1VOM1U5MFJHQkpYJmVuY3J5cHRlZElkPUEwMzM5OTI1MUJIWTZLVVpWNjNRVCZlbmNyeXB0ZWRBZElkPUEwODk4MzQ4QUVLRlJFRllNSU5LJndpZGdldE5hbWU9c3BfZGV0YWlsJmFjdGlvbj1jbGlja1JlZGlyZWN0JmRvTm90TG9nQ2xpY2s9dHJ1ZQ=='
#PRODUCT_URL = 'https://www.amazon.com/Web-Design-HTML-JavaScript-jQuery/dp/1118907442/ref=cm_cr_arp_d_product_top?ie=UTF8'
MAX_REVIEW_PAGES = 400
REVIEW_LENGTH = 100
pages_checked = 0
driver = None
profile_links = []
ratings = []
reviews = []
vp_badges = []

profile_links_back = []
ratings_back = []
reviews_back = []
vp_badges_back = []

# How to get the text or attributes of an HTML element
# print(element.text)
# print(element.get_attribute('value'))

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
    tries = 3
    while tries > 0:
        try:
            driver.find_element(By.XPATH, element)
            return True
        except NoSuchElementException:
            print(f'No element found, trying {tries - 1} more times...')
            tries -= 1
            time.sleep(5)
    return False

# Navigates each page of reviews, storing all necessary data
def store_all_reviews():
    global driver, pages_checked
    while check_more_elements('//li[@class="a-last"]//a') and pages_checked < MAX_REVIEW_PAGES:
        store_current_page_data(False)
        print(f'Scraped page {pages_checked + 1} of reviews.')
        while True:
            try:
                driver.find_element(By.XPATH, '//li[@class="a-last"]//a').click()
                break
            except ElementClickInterceptedException:
                print('Element not clickable: Retrying in 1 second...')
                time.sleep(1)
            except StaleElementReferenceException:
                print('Stale Element Exception: Retrying in 1 second...')
                time.sleep(1)

        pages_checked += 1
        time.sleep(1.5)
    
    # No review padding for the last page (rare)
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
    if check_more_elements('//div[contains(@id, "customer_review")]'):
        
        # For each desired element, back up the array, then try fetching data
        profile_links_back = profile_links[:]
        while True:
            try:
                data = driver.find_elements(By.XPATH, '//div[contains(@id, "customer_review")]//a[@class="a-profile"] | //div[contains(@id, "customer_review_foreign")]//span[@class="a-profile-name"]')
                for value in data:
                    profile_links.append(value.get_attribute('href'))
                profile_links_back.clear()
                break
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
        # print(len(profile_links))
        # print(len(ratings))
        # print(len(reviews))
        # print(len(vp_badges))

# Modify the list of links based on badge and review length
def modify_profile_links():
    global profile_links
    for i in range(min(len(profile_links), len(reviews), len(vp_badges))):
        if not (vp_badges[i] or (reviews[i] and len(reviews[i]) >= REVIEW_LENGTH)):
            profile_links[i] = None

open_amazon_product_link()
show_all_reviews()
store_all_reviews()
modify_profile_links()
print(f'Got {len(profile_links)} links!\n', profile_links)
print(f'Got {len(ratings)} ratings!\n', ratings)
print(f'Got {len(reviews)} reviews!\n', reviews)
print(f'Got {len(vp_badges)} badges!\n', vp_badges)

count = 0
for link in profile_links:
    if link:
        count += 1
print(f'The number of valid links is {count}')

driver.close()