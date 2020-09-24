#!/usr/bin/env python3
# coding:utf-8
import time
import sys
import threading
# 项目的lib
from src.lib import db_mysql
from src.lib import get_gitlab


class GitLabSearch:
    def __init__(self):
        self.gl = get_gitlab.GitlabAPI()
        self.ak_list_completed = []
        self.ak_list_table_name = 'ak_list'
        self.ak_use_info_table_name = 'ak_use_info'
        self.usr_info_type = 'gitlab'

    def get_project_id_list(self):
        project_id_list = []
        try:
            project_id_list = self.gl.get_allprojects_list()
            #print(len(project_id_list), project_id_list)
        except Exception as e:
            print('Error:获取project id 失败，',e)
        else:
            n = 0
            print('{datetime}, 开始查找出有效的project' .format(datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
            for project_id in project_id_list:
                # print(project_id, n)
                try:
                    branch_list = self.gl.get_project_branch(project_id)
                except Exception as e:
                    n = n + 1
                    project_id_list.remove(project_id)
                    project_name = self.gl.get_project_name(project_id)
                    print("项目: %s , ID:%s ,获取项目分支列表失败！Error code : %s" % (project_name, project_id, e))
                    pass
                else:
                    if not branch_list:
                        n = n + 1
                        project_id_list.remove(project_id)

            print("{datetime}, 查找出project {n} 个： {m}" .format(datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), n = len(project_id_list),m = project_id_list))
        return project_id_list

    @staticmethod
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
            finally:
                mysql_conn_dict.dispose()
            attempts += 1
        return result

    @staticmethod
    def get_sql_insert_result(sql):
        attempts = 0
        status = False
        while attempts < 3 and not status:
            try:
                mysql_conn_dict = db_mysql.MyPymysqlPoolDict()
                mysql_conn_dict.insert(sql)
            except Exception as e:
                print(e)
            else:
                status = True
            finally:
                mysql_conn_dict.dispose()
            attempts += 1
        return True

    @staticmethod
    def get_sql_update_result(sql):
        attempts = 0
        status = False
        while attempts < 3 and not status:
            try:
                mysql_conn_dict = db_mysql.MyPymysqlPoolDict()
                mysql_conn_dict.update(sql)
            except Exception as e:
                print(e)
            else:
                status = True
            finally:
                mysql_conn_dict.dispose()
            attempts += 1
        return True

    @staticmethod
    def get_sql_delete_result(sql):
        attempts = 0
        status = False
        while attempts < 3 and not status:
            try:
                mysql_conn_dict = db_mysql.MyPymysqlPoolDict()
                mysql_conn_dict.delete(sql)
            except Exception as e:
                print(e)
            else:
                status = True
            finally:
                mysql_conn_dict.dispose()
            attempts += 1
        return True

    def exec_gitlab(self, task_id=0):
        # 保存当前的sys.stdout状态, 开始捕获当前的输出
        path = './ak_leak.log'
        current = sys.stdout
        f = open(path, 'w')
        # 这一步实际是sys.stdout.write, 当sys捕获到了print输出的时候, 就写入f里面
        sys.stdout = f

        sql_select_ak = "select accesskey_id from %s WHERE status = 1 and policies <> 'NULL'; " % self.ak_list_table_name
        select_ak_result = self.get_sql_select_result(sql_select_ak)

        ak_list = []
        if select_ak_result:
            m = 0
            for  i in select_ak_result:
                m = m + 1
                ak_list.append(i['accesskey_id'])
                #if m == 12:
                    #break
            print("查询到 {n} 个ak：{m}".format(n=len(ak_list), m=ak_list))
            self.project_id_list = self.get_project_id_list()
            #ak_list = ['LTAI4FtvAS1F3kvCtuNojx7B', 'LTAIYASREabK6nZC', 'LTAI4FujoeQpXxTvgnj7We7Y',
            #           'LTAI4Fmi6C5LHeYV7N8H4BEK', 'LTAI4GBw4DSdnCnfBkjaTs6b', 'LTAI4FjGFzmW1DdDre7W9W4e',
            #           'LTAIFka39fEtZGtN', 'LTAI4GBw4DSdnCnfBkjaTs6b']
            attempts = 1
            status = False
            ak_list_be_check = ak_list
            while attempts < 4 and not status:
                if ak_list_be_check:
                    self.exec_thread(ak_list_be_check)
                    c = [x for x in self.ak_list_completed if x in ak_list]
                    ak_list_be_check = [y for y in (self.ak_list_completed + ak_list) if y not in c]  # 获取没有成功的遍历查询到的ak
                    print("第 %s 轮的ak查询已完成,完成ak查询共 %s 个,未完成遍历查询的ak %s 个.未完成的ak:[ %s ]" % (
                        attempts, len(self.ak_list_completed), len(ak_list) - len(self.ak_list_completed),
                        ak_list_be_check))
                    attempts += 1
                else:
                    status = True

            print("退出主线程", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        else:
            print("Warn：数据库 ak_list 未查询到有效ak..")


        #从ak泄露表中删除已经不存在的ak
        sql_select_ak_leak_id = "select DISTINCT ak_list_id from %s ; " % self.ak_use_info_table_name
        select_ak_leak_id_result = self.get_sql_select_result(sql_select_ak_leak_id)
        ak_leak_id_list = []
        if select_ak_leak_id_result:
            for i in select_ak_leak_id_result:
                ak_leak_id_list.append(i['ak_list_id'])

            sql_select_ak_id = "select id from %s ; " % self.ak_list_table_name
            select_ak_id_result = self.get_sql_select_result(sql_select_ak_id)
            ak_id_list = []
            if select_ak_id_result:
                for i in select_ak_id_result:
                    ak_id_list.append(i['id'])

            ak_id = [ak_id for ak_id in ak_leak_id_list if ak_id not in ak_id_list]
            if ak_id:
                for i in ak_id:
                    delete_ak_leak = "DELETE FROM %s WHERE ak_list_id = '%s' ;" % (self.ak_use_info_table_name, i)
                    self.get_sql_delete_result(delete_ak_leak)

        # 恢复状态, 之后的print内容都不捕获了
        sys.stdout = current
        return True

    #创建多个线程并执行线程
    def exec_thread(self, ak_list):
        thread_num = 16     #默认创建16个线程
        thread_task_num = len(ak_list) // thread_num     #取整,每个线程需要跑的ak数量
        remainder = len(ak_list) - thread_num * (len(ak_list) // thread_num)        #取余
        if thread_task_num == 0:
            thread_num = remainder
        # 创建新线程，将ak_list按照线程数均分开
        for i in range(1,thread_num+1):
            thread_name = 'Thread-' + str(i)
            if remainder == 0:
                s =0
            else:
                s = 1
            if i == 1 :
                locals()['thread' + str(i)] = threading.Thread(target=self.ak_in_gitlab_matching, args=([ak_list[:(thread_task_num+s) * i]]))
            elif i == thread_num:
                locals()['thread' + str(i)] = threading.Thread(target=self.ak_in_gitlab_matching, args=([ak_list[(thread_task_num+s)*(i-1):]]))
            else:
                locals()['thread' + str(i)] = threading.Thread(target=self.ak_in_gitlab_matching, args=([ak_list[(thread_task_num+s)*(i-1):(thread_task_num+s)*i]]))


        # 开启多线程
        for i in range(1,thread_num+1):
            thread_name = 'Thread-' + str(i)
            print("开始线程：" + thread_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            locals()['thread' + str(i)].start()
            time.sleep(5)
        for i in range(1,thread_num+1):
            thread_name = 'Thread-' + str(i)
            locals()['thread' + str(i)].join()
            print("退出线程：" + thread_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    #将ak在project里匹配查找
    def ak_in_gitlab_matching(self, ak_list):
        for ak in ak_list:
            project_name_list = []
            for project_id in self.project_id_list:
                attempts = 0
                status = False
                while attempts < 3 and not status:
                    try:
                        result = self.gl.search_ak(project_id, ak)
                        print(project_id, 'and', ak, 'and', result)
                        if result:
                            print("ak字段匹配成功",project_id, 'and', ak, 'and', result)
                            project_name = self.gl.get_project_name(project_id)
                            project_name_list.append(project_name)
                    except Exception as e:
                        print("ak字段查找失败",project_id, 'and', ak, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                        time.sleep(10)
                    else:
                        status = True
                    attempts += 1
            print("{ak} 匹配到的project 如下：{s}".format(ak = ak, s = project_name_list))
            if project_name_list:
                sql_select_ak_id = "select id from %s WHERE accesskey_id = '%s'; " % (self.ak_list_table_name, ak )
                select_ak_id_result = self.get_sql_select_result(sql_select_ak_id)
                print("select_ak_id_result",select_ak_id_result)
                ak_id = select_ak_id_result[0]['id']

                sql_select_ak_use_info = "select count(*) from %s WHERE ak_list_id = '%s' AND use_name = '%s' ; " % (self.ak_use_info_table_name, ak_id, self.usr_info_type)
                #sql_select_ak_use_info = "select count(*) from %s LEFT JOIN %s ON %s.ak_list_id = %s.id WHERE accesskey_id = '%s' AND use_name = '%s' ; "%(
                #    self.ak_use_info_table_name, self.ak_list_table_name, self.ak_use_info_table_name, self.ak_list_table_name, ak, self.usr_info_type)
                select_ak_use_info_result = self.get_sql_select_result(sql_select_ak_use_info)
                ak_use_info_count = select_ak_use_info_result[0]['count(*)']
                print('select_ak_use_info_result',select_ak_use_info_result)
                if ak_use_info_count == 0:
                    sql_insert_ak_use_info = "insert into %s SET ak_list_id = '%s',use_name = '%s', use_detail = \"%s\", start_time = %s; " % (
                    self.ak_use_info_table_name, ak_id, self.usr_info_type, project_name_list, int(time.time()))

                    self.get_sql_insert_result(sql_insert_ak_use_info)
                else:
                    update_ak_use_info_result = "update %s SET use_detail = \"%s\" WHERE ak_list_id = '%s'AND use_name = '%s';" % (self.ak_use_info_table_name, project_name_list, ak_id, self.usr_info_type)
                    print(update_ak_use_info_result)
                    self.get_sql_update_result(update_ak_use_info_result)

            self.ak_list_completed.append(ak)
            print("插入已完成查找的ak", ak, self.ak_list_completed)

        return self.ak_list_completed


if __name__ == "__main__":
    a = GitLabSearch()
    a.exec_gitlab()
