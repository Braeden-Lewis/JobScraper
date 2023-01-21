# ---------------------------------------------------------------------------- #
# --------------------------------- IMPORTS ---------------------------------- #
# ---------------------------------------------------------------------------- #
# Local Imports
import configuration
import collect
#import monster

# Standard Library Imports
import sys

# Dependency Imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
# ---------------------------------------------------------------------------- #
# ------------------------------- EXECUTABLES -------------------------------- #
# ---------------------------------------------------------------------------- #

options = Options()
options.add_experimental_option('excludeSwitches', ['enable-logging'])

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                          options=options)

config = configuration.Configuration(driver)

indeed_jobs = collect.IndExtraction(config.driver, config.url,
                                          config.job, config.location)

indeed_jobs.job_pages = indeed_jobs.scrape_job_preview()
