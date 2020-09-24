#!/usr/bin/env python 
# coding:utf-8
import os
import configparser
import datetime
import time
from src.lib import get_github
from src.lib import github_searchcode
from src.lib import db_mysql
from pymysql import NULL
mysql_conn = db_mysql.MyPymysqlPoolDict()
now_time = time.time()

# 从配置文件里读取github的用户名密码
file_path = os.path.join(os.path.dirname(__file__), "../../../conf/key.conf")
cf = configparser.ConfigParser()
cf.read(file_path,encoding='utf-8')
section = 'github'
user_name = cf.get(section, 'user')
password = cf.get(section, 'password')
api_token = cf.get(section, 'token')
ak_list_table_name = 'ak_list'
ak_leak_table_name = 'ak_leak'


def get_sql_select_result(sql):
    attempts = 0
    status = False
    result = list()
    while attempts < 3 and not status:
        try:
            mysql_conn_dict = db_mysql.MyPymysqlPoolDict()
            result = mysql_conn_dict.select(sql)
        except Exception as e:
            print(e)
        else:
            status = True
            #if result:
            #    for i in result:
            #        ak_list.append(i['ak_id'])
            #print('成功获取可用ak %s 个,列表: %s' % (len(ak_list),ak_list))
        finally:
            mysql_conn_dict.dispose()
        attempts += 1
    return result


def check_ak_leak_in_github(task_id=0):
    calculate_fail = []     #对接巡检系统失败的ak
    calculate_data = {'task_id' : task_id, 'object_field' : 'ak'}     #巡检抽象化数据集合

    sql_select_ak_be_check = "select accesskey_id from %s WHERE status = 1 and policies <> 'NULL'; " % ak_list_table_name
    ak_be_check_list = []      #待检查的ak列表集合
    ak_info_list = get_sql_select_result(sql_select_ak_be_check)
    if ak_info_list:
        for i in ak_info_list:
            ak_be_check_list.append(i['accesskey_id'])
        print('获待检查ak %s 个,列表: %s' % (len(ak_be_check_list), ak_be_check_list))

    sql_ak_leak_list = "SELECT  ak_list_id, file_path_url FROM %s WHERE end_time is NULL ;" % ak_leak_table_name
    ak_leak_list = get_sql_select_result(sql_ak_leak_list)    #获取ak泄漏表中还未恢复泄漏问题的ak信息
    problem_ak_list = []    #经过此次检查存在泄漏问题的ak信息集合
    for ak in ak_be_check_list:
        calculate_data_list = []
        calculate_data['object_value'] = ak
        metric_dict = {}
        attempts = 0
        break_flag = False
        leak_list = list()
        while attempts < 4:
            try:
                leak_list = github_searchcode.Engine(token=api_token, keyword=ak).search()
                break
            except Exception as e:
                attempts += 1
                print("获取失败: %s," % e, "重试三次")
                time.sleep(660)
                if attempts == 3:
                    break_flag = True
                    break
        if break_flag:
            continue
        #print('leak_list',leak_list,type(leak_list),len(leak_list))

        if len(leak_list) > 0:
            print('查询到有%s的匹配记录' % ak, leak_list)
            metric_dict['use_in_github'] = 1
            calculate_data['metric_dict'] = metric_dict
            for i in leak_list:
                sql_select_ak_id = "select id from %s WHERE accesskey_id = '%s'; " % (ak_list_table_name, ak)
                select_ak_id_result = get_sql_select_result(sql_select_ak_id)
                print("select_ak_id_result", select_ak_id_result)
                ak_id = select_ak_id_result[0]['id']

                problem_ak = {'ak_list_id' : ak_id, 'file_path_url' : i['url']}
                problem_ak_list.append(problem_ak)  #将存在泄漏情况的ak信息收集到一个集合里

                sql = "select count(*) from %s where file_path_url = '%s' AND  ak_list_id = '%s' AND end_time is NULL" % (ak_leak_table_name, i['url'], ak_id)
                result = get_sql_select_result(sql)     #查询ak_leak表中是否已存在该ak泄漏记录
                ak_leak_count = result[0]['count(*)']
                if ak_leak_count == 0:
                    if i['email'] is None:
                        i['email'] = NULL
                    sql = "insert into %s set ak_list_id = '%s', repository = '%s', file_path_url = '%s', user = '%s', email = %s, start_time = '%s';" % (
                    ak_leak_table_name, ak_id, i['repository'], i['url'], i['user_name'], i['email'], now_time)
                    attempts = 0
                    while attempts < 3:
                        try:
                            mysql_conn_dict = db_mysql.MyPymysqlPoolDict()
                            mysql_conn_dict.update(sql)
                            mysql_conn_dict.dispose()
                            break
                        except Exception as e:
                            print(e)
                            attempts += 1
                        finally:
                            if attempts == 2:
                                print("error: insert {m} table is fail" .format(m = ak_leak_table_name))
                                return False

        if len(leak_list) == 0:
            print('本次查询没有%s的匹配记录' % ak)
            metric_dict['use_in_github'] = 0
            calculate_data['metric_dict'] = metric_dict
        calculate_data_list.append(calculate_data)
        print('calculate_data_list', calculate_data_list)

        #数据对接巡检系统
        from src.judge import data_calculate
        calculate_result = data_calculate.BecomeCalculate(calculate_data_list).exec_data_list()
        #print('calculate_result',calculate_result)
        if not calculate_result:
            calculate_fail.append(ak)
    if calculate_fail:
        print('输出对接巡检系统失败的ak',calculate_fail)
    print('problem_ak_list',problem_ak_list)

    #判断出已经恢复泄露的ak
    if ak_leak_list and problem_ak_list:
        noleak_ak = [ak for ak in ak_leak_list if ak not in problem_ak_list]
    elif ak_leak_list and not problem_ak_list:
        noleak_ak = ak_leak_list
    print('noleak_ak',noleak_ak)
    if noleak_ak:
        for i in noleak_ak:
            sql = "update %s set end_time = '%s' WHERE ak_list_id = '%s' AND file_path_url = '%s' AND end_time is NULL;" % (ak_leak_table_name, now_time, i['ak_list_id'], i['file_path_url'])
            attempts = 0
            while attempts < 3:
                try:
                    mysql_conn_dict = db_mysql.MyPymysqlPoolDict()
                    mysql_conn_dict.update(sql)
                    mysql_conn_dict.dispose()
                    break
                except Exception as e:
                    print(e)
                    attempts += 1

    return True

if __name__ == "__main__":
    print('当前时间', time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    check_ak_leak_in_github()
    print('当前时间', time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))



