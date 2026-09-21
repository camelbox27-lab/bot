from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

chrome_options = Options()
chrome_options.add_argument('--headless=new')
driver = webdriver.Chrome(options=chrome_options)
driver.get('https://www.adamchoi.co.uk/cards/detailed')
time.sleep(5)

try:
    driver.find_element(By.XPATH, "//label[contains(text(), 'All matches')]").click()
    time.sleep(2)
except Exception as e:
    print('Click error:', e)

rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
for row in rows[:5]:
    cols = row.find_elements(By.TAG_NAME, 'td')
    texts = [c.get_attribute('textContent').strip() for c in cols]
    print('Row cols:', len(cols), sum(len(t) for t in texts))
    for t in texts:
        print('  Col:', ascii(t))

driver.quit()
