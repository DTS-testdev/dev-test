import requests
import json
import pandas as pd
import re
import time
import random
import os
import ast

# ================================================

api_token = os.getenv("API_TOKEN")
webhook_url_new = os.getenv("WEBHOOK_URL_NEW")
webhook_url_json = os.getenv("WEBHOOK_URL_JSON")
webhook_url_ping = os.getenv("WEBHOOK_URL_PING")
rCID = os.getenv("RCID")
sURL = os.getenv("SURL")

# ================================================

def comma_deleted_number (string):
    number_string = re.sub(r'[^\d]', '', string)
    number_integer = int(number_string)
    return number_integer


def string_to_number (string):
    try:
        try:
            former = int(string.split('억')[0])*10000
        except ValueError:
            former = 0
        try:
            latter = int(comma_deleted_number(string.split('억')[1]))
        except ValueError:
            latter = 0
        number_output = former + latter
    except IndexError:
        number_output = comma_deleted_number (string)
    return number_output


def send_msg(message, webhook_url):
    payload = {'text': message}
    headers={
        'Content-Type' : 'application/json'
    }
    resp = requests.post(webhook_url, headers=headers, data=json.dumps(payload))
    return resp


def recall_last_msg(
        api_token = api_token,
        channel_id = rCID,
        no_msg_return = []
):

    headers = {
        'Authorization': f'Bearer {api_token}',
    }
    params = {
        'channel': channel_id,
        'limit': 1,
    }

    response = requests.get(sURL, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['ok']:
            messages = data['messages']
            if messages:
                last_message = messages[0]['text']
                return last_message
            else:
                return no_msg_return
        else:
            return no_msg_return
    else:
        return no_msg_return

# ================================================

dURL = os.getenv("DURL")
parameters = json.loads(os.getenv("PARAMETERS_APT"))
header = json.loads(os.getenv("HEADER"))
search_comment = json.loads(os.getenv("SEARCH_COMMENT"))
url_prefix = os.getenv("URL_PREFIX")

lands = []

for parameter in parameters:
    page = 0
    while True:
        page = page + 1
        parameter['page'] = page

        response = requests.get(dURL, params=parameter, headers=header)

        if response.status_code != 200:
            print('invalid status: %d' % response.status_code)
            send_msg(f"[NLAND] {parameter['hscpNo']}-{page}\n{'invalid status: %d' % response.status_code}", webhook_url=webhook_url_ping)
            break
        else:
            send_msg(f"[NLAND] {parameter['hscpNo']}-{page}\n{'valid status: %d' % response.status_code}", webhook_url=webhook_url_ping)

        data = json.loads(response.text)
        result = data['result']
        if result is None:
            print('no result')
            break

        for item in result['list']:

            updated = item['cfmYmd']
            building = f"{item['atclNm']} {item['bildNm']}"
            floor = item['flrInfo'].split('/')[0]
            deposit = string_to_number(item['prcInfo'])
            area_trans = int(float(item['spc1'])// 3.3058)
            area_real = int(float(item['spc2'])// 3.3058)
            try:
                comment = item['atclFetrDesc']
                enlist = any(word in item['atclFetrDesc'] for word in search_comment)
            except KeyError:
                comment = ''
                enlist = False
            agent = item['rltrNm']
            articleno = item['atclNo']

            lands.append([updated, building, floor, deposit, area_trans, area_real, enlist, agent, comment, articleno])
            
        if result['moreDataYn'] == 'N':
            break

    time.sleep(random.uniform(20, 70))

result_df = pd.DataFrame(lands, columns=['updated', 'building', 'floor', 'deposit', 'area_trans', 'area_real', 'enlist', 'agent', 'comment', 'articleno']).sort_values(by='updated', ascending=False)
sorted_df = result_df[
    (result_df['deposit'] <= 30000)
    ].reset_index(drop=True)

try:
    list_saved = ast.literal_eval(recall_last_msg())
except:
    list_saved = []

filtered_df = sorted_df[~sorted_df['articleno'].isin(list_saved)]
list_new = filtered_df['articleno'].to_list()

if not filtered_df.empty:
    for idx, row in filtered_df.iterrows():
        enlist_ok = '🔥🔥🔥🔥🔥🔥🔥\n' if row['enlist'] else ''
        message_short = f"{enlist_ok}[{row['deposit']}] {row['building']} {row['floor']}층\n계약면적 {row['area_trans']}평, 전용면적 {row['area_real']}평\n{row['comment']}\n{row['agent']} {row['updated']}\n{url_prefix}{row['articleno']}"
        send_msg(message_short, webhook_url=webhook_url_new)
    list_all = list_saved + list_new
    send_msg(str(list_all), webhook_url=webhook_url_json)
