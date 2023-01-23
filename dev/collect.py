# ---------------------------------------------------------------------------- #
# --------------------------------- IMPORTS ---------------------------------- #
# ---------------------------------------------------------------------------- #
# Standard Library Imports
import datetime
import json
import re
import time

from itertools import chain

# Dependency Imports
import bs4 as bs
import pandas as pd

from nltk.corpus import stopwords
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ---------------------------------------------------------------------------- #
# --------------------------------- CLASSES ---------------------------------- #
# ---------------------------------------------------------------------------- #

class IndExtraction:

    def __init__(self, driver, url, job, location):
        self.driver = driver
        self.url = url
        self.job = job
        self.location = location
        self.df = pd.DataFrame(columns=["Hyperlink","JobTitle","Company","CompanyRating","Location"])

    def _request(self):
        self.driver.get(self.url)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "text-input-where"))
        )

        search = self.driver.find_element("id", "text-input-what")
        search.send_keys(self.job)
        search = self.driver.find_element("id", "text-input-where")
        search.send_keys(Keys.CONTROL + "a")
        search.send_keys(Keys.DELETE)
        search.send_keys(self.location)
        search.send_keys(Keys.RETURN)
        return

    @staticmethod
    def _collect_hyperlinks(job_cards):
        job_links = [(card.find_element(By.XPATH, ".//div/h2/a").get_attribute('href')) for card in job_cards]
        return job_links

    def _collect_job_titles(self, job_cards):
        job_titles = [card.find_element(By.XPATH, ".//div/h2/a/span").get_attribute('title').lower() for card in job_cards] # Acqure all full job titles for each jobcard
        job_titles = [re.split('[,|\-|\\|//|(|)|#]', card) for card in job_titles] # Split elements by any odd symbols to remove them from the job title
        job_titles = [string.split(' ') for title in job_titles for string in title if self.job.split(' ')[-1] in string.split(' ')]
        job_titles = [title[:title.index(self.job.split(' ')[-1])+1] for title in job_titles]
        job_titles = [['junior' if string in ['jr', 'jr.'] else string for string in title] for title in job_titles]
        job_titles = [['senior' if string in ['sr', 'sr.'] else string for string in title] for title in job_titles]
        job_titles = [title[title.index('and')+1:] if 'and' in title else title for title in job_titles]
        job_titles = [title[title.index('&')+1:] if '&' in title else title for title in job_titles]
        job_titles = [[string for string in title if not any(character.isdigit() for character in string)] for title in job_titles]
        job_titles = [' '.join([string for string in title if string != '']) for title in job_titles]
        return job_titles

    @staticmethod
    def _collect_companies(job_cards):
        companies = [card.find_element(By.CLASS_NAME, 'companyName').text for card in job_cards]
        return companies

    def _collect_company_ratings(self, job_cards):
        xpath = ".//div[2]/span[2]/a/span/span"
        company_ratings = [card.find_element(By.XPATH, xpath).text if self._check_if_element_exists(card, xpath) else 'NA' for card in job_cards]
        return company_ratings

    def _collect_location_info(self, job_cards):

        def collect_work_types(locations):
            work_types = []
            for location in locations:
                location = location.lower()
                if bool(re.search('hybrid', location)):
                    work_types.append('hybrid')
                elif bool(re.search('remote', location)):
                    work_types.append('remote')
                else:
                    work_types.append('onsite')
            return work_types

        def parse_locations(locations):
            with open('states.json', 'r') as file:
                states_dict = json.load(file)

            locations = [location.split(',') for location in locations]
            locations = [[location[0].strip(), location[1].split(' ')]
                          if len(location) > 1 else [location[0], ['NA', 'NA']]
                          for location in locations]
            locations = [[location[0].strip(), [substr for substr in location[1] if substr != '']] for location in locations]
            locations = [[location[0], location[1][0], location[1][1]]
                          if len(location[1]) == 2 else [location[0], location[1][0], 'NA']
                          for location in locations]
            locations = [['NA', states_dict[location[0]], 'NA'] if location[0] in states_dict and location[1] == 'NA' else location
                          for location in locations]
            return locations

        locations = [card.find_element(By.XPATH, ".//div[2]/div").text for card in job_cards]
        locations = [re.sub('[\\n]*(\+[0-9]+) (location[s]*)[\\n]*', '', location) for location in locations]
        work_types = collect_work_types(locations)
        locations = [re.sub('([hH]ybrid)*\s*[rR]emote [in]*', '', location) for location in locations]
        locations = [re.sub('\\n\(.+\)', '', location) for location in locations]
        locations = [re.sub('[rR]emote', 'NA', location) for location in locations]
        locations = parse_locations(locations)
        return locations, work_types

    def _collect_salary_info(self, job_cards):

        def parse_salaries(salaries):
            estimated = [bool(re.search('estimated', salary.lower())) for salary in salaries]
            salaries = [[string for string in salary.split(' ') if any(map(str.isdigit, string))] for salary in salaries]
            salaries = [[str(int(float(string[1:-1])*1000)) if 'k' in string.lower() else string[1:] for string in salary] for salary in salaries]
            salaries = [[re.sub(',', '', string) if ',' in string else string for string in salary] for salary in salaries]
            salaries = [[str(int(float(string)*40*52))
                         if len(string) < 4 or '.' in string else string
                         for string in salary] for salary in salaries]
            salaries = [['NA', 'NA'] if len(salary) == 0 else salary for salary in salaries]
            salaries = [['NA', salary[0]] if len(salary) == 1 else salary for salary in salaries]
            return salaries, estimated

        salaries = []
        for card in job_cards:
            if self._check_if_element_exists(card, ".//div[3]/div[1]/span/span"):
                salaries.append(card.find_element(By.XPATH, ".//div[3]/div[1]/span/span").text)
            elif self._check_if_element_exists(card, ".//div[3]/div/div"):
                salaries.append(card.find_element(By.XPATH, ".//div[3]/div/div").text)
            else:
                salaries.append('NA')
        salaries, estimated = parse_salaries(salaries)
        return salaries, estimated

    def _collect_hiring_insights(self):
        hire_cards = self.driver.find_elements(By.CLASS_NAME, "job_seen_beacon")
        urgent_hire = [self._check_if_element_exists(card, "shelfItem.urgentlyHiring", search_type=By.CLASS_NAME)
                      for card in hire_cards]
        easy_apply = [self._check_if_element_exists(card, "shelfItem.indeedApply", search_type=By.CLASS_NAME)
                      for card in hire_cards]
        return urgent_hire, easy_apply

