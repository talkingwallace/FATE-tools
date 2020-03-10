import os
import re
from subprocess import Popen, PIPE
import json
import traceback
import time
import copy

FATE_FLOW_PATH = '../fate_flow/fate_flow_client.py'
CHECK_INTERVAL = 60

TEMPLATE_PARAM_PATH = './config_template/param.json'
TEMPLATE_DSL_PATH = './config_template/dsl.json'

running_job_list = []


class JOB(object):

    def __init__(self, id_, tag):
        self.id = id_
        self.tag = tag
        self.time = time.strftime("%y %m %d %x", time.localtime())
        self.status = 'running'

    def __str__(self):
        return 'id: {}, tag: {}, time: {}, status: {}'.format(self.id, self.tag, self.time, self.status)


def handle_ret_msg(std_out_str):
    try:
        s = std_out_str
        s = s.replace("'", '"')
        s = s.replace(r'\n', '')
        s = re.findall('{.*}', s)[0]
        dict_ = json.loads(s)
        return dict_

    except Exception as e:
        traceback.print_exc()
        return None


def get_job_status(jobId):

    b = Popen(args=['python', FATE_FLOW_PATH, '-f', 'query_job', '-j', str(jobId)], stdout=PIPE)
    str_ = str(b.stdout.read())
    rs = re.findall('"f_status":.*?,',str_)
    if len(rs) == 0:
        raise ValueError('unkown status get')
    if "running" in rs[0]:
        return 'running'
    elif 'success' in rs[0]:
        return 'success'
    elif 'failed' in rs[0]:
        return 'failed'
    else:
        return None


def load_config_template():
    template_conf = json.load(open(TEMPLATE_PARAM_PATH, 'r'))
    template_dsl = json.load(open(TEMPLATE_DSL_PATH, 'r'))
    return template_conf, template_dsl


def load_parameters():
    js = json.load(open(r'./parameters.json', 'r'))
    return js


def generate_configs(param, para_list):

    test_configs = para_list['tests']

    conf_names = []

    for test_name, config in test_configs.items():

        new_param = copy.deepcopy(param)
        para_dict = new_param['algorithm_parameters'][para_list['module_name']]

        for role, data_set in config["data_set_list"].items():
            new_param["role_parameters"][role]['args']['data']['train_data'] = data_set
            new_param["role_parameters"][role]['args']['data']['eval_data'] = data_set

        for k, value in config['params'].items():
            para_dict[k] = value
            if 'task_type' in config['params'] and config['params']['task_type'] == 'regression':
                new_param["role_parameters"]['guest']['dataio_0']['label_type'] = ['float']

        algo_para_list = config['algo_param_list']

        if config['generate_mode'] == 'align':
            params, tmp_config_name = None, None
            for k, value in algo_para_list.items():
                if type(algo_para_list[k]) is list:

                    if params is None and tmp_config_name is None:
                        params = [copy.deepcopy(new_param) for i in range(len(algo_para_list[k]))]
                        tmp_config_name = ['./configs/{}'.format(test_name) for i in range(len(algo_para_list[k]))]

                    for idx, val in enumerate(algo_para_list[k]):
                        para_dict = params[idx]['algorithm_parameters'][para_list['module_name']]
                        para_dict[k] = val
                        tmp_config_name[idx] += '_{}'.format(k)+'_{}'.format(val)

            for i in range(len(tmp_config_name)):
                tmp_config_name[i] += '.json'

            for n, p in zip(tmp_config_name, params):
                json.dump(p, open(n, 'w'), indent=3)

            conf_names.extend(tmp_config_name)

    return conf_names


def run_a_ml_task(conf, dsl, tag='cwj'):

    b = Popen(args=['python', FATE_FLOW_PATH, '-f', 'submit_job', '-c', conf, '-d', dsl], stdout=PIPE)
    rtn_str = str(b.stdout.read())
    rtn = handle_ret_msg(rtn_str)
    print(rtn)
    try:
        if rtn['retmsg'] == 'success':
            print('submit ml task success, job info is {}, tag is {}'.format(rtn['jobId'], tag))
            return rtn
        else:
            print('job failed: {}'.format(rtn_str))
            return None
    except:
        traceback.print_exc()
        print('unkown error {}'.format(rtn_str))
        return None


def check_cv_stop(jobId, cpn='secureboost_0', key='fold_0.iteration_49', parti_id='10000', role='guest'):

    query_rs = Popen(args=['python', FATE_FLOW_PATH, '-f', 'component_metric_all', '-r', role,
                           '-p', parti_id, '-cpn', cpn, '-j', str(jobId), ], stdout=PIPE)

    return key in str(query_rs.stdout.read())


def kill_job(jobId):
    ret = Popen(args=['python', FATE_FLOW_PATH, '-f', 'stop_job', '-j', str(jobId), ], stdout=PIPE)
    str_ = str(ret.stdout.read())
    ret = handle_ret_msg(str_)

    return ret['retmsg'] == 'kill job success'


def run_a_test(param_path, dsl_path, stop_cv_iter=50, tag='114514', check_cpn='secureboost_0'):

    stop_key = 'fold_0.iteration_{}'.format(stop_cv_iter-1)
    print("stop key is {}".format(stop_key))
    ret = run_a_ml_task(param_path, dsl_path, tag=tag)
    job = JOB(id_=ret['jobId'], tag=tag)

    while True:

        time.sleep(60)
        status = get_job_status(ret['jobId'])
        if status != 'running':
            print('job {} {}'.format(ret['jobId'],status))
            job.status = status
            break
        if check_cv_stop(ret['jobId'], cpn=check_cpn, key=stop_key):
            kill_rs = kill_job(ret['jobId'])
            print('kill_rs :{}'.format(kill_rs))
            job.status = 'done'
            break
        else:
            print('checking cv stop, should not stop')

    return job


def run_batch_test(batch_test_name='cwj', stop_cv_iter=50):

    para_list = load_parameters()
    param, dsl = load_config_template()
    conf_names = generate_configs(param, para_list)
    check_cpn = list(param["algorithm_parameters"].keys())[0]
    dsl_path = './dsls/{}_dsl.json'.format(batch_test_name)
    json.dump(dsl, open(dsl_path, 'w'))

    for idx, conf_path in enumerate(conf_names):
        print('start to run config {}, {}/{}'.format(conf_path, idx, len(conf_names)))
        history_log = open('./history.txt', 'a')
        job = run_a_test(conf_path, dsl_path, tag=conf_path, check_cpn=check_cpn, stop_cv_iter=stop_cv_iter)
        history_log.write(str(job)+'\n')
        history_log.close()
        print('run {} done'.format(conf_path))
        print('*'*30)


if __name__ == '__main__':

    run_batch_test('fast', stop_cv_iter=50)

    # para_list = load_parameters()
    # param, dsl = load_config_template()
    # conf_names = generate_configs(param, para_list)
