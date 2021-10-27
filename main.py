import base64
import datetime
import hashlib
import hmac
import json
import random
import re
import struct
import time
import requests
import vk_api
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from vk_api.longpoll import VkLongPoll

with open('account.json', 'r') as json_file_account:
    data = json.load(json_file_account)

with open('words.json', 'r', encoding='utf-8') as json_file_words:
    words = json.load(json_file_words)

advance_url = "https://forum.advance-rp.ru/"
login_url = "https://forum.advance-rp.ru/login/login"
options = webdriver.ChromeOptions()
options.add_experimental_option("excludeSwitches", ["enable-logging"])
driver = webdriver.Chrome(executable_path=data['data']['path_to_browser'])
session_vk = vk_api.VkApi(token=data['data']['token_vk'])
session_api = session_vk.get_api()
longpoll = VkLongPoll(session_vk)
ready_list = {}
secret = data['data']['auth_code']

dataAuthorization = {
    'login': data['data']['login'],
    'password': data['data']['password'],
    'remember': '1',
}

header = {
    'User-Agent': data['data']['user_agent']
}

symbols = ['.', ',', '!', '?', '$', '@', '#', '%', '^', '&', '*', '(', ')', '-', '+', '/', '\\', '[', ']', '{', '}',
           ';', '#', '"', ':', 'ь', 'ъ', '<', '>', '~']

themes = {
    'words': [
        'https://forum.advance-rp.ru/threads/arp-igra-slova.1788222/page-7777',
        'https://forum.advance-rp.ru/threads/arp-igra-slova.1916258/page-7777',
    ],
    'Cities': 'https://forum.advance-rp.ru/threads/arp-igra-goroda.1742581/page-7777',
    'Names': 'https://forum.advance-rp.ru/threads/arp-igra-imena.1874176/page-7777',
}


# MessageToVk
def vk(text):
    session_vk.method('messages.send', {'peer_id': data['data']['peer_id'], 'message': text, 'random_id': 0})


def get_time():
    date_now = datetime.datetime.now()
    _time = date_now.strftime("%d.%m.%Y %H:%M")
    return _time


# Google Authenticator
def get_hotp_token(secret, intervals_no):
    key = base64.b32decode(secret, True)
    msg = struct.pack(">Q", intervals_no)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[19] & 15
    h = (struct.unpack(">I", h[o:o + 4])[0] & 0x7fffffff) % 1000000
    return '{:06}'.format(h)


def get_totp_token(secret):
    return get_hotp_token(secret, intervals_no=int(time.time()) // 30)


# Themes parser
def parse():
    for i in themes['words']:
        url = i
        response = requests.get(url, headers=header)
        soup = BeautifulSoup(response.content, 'html.parser')
        items = soup.findAll('div', class_='message-inner')
        comps = []
        global ready_list

        for item in items:
            comps.append({
                'message': item.find('div', class_='bbWrapper'),
                'user_id': item.find('a', class_='username')['data-user-id'],
                'nickname': item.find('a', class_='username').get_text(strip=True),
                'post_id': item.find('div', class_='js-lbContainer')['data-lb-id']
            })

        if int(comps[-1]['user_id']) != int(data['data']['account_id']):
            if comps[-1]['message'].blockquote:
                comps[-1]['message'].blockquote.decompose()
            driver.get(url=url)
            word = comps[-1]['message'].get_text()
            pattern = re.compile(r'\w+')
            word = pattern.findall(word)[0].lower()
            last = word[-1]
            for symbol in symbols:
                if symbol == last:
                    last = word[-2]
            post_id = re.sub("[^0-9]", "", comps[-1]['post_id'])
            ready_list = {
                'nickname': comps[-1]['nickname'],
                'post_id': post_id,
                'user_id': comps[-1]['user_id'],
                'user_word': comps[-1]['message'].get_text(),
                'send_word': random.choice(words[last]),
                'url': url
            }


try:
    driver.get(url=login_url)
    time.sleep(2)

    login_input = driver.find_element_by_name('login')
    login_input.clear()
    login_input.send_keys(dataAuthorization['login'])
    time.sleep(0)

    password_input = driver.find_element_by_name('password')
    password_input.clear()
    password_input.send_keys(dataAuthorization['password'])
    time.sleep(1)
    password_input.send_keys(Keys.ENTER)
    time.sleep(1)

    auth_input = driver.find_element_by_name('code')
    auth_input.clear()
    auth_input.send_keys(get_totp_token(secret))
    auth_input.send_keys(Keys.ENTER)

    while driver.current_url != advance_url:
        time.sleep(1)
    while True:
        parse()
        time.sleep(5)
        if ready_list != {}:
            time.sleep(2)
            input_field = driver.find_element_by_class_name('fr-view')
            input_field.clear()
            input_field.send_keys(
                '[QUOTE="{0}, post: {1}, member: {2}"]\n{3}\n[/QUOTE]\n{4}'.format(ready_list['nickname'],
                                                                                   ready_list['post_id'],
                                                                                   ready_list['user_id'],
                                                                                   ready_list['user_word'],
                                                                                   ready_list['send_word']))
            time.sleep(5)
            button_input = driver.find_element_by_class_name('button--icon--reply').click()
            time.sleep(1)
            if len(driver.find_elements_by_css_selector('div.overlay-title')) > 0:
                driver.find_element_by_class_name('overlay-titleCloser').click()
                time.sleep(20)
                button_input = driver.find_element_by_class_name('button--icon--reply').click()
            print_message = '[{0}] Сообщение: "{1}", автор: {2}, ответ: {3}'.format(get_time(),
                                                                                    ready_list['user_word'],
                                                                                    ready_list['nickname'],
                                                                                    ready_list['send_word'])
            print(print_message)
            vk(print_message)
            ready_list = {}
except Exception as ex:
    vk('[Ошибка/Краш | {0}]: {1}'.format(get_time(), ex))
    print('[Ошибка/Краш | {0}]: {1}'.format(get_time(), ex))