# NOT CURRENTLY WORKING
    # def _collect_worktime_status(self, job_cards):
    #     worktime_status = []
    #     # /div[contains(@class='attribute_snippet')]/[@aria-label='Job type']
    #     # /svg[contains(@aria-label,'Job')]
    #     xpath = ".//div[3]/div[contains(@class,'metadata')]/div/svg"
    #     for card in job_cards:
    #         x = card.find_element(By.XPATH, xpath).text
    #         if self._check_if_element_exists(card, xpath):
    #             worktime_status.append(card.find_element(By.XPATH, xpath).text)
    #         else:
    #             worktime_status.append('NA')
    #     return worktime_status

    @staticmethod
    def _check_if_element_exists(card, search_string, search_type=By.XPATH):
        try:
            card.find_element(search_type, search_string)
        except NoSuchElementException:
            return False
        return True

    def _pagination(self):
        next_page = self.driver.find_element(By.CLASS_NAME, "jobsearch-LeftPane")
        next_page = next_page.find_element(By.XPATH, "//nav/div/a[@data-testid='pagination-page-next']")
        next_page.click()
        return

    def _check_next(self):
        try:
            self.driver.find_element(By.XPATH, "//nav/div/a[@data-testid='pagination-page-next']")
        except NoSuchElementException:
            return False
        return True

    def scrape_job_preview(self, job_pages=[]):
        self._request()
        while self._check_next():
            job_cards = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_all_elements_located((By.CLASS_NAME, "resultContent"))
            )

            locations, work_types = self._collect_location_info(job_cards)
            salaries, estimated = self._collect_salary_info(job_cards)
            urgent_hire, easy_apply = self._collect_hiring_insights()

            data = {
                "Hyperlink" : self._collect_hyperlinks(job_cards),
                "JobTitle" : self._collect_job_titles(job_cards),
                "Company": self._collect_companies(job_cards),
                "CompanyRating": self._collect_company_ratings(job_cards),
                "City": [location[0] for location in locations],
                "State": [location[1] for location in locations],
                "ZipCode": [location[2] for location in locations],
                "WorkType": work_types,
                # "WorkTimeStatus": self._collect_worktime_status(job_cards)
                "MinSalary": [salary[0] for salary in salaries],
                "MaxSalary": [salary[1] for salary in salaries],
                "SalaryEstimated": estimated,
                "EasyApply": easy_apply,
                "UrgentHire": urgent_hire,
                # "CandidatesAccepted":
                # "Qualifications":
                # "RequiredSkills":
                # "Benefits":
            }
            print(data["WorkTimeStatus"])
            self._pagination()
        self.driver.quit()
        return




### --------------------------THOUGHTS-------------------------- ###
# -> look for href inside of class='resultContent', collect list
# -> open each href, scrape data, then close iteratively
#   ->> This will not only use beautifulSoup, but also html parsing
# -> after all jobs on page have been scraped, find next page
#   ->> This will either be the arrow until it no longer exists, or increasing
#       an index value to find the next page, but I think arrow will be easier.

# jobcards = driver.find_element("id", "mosaic-jobcards")


# broth = requests.get(req['url'], headers=req['headers'])
# soup = bs.BeautifulSoup(broth.text, 'lxml')
# bowl = soup.find('div', attrs={'id':'mosaic-jobcards'})
#
# print(soup.text)

# for item in bowl.find('ul'):
#     job_title = item.find('h2', {'class': 'jobTitle css-1h4a4n5 eu4oa1w0'})
#     if job_title != None:
#         jobs = job_title.find('a').text
#     print(jobs)
# print(soup.prettify())
# print(soup.find_all('h2'))
#, {'class':'jobTitle css-1h4a4n5 eu4oa1w0'}
#&l=&from=searchOnHP&vjk=1155776db3d50a66
