#import packages
from selenium import webdriver as wb
import pandas as pd
import numpy as np
import os
from time import sleep
import random

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.action_chains import ActionChains

import scraper_tool

chrome_options = Options()




def get_all_match_url(url, driver):
	"""
	Get the URLs to all matches in the given link.
	"""
	driver.get(url)
	all_matches = driver.find_elements(by=By.CSS_SELECTOR, value="#all_sched > div[class='table_container current is_setup'] > table > tbody > tr > td[data-stat='score'] > a")
	all_match_links = [match.get_attribute('href') for match in all_matches]
	return all_match_links



def get_normal_stats(tbl_element, match_id='', team_id=''):
	"""
	Get all the individual player stats from each table for any particular match
	This grabs all the stats from the match and then add player_id, team_id and match_id to make a table
	"""
	#get header for stats table
	header_elements = tbl_element.find_elements(by=By.XPATH, value='thead/tr[2]/th')
	header = [element.get_attribute('data-stat') for element in header_elements[3:]] 
	for i, column_name in zip(range(3), ['player_id', 'match_id', 'team_id']):
		header.insert(i, column_name)
	#print(header)

	#add rows
	body_rows = tbl_element.find_elements(by=By.XPATH, value='tbody/tr')
	tbl_body = []
	for row_ind in body_rows:
		row = []
		player_id = f"{row_ind.find_element(by=By.TAG_NAME, value='th').get_attribute('data-append-csv')}"
		row = [cell.text for cell in row_ind.find_elements(by=By.TAG_NAME, value='td')[2:]] #get only position, minutes and stats
		for i, column_value in zip(range(3), [player_id, match_id, team_id]):
			row.insert(i,column_value)
		#print(row)
		tbl_body.append(row)
	#print(np.array(tbl_body).shape)
	tbl = pd.DataFrame(np.array(tbl_body), columns=header)

	return tbl

def get_shot_stats(tbl_element, match_id):
	header_elements = tbl_element.find_elements(by=By.XPATH, value='thead/tr[2]/th')
	header = [element.get_attribute('data-stat') for element in header_elements] #get only position, minutes and stats

	header[1] = 'player_id'
	header[2] = 'team_id'
	#print(header)
	body_rows = tbl_element.find_elements(by=By.CSS_SELECTOR, value='tbody > tr[class^="shots_"]')
	tbl_body = []
	for row_ind in body_rows:
		row = []
		minute =  row_ind.find_element(by=By.TAG_NAME, value='th').text
		player_id = row_ind.find_element(by=By.CSS_SELECTOR, value='td[data-stat="player"]').get_attribute('data-append-csv')
		team_id = row_ind.get_attribute('class').split("_")[1]
		try:
			sca_1_player = row_ind.find_element(by=By.CSS_SELECTOR, value='td[data-stat="sca_1_player"] > a').get_attribute('href').rsplit("/", 2)[-2]
		except NoSuchElementException:
			sca_1_player = ""
		try:
			sca_2_player = row_ind.find_element(by=By.CSS_SELECTOR, value='td[data-stat="sca_2_player"] > a').get_attribute('href').rsplit("/", 2)[-2]
		except NoSuchElementException:
			sca_2_player = ""

		row = [cell.text for cell in row_ind.find_elements(by=By.TAG_NAME, value='td')[2:]] #get only position, minutes and stats
		for i, column_value in zip(range(3), [minute, player_id, match_id]):
			row.insert(i,column_value)
		row[7] = sca_1_player
		row[9] = sca_2_player
		#print(row)
		#print(f'alo {len(row)}')
		tbl_body.append(row)
	#print(np.array(tbl_body).shape)
	tbl = pd.DataFrame(np.array(tbl_body), columns=header)

	return tbl


def get_all_stats_from_match(url, driver):
	"""
	This function uses the 2 functions get_normal_stats and get_shot_stats to retrieve all stats from the match in the URL.
	All stats are saved into the respective csv files.
	"""
	driver.get(url)
	match_id = url.rsplit("/", 2)[-2]

	#find 2 stats tables (1 for each team)
	
	tables_to_scrape = driver.find_elements(by=By.CSS_SELECTOR, value="div[id^='all_player_stats_'][class^='table_wrapper']")
	for table in tables_to_scrape:
		#get the ID of the team the given table is for
		team_id = table.get_attribute('id').rsplit('_', 1)[-1]
		#find toggle that switches between summary, passing, pass type, defensive actions, possession and misc.
		toggles = table.find_element(by=By.CSS_SELECTOR, value="div[class='filter switcher']").find_elements(by=By.TAG_NAME, value="a") 
		#for each toggle: click that toggle button to switch to that table, 
		for toggle in toggles:
			driver.execute_script("arguments[0].scrollIntoView();", toggle)
			driver.execute_script("arguments[0].click();", toggle)
			sleep(random.randint(1,2))
			toggle_table = table.find_element(by=By.CSS_SELECTOR, value="div[class='switcher_content'] > div[class$='current'] > table")
			toggle_table_name = toggle_table.get_attribute('id').rsplit('_', 1)[-1]
			print(f"Getting toggle table #{toggles.index(toggle)+1} out of {len(toggles)} for Team #{tables_to_scrape.index(table)+1}")
			#get table
			tbl_df = get_normal_stats(toggle_table, match_id, team_id)
			#check if the csv file this data will be stored in is empty or not
			csv_file = f'{toggle_table_name}.csv'
			try:
				file_check = not(bool(os.path.getsize(csv_file))) #if file size > 0, file_check = False, meaning we don't need to include header when writing to csv
				tbl_df.to_csv(csv_file, mode='a', header=file_check)
			except OSError:
				tbl_df.to_csv(csv_file, mode='a', header=True)
	
	#get shots table			
	
	shot_table = driver.find_element(by=By.XPATH, value='//*[@id="shots_all"]')
	print('getting shots table')
	tbl_df = get_shot_stats(shot_table, match_id)
	#check if the csv file this data will be stored in is empty or not
	csv_file = f'shot.csv'
	try:
		file_check = not(bool(os.path.getsize(csv_file))) #if file size > 0, file_check = False, meaning we don't need to include header when writing to csv
		tbl_df.to_csv(csv_file, mode='a', header=file_check)
	except OSError:
		tbl_df.to_csv(csv_file, mode='a', header=True)

	return match_id


premier_league_match_list = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"

wbD = scraper_tool.open_chrome_window(headless=True)
all_match_links = get_all_match_url(premier_league_match_list, wbD)

for match in all_match_links:
	print(f'Scraping all player data of match #{all_match_links.index(match)+1} out of {len(all_match_links)}: {match}')
	get_all_stats_from_match(match, wbD)
wbD.quit()


