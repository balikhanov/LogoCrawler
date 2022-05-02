# pip3 install webdriver-manager selenium googlesearch-python requests beautifulsoup4
from googlesearch import search
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests

from time import sleep, time
import csv
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures
from itertools import chain


class LogoCrawler:
    def __init__(self, filename):
        with open(filename) as csvFile:
            reader = csv.reader(csvFile)
            self.urls = [row[0] for row in reader]
        self.urlsNum = len(self.urls)
        self.options = webdriver.ChromeOptions()
        self.options.add_experimental_option("excludeSwitches", ["enable-logging"])
        self.options.headless = True
        self.chromeDriverManager = ChromeDriverManager().install()
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',"Accept-Encoding": "gzip, deflate"}

    def retrieveLogoUrl(self, page_source, str1, str2, indent):
        index = page_source.find(str1)
        indexStart = page_source.find(str2, index) + indent
        indexEnd = page_source.find('"', indexStart)
        logoUrl = page_source[indexStart:indexEnd].replace("&amp;", "&")
        if logoUrl is None:
            return ""
        return logoUrl
    
    def parse(self, url):
        fullUrl = "http://www."+ url

        #First approach: get the html and search for keywords amongst img attributes 
        try:
            response = requests.get(fullUrl, headers=self.headers, stream=True, timeout=10)
        except Exception:
            return url, ''
        soup = BeautifulSoup(response.content, 'html.parser')
        for node in soup.find_all('img'):
            logoUrl = node.get('src')
            if not logoUrl:
                continue
            searchString = ''.join(list(chain.from_iterable(node.attrs.values()))).casefold()
            if "logo" in searchString or "brand" in searchString:
                if "http" not in logoUrl:
                    logoUrl = fullUrl + logoUrl
                return url, logoUrl

        #Second approach: google search for company's facebook group and scrape the logo
        query = "facebook.com " + url
        try:
            fbGroupUrl = list(search(query))[0]
        except Exception:
            return url, ''
        # fbGroupUrl = list(search(query, tld="com", num=10, stop=10, pause=1))[0]

        driver = webdriver.Chrome(self.chromeDriverManager, options=self.options)
        driver.get(fbGroupUrl)
        sleep(2)
        
        if ("tinyViewport tinyWidth" in driver.page_source):
            return url, self.retrieveLogoUrl(driver.page_source, "_6tb5 img", "src=", 5)
        elif ("_9dls __fb-light-mode" in driver.page_source):
            return url, self.retrieveLogoUrl(driver.page_source, "xMidYMid slice", "xlink:href=", 12)
            
        return url, ""

    def getLogoUrls(self):
        print("logoCrawler started")
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_results = {executor.submit(self.parse, url): url for url in self.urls}

            results = []
            processedUrls = 1
            for future in concurrent.futures.as_completed(future_results):
                url, logoUrl = future.result()
                if logoUrl:
                    results.append([url, logoUrl])
                print("Processed urls = {}/{} {}%, Logos scraped = {}%, {} {}".format(processedUrls, self.urlsNum, processedUrls/self.urlsNum*100, len(results)/processedUrls*100, url, logoUrl))
                processedUrls += 1
            
            with open("result.csv", 'w') as csvFile:
                csvWriter = csv.writer(csvFile)
                for row in results:
                    csvWriter.writerow(row)


if __name__ == '__main__':
    filename = 'websites.csv'
    crawler = LogoCrawler(filename)
    crawler.getLogoUrls()