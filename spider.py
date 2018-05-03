import json
import os
from urllib.parse import urlencode
import pymongo
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError
import re
from multiprocessing import Pool
from hashlib import md5
from json.decoder import JSONDecodeError
#创建数据库连接 connect = False能防止多线程时候的warnning
MONGO_URL = 'localhost'
MONGO_DB = 'toutiao'
MONGO_TABLE = 'toutiao'
client = pymongo.MongoClient(MONGO_URL, connect=False)
db = client[MONGO_DB]
headers = {
	'user-agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'
}
def get_page_index(offset,keyword):
	data={
	'offset':offset,
	'format':'json',
	'keyword':keyword,
	'autoload':'true',
	'count':20,
	'cur_tab':3,
	'from':'gallery'
	}
	#拼接url 用来获取json数据
	url = 'https://www.toutiao.com/search_content/?'+urlencode(data)
	#如果返回的状态码为200 则返回 否则返回None
	try:
		response = requests.get(url)
		if response.status_code == 200:
			return response.text
		return None
	except Exception as e:
		print(e)
		return None
def parse_page_index(text):
	#解析json数据 获取每一页的article_url 在之前判断是否包含'data'键名
    try:
        data = json.loads(text)
        if data and 'data' in data.keys():
            for item in data.get('data'):
                yield item.get('article_url')
    except JSONDecodeError:
        pass
def get_page_content(url):
	#获取内容页状态码 
	try:
		response = requests.get(url,headers=headers)
		if response.status_code == 200:
			return response.text
		return None
	except Exception as e:
		print(e)
		return None
def parse_page_content(html,url):
	#用beautifulsoup获取title js中的变量gallery保存的有图片链接数据，格式是json数据 用json.loads()解析后获取 	
	soup = BeautifulSoup(html, 'lxml')
	result = soup.select('title')
	title = result[0].get_text() if result else ''
	imgs_pattern = re.compile('gallery: JSON.parse\("(.*?)"\)',re.S)
	result = re.search(imgs_pattern,html)
	if result:
		result = result.group(1).replace('\\','')
		try:
			data = json.loads(result)
			if data and 'sub_images' in data.keys():
				sub_images = data.get('sub_images')
				images = [item.get('url') for item in sub_images]
				
				for img in images:
					down_img(img,title)
				
				return {
				'title':title,
				'url':url,
				'images':images
				}				
		except JSONDecodeError as e:
			print('-'*20)
			print(e)
def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('Successfully Saved to Mongo', result)
        return True
    return False


def down_img(url,title):
	#获取图片二进制文件，传入save_img 
	try:
		response = requests.get(url)
		if response.status_code == 200:
			save_img(response.content,title) 
		return None
	except Exception as e:
		print(e+url)
		return None
def save_img(content,title):
	#保存图片至本地
	file_path = os.getcwd()+'\\'+title
	if not os.path.exists(file_path):os.makedirs(file_path)
	full_name = file_path+'\\'+str(md5(content).hexdigest())+'.jpg'
	with open (full_name,'wb+') as f:
		f.write(content)
		print('Successfully save:'+file_path)
		f.close()

def main(offset):
	html = get_page_index(offset,'美图')
	urls = parse_page_index(html)

	for url in urls:
		content = get_page_content(url)
		result = parse_page_content(content,url)
		save_to_mongo(result)
		
#开启多线程 多线程采集1到4页用82S
'''	
if __name__ == '__main__':
	pool = Pool()
	groups = [x*20 for x in range(1,5)]
	pool.map(main,groups)
	pool.close()
	pool.join()
'''
#不用多线程 183S

if __name__ == '__main__':
	for x in range(1,5):
		groups = x*20
		main(groups)
