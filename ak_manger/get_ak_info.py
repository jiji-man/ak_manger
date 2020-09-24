#!/usr/bin/env python3
# coding:utf-8
import datetime,time
import os
import json
import configparser

# 项目的lib
from src.lib.cloud import aliyun_api
from src.lib import db_mysql
from pymysql import NULL

class GetRamInfo:
    username = ''

    def __init__(self):  # 获取ram中所有用户名
        self.data_formart = 'json'
        self.mysql_conn_dict = db_mysql.MyPymysqlPoolDict()
        file_path = os.path.join(os.path.dirname(__file__), "../../../conf/key.conf")
        self.cf = configparser.ConfigParser()
        self.cf.read(file_path, encoding='utf-8')
        self.ak_list_tablename = 'ak_list'

    def get_username_list(self):    #获取用户列表
        marker = '' #当marker为空，最多获取100个用户数据
        username_list = []
        try:
            response = aliyun_api.AliyunApi(self.accessid, self.accesssecret, self.regionid).list_users(self.data_formart, marker)
            result = json.loads(response, encoding='utf-8')
        except Exception as e :
            msg = 'Error: Get account list is fail.error_code: {m} '.format( m=e)
            print(msg)
        else:
            truncated = result['IsTruncated']
            for i in result['Users']['User']:
                username = i['UserName']
                username_list.append(username)
            while truncated:    #是否被截断
                marker = result['Marker']
                response = aliyun_api.AliyunApi(self.accessid, self.accesssecret, self.regionid).list_users(self.data_formart, marker)

                # response = client.do_action_with_exception(request)
                result = json.loads(response, encoding='utf-8')
                truncated = result['IsTruncated']

                for i in result['Users']['User']:
                    username = i['UserName']
                    username_list.append(username)
        return username_list

    def get_last_login_time(self):  #获取账号最后登录时间
        last_login_time = NULL
        try:
            response = aliyun_api.AliyunApi(self.accessid, self.accesssecret, self.regionid).get_user_lastlogintime(self.data_formart, self.username)
            result = json.loads(response, encoding='utf-8')
            #print('账号信息：',result)
        except Exception as e:
            msg = 'Error: User {u} get account last login time is fail.error_code: {m} '.format(u=self.username, m=e)
            print(msg)
        else:
            last_login_time_str = str(result['User']['LastLoginDate'])
            if last_login_time_str:
                last_login_time = datetime.datetime.strftime((datetime.datetime.strptime(last_login_time_str, "%Y-%m-%dT%H:%M:%SZ") + datetime.timedelta(hours=8)) ,'%Y-%m-%d %H:%M:%S')
                last_login_time = "'{m}'".format(m=last_login_time)
        return last_login_time

    def get_login_profile(self):  # 获取用户是否可以登陆控制台
        username = self.username
        try:
            response = aliyun_api.AliyunApi(self.accessid, self.accesssecret, self.regionid).get_user_loginprofile(self.data_formart, username)
            if response is not False:
                login_profile = json.loads(response, encoding='utf-8')
                i = login_profile['LoginProfile']
                if not i:
                    login_enable = 0
                else:
                    login_enable = 1
            else:
                login_enable = 0
        except Exception as e:
            msg = 'Error: User {u} get login_profile is fail.error_code: {m} '.format(u=self.username, m=e)
            print(msg)
            login_enable = 0
        return login_enable

    def get_policies(self):  # 获取用户所拥有的权限
        polices_json = NULL
        try:
            # 获取权限所有内容
            response = aliyun_api.AliyunApi(self.accessid, self.accesssecret, self.regionid).get_user_policies(self.data_formart, self.username)
            policies = json.loads(response, encoding='utf-8')
        except Exception as e:
            msg = 'Error: User {u} get account policies is fail.error_code: {m} '.format(u=self.username, m=e)
            print(msg)
        else:
            # 获取权限信息
            police = policies['Policies']['Policy']
            if police:
                police_list = []
                for i in police:
                    policyname = i['PolicyName']
                    police_list.append(policyname)
                    polices_json = json.dumps(police_list,sort_keys=True,separators=(',',':'))
        return polices_json

    def get_ak_by_user(self):  # 获取用户所有的ak信息
        ak_info_json = dict()
        try:
            response = aliyun_api.AliyunApi(self.accessid, self.accesssecret, self.regionid).get_user_ak(self.data_formart, self.username)
            result = json.loads(response, encoding='utf-8')
            #print('ak_result',result)
            accesskey_info = result['AccessKeys']['AccessKey']
        except Exception as e:
            msg = 'Error: User {u} get accesskey_info is fail.error_code: {m} '.format(u=self.username, m=e)
            print(msg)
        else:
            # 获取用户ak信息
            if accesskey_info:  # 如果有ak的话，则accesskey_info非空
                for i in accesskey_info:
                    ak_info = dict()
                    ak_id = i['AccessKeyId']
                    ak_status = i['Status']

                    if ak_id:
                        ak_last_use_time = self.get_ak_last_use_time(ak_id)
                        ak_info_json["ak_id"] = ak_id
                        ak_info_json["ak_status"] = ak_status
                        ak_info_json["last_use_time"] = ak_last_use_time
                    #ak_info_list_json.append(ak_info)
        return ak_info_json

    def get_ak_last_use_time(self,ak_id):  #获取ak的最后使用时间
        ak_last_use_time = NULL
        eventrw = 'All'
        try:
            response = aliyun_api.AliyunApi(self.accessid, self.accesssecret, self.regionid).get_last_useak_time(self.data_formart, eventrw, ak_id)
            result = json.loads(response, encoding='utf-8')
        except Exception as e:
            msg = 'User {u} get last_use_ak_time is fail.error_code: {m} '.format(u=self.username, m=e)
            print(msg)
        else:
            try:
                if result['Events']:
                    last_event_time = result['Events'][0]['eventTime']
                    ak_last_use_time = datetime.datetime.strftime(
                        (datetime.datetime.strptime(last_event_time, "%Y-%m-%dT%H:%M:%SZ") + datetime.timedelta(hours=8)),
                        '%Y-%m-%d %H:%M:%S')
                    ak_last_use_time = "'{m}'".format(m=ak_last_use_time)
            except Exception as e:
                msg = 'User {u} get last_use_ak_time is fail.error_code: {m} '.format(u=self.username, m=e)
                print(msg)
        return ak_last_use_time

    def get_ak_list(self,task_id=0):
        import aliyunsdkcore
        from aliyunsdkcore.acs_exception.exceptions import ClientException
        # 保存当前的sys.stdout状态, 开始捕获当前的输出
        path = './ak.log'
        #current = sys.stdout
        #f = open(path, 'w')
        # 这一步实际是sys.stdout.write, 当sys捕获到了print输出的时候, 就写入f里面
        #sys.stdout = f

        now_time = datetime.datetime.now()
        ak_id_list = []
        for ak_section in self.cf.sections():
            print('ak_section',ak_section)
            if ak_section.startswith('aliyun') or ak_section.startswith('tencentcloud'):
                try:
                    self.accessid = self.cf.get(ak_section, 'AccessKeyId')
                    self.accesssecret = self.cf.get(ak_section, 'AccessKeySecret')
                    self.regionid = self.cf.get(ak_section, 'DefaultRegionId')
                    self.cost_item_id = self.cf.get(ak_section, 'CostItemId')
                except Exception as e:
                    print("except, reason: %s" % e)
                    continue

                if ak_section.startswith('aliyun'):
                    from src.lib.cloud import aliyun_api

                    username_list = self.get_username_list()
                    if username_list:   #当前云账户下存在ram账户
                        for self.username in username_list:
                            login_enable = self.get_login_profile()
                            last_login_time = self.get_last_login_time()
                            polices_json = self.get_policies()
                            ak_info_json = self.get_ak_by_user()
                            if ak_info_json:
                                #for self.a in akinfo_list_json:
                                    #print('self.username', self.username, self.a)
                                ak_id = ak_info_json['ak_id']
                                ak_status = ak_info_json['ak_status']
                                last_use_time = ak_info_json['last_use_time']
                                ak_id_list.append(ak_id)
                                if ak_status == 'Active':
                                    ak_status = 1
                                elif ak_status == 'Inactive':
                                    ak_status = 0
                                # 判断是否是新增的ak，如果是插入一条新数据，不是则从表中读取数据
                                sql = "select count(*) from %s where accesskey_id = '%s'" % (self.ak_list_tablename, ak_id)
                                try:
                                    #mysql_conn = db_mysql.MyPymysqlPool()
                                    result = self.mysql_conn_dict.select(sql)
                                    #mysql_conn.dispose()
                                except Exception as e:
                                    print('ERROR:',e)
                                    self.mysql_conn_dict.dispose()
                                    return False
                                username_count = result[0]['count(*)']
                                if username_count == 0:
                                    sql = (
                                    "insert into %s(accesskey_id, status, last_use_time, account_name, account_login_enable, account_last_login_time, policies, cost_item_id, update_time) "
                                    "values('%s', '%s', %s, '%s', '%s', %s, '%s', '%s', '%s')" %
                                    (self.ak_list_tablename, ak_id, ak_status, last_use_time,
                                     self.username, login_enable, last_login_time,
                                     polices_json, self.cost_item_id, now_time))
                                    attempts = 0
                                    status = False
                                    while attempts < 3 and not status:
                                        try:
                                            #mysql_conn = db_mysql.MyPymysqlPool()
                                            self.mysql_conn_dict.insert(sql)
                                            #mysql_conn.dispose()
                                        except Exception as e:
                                            print('ERROR:',e)
                                            time.sleep(10)
                                            #mysql_conn.dispose()
                                        except self.mysql_conn_dict as e:
                                            print("数据库连接失败.")
                                            time.sleep(10)
                                        else:
                                            status = True
                                        attempts += 1
                                else:
                                    sql = "select last_use_time, account_login_enable, account_last_login_time, policies, status, update_time, ak_status_change_time from %s where accesskey_id = '%s'" \
                                          % (self.ak_list_tablename, ak_id)
                                    try:
                                        old_result = self.mysql_conn_dict.select(sql)
                                    except Exception as e:
                                        print('ERROR:',e)
                                        self.mysql_conn_dict.dispose()
                                        return False
                                    print('查询出已存在的ak:{m}记录'.format(m = ak_id), old_result)
                                    last_use_time_old = old_result[0]['last_use_time']
                                    login_enable_old = old_result[0]['account_login_enable']
                                    last_login_time_old = old_result[0]['account_last_login_time']
                                    ak_status_old = old_result[0]['status']
                                    policies_old = old_result[0]['policies']
                                    ak_status_change_time_old = old_result[0]['ak_status_change_time']
                                    if ak_status_change_time_old is None:
                                        ak_status_change_time = NULL
                                    else:
                                        ak_status_change_time = "'{m}'".format(m=ak_status_change_time_old)
                                    if ak_status_old != ak_status:     #ak的状态发生更新
                                        ak_status_change_time = "'{m}'".format(m=now_time)
                                        print('更新AK禁用时间',ak_status_change_time)
                                    try:
                                        time_old = old_result[0]['update_time'].strftime("%Y-%m-%d %H:%M:%S")
                                    except Exception as e:
                                        print(e)
                                        time_old = NULL
                                    if login_enable != login_enable_old or last_login_time != last_login_time_old or polices_json != policies_old or ak_status != ak_status_old or last_use_time != last_use_time_old or now_time != time_old:
                                        sql = "update %s set status = %s,last_use_time = %s, account_login_enable = %s,account_last_login_time = %s, policies = '%s', " \
                                              "update_time = '%s', ak_status_change_time = %s where accesskey_id = '%s';" % (
                                                self.ak_list_tablename, ak_status, last_use_time, login_enable,
                                                  last_login_time, polices_json,
                                                  now_time, ak_status_change_time, ak_id)
                                        try:
                                            self.mysql_conn_dict.update(sql)
                                        except Exception as e:
                                            print('ERROR:',e)
                                            self.mysql_conn_dict.dispose()
                                            return False
                elif ak_section.startswith('tencentcloud'):
                    pass

        # 将已经不存在的ak从数据库中delete
        sql_ak = "select accesskey_id from %s" % self.ak_list_tablename
        try:
            result = self.mysql_conn_dict.select(sql_ak)
        except Exception as e:
            print('ERROR:',e)
        else:
            print('del result', result)
            sql_ak_list = []
            for s in result:
                sql_ak_list.append(s['accesskey_id'])
            del_list = [y for y in sql_ak_list if y not in ak_id_list]
            for del_ak in del_list:
                sql = "delete from %s where accesskey_id = '%s'" % (self.ak_list_tablename, del_ak)
                try:
                    self.mysql_conn_dict.delete(sql)
                except Exception as e:
                    print('ERROR:',e)

        #exec_ak_usefor.query_ak_usrfor()
        # 恢复状态, 之后的print内容都不捕获了
        #sys.stdout = current
        self.mysql_conn_dict.dispose()
        return True

if __name__ == "__main__":
    print("开始：" ,time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    X = GetRamInfo()
    X.get_ak_list()
    print("结束：" ,time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
