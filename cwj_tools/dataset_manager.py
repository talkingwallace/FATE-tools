import os
import re
from subprocess import Popen, PIPE
import json
import traceback
import time
import copy

DATA_PATH = '../examples/data'

FATE_FLOW_PATH = '../fate_flow/fate_flow_client.py'

CONFIG_PATH = './upload_template.json'

DATASET_NUM = 0

UPLOAD_INTERVAL = 0.5

upload_set = set()


def get_all_dataset(verbose=False):

    b = Popen(args=['python', FATE_FLOW_PATH, '-f', 'upload_history', ], stdout=PIPE)
    data_list = json.loads(b.stdout.read())['data']

    global DATASET_NUM
    DATASET_NUM = len(data_list)

    for dict_ in data_list:
        for k, v in dict_.items():
            upload_set.add((v['upload_info']['namespace'], v['upload_info']['table_name']))

    if verbose:
        print('process done')
        print('total number is {}'.format(DATASET_NUM))
        print('data set detail:')
        for t in sorted(list(upload_set)):
            print(t)


def set_upload_config(namespace, table_name, data_path):

    js = json.load(open('./upload_template.json', 'r'))
    js['file'] = data_path
    js['table_name'] = table_name
    js['namespace'] = namespace
    json.dump(js, open('./upload_template.json', 'w'), indent=2)


def upload_data():

    b = Popen(args=['python', FATE_FLOW_PATH, '-f', 'upload', '-c', CONFIG_PATH], stdout=PIPE)
    print(str(b.stdout.read()))


def update_all_dataset(namespace, data_path, show_result=True):

    get_all_dataset(verbose=show_result)
    dataset_names = os.listdir(data_path)
    to_upload = set()
    for name in dataset_names:
        t = (namespace, name.replace('.csv',''))
        if t not in upload_set:
            to_upload.add(t)

    print('to upload data sets number:', len(to_upload))
    for t in to_upload:
        print(t)

    data_path = data_path.replace('../', '')
    for t in to_upload:
        set_upload_config(namespace, table_name=t[1], data_path=data_path+r"/"+t[1]+'.csv')
        time.sleep(UPLOAD_INTERVAL)
        upload_data()


if __name__ == '__main__':

    # update_all_dataset('wj', '../cwj_dataset', show_result=False)
    # set_upload_config('nmsl', 'cnm', 'hhhh')
    # upload_data()
    get_all_dataset(verbose=True)