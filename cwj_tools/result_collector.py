import os
import re
from subprocess import Popen, PIPE
import json
import pandas as pd
import tqdm

FATE_FLOW_PATH = '../fate_flow/fate_flow_client.py'


def extract_metric(dict_, metric_name_list):
    l = dict_['data']
    for m in l:
        if m[0] in metric_name_list:
            return m[1]
    return None


def process_a_job(jobId, cpn_name, metric_name_list, key_iterator):

    b = Popen(args=['python', FATE_FLOW_PATH, '-f', 'component_metric_all', '-j', str(jobId),
                    '-cpn', cpn_name, '-r', 'guest', '-p', '10000'], stdout=PIPE)

    metric_dict = json.loads(b.stdout.read())
    data = metric_dict['data']
    validate_data = data['validate']
    rs = {}
    print(validate_data)
    for k in key_iterator:
        rs[k] = extract_metric(validate_data[k], metric_name_list)

    return rs


if __name__ == '__main__':

    cpn_name = 'fast_secureboost_0'
    history_job = open('./history.txt', 'r').read().split('\n')
    collect_rs = {}

    key_template = 'fold_0.iteration_{}'
    keys = [key_template.format(i) for i in range(4, 50, 5)]

    count = 0
    for job_str in history_job:
        print("{}/{}".format(count, len(history_job)))
        count += 1
        try:
            jobId = re.findall('id: .*?,', job_str)[0]
            jobId = jobId.replace(',', '').replace('id: ', '')
            tag = re.findall('tag: .*?,', job_str)[0]
            print(jobId)
            rs = process_a_job(jobId, cpn_name, metric_name_list=['auc', 'root_mean_squared_error',
                                                                  'accuracy'], key_iterator=keys)
            collect_rs[tag] = rs
        except:
            pass
    #
    # rs = process_a_job(2020030902280643914721, cpn_name, metric_name_list=['accuracy'], key_iterator=keys)

    df = pd.DataFrame()
    df = df.from_dict(collect_rs, orient='columns')
    df = df.transpose()
    df.to_csv('test_result.csv',)
