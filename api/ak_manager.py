#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import sys, time
sys.path.append("..")
from django.http import HttpResponse
from src.lib import db_mysql
from django.views.decorators.clickjacking import xframe_options_sameorigin
try:
    import simplejson as json
except ImportError:
    import json


def query_ak_info_list(request):
    table_name = 'ak_list'
    accesskey_id = request.GET['accessKeyId']
    status = request.GET['status']
    cost_item_id = request.GET['costItemId']
    page = int(request.GET['page'])
    limit = int(request.GET['limit'])

    mysql_conn = db_mysql.MyPymysqlPoolDict()
    offset = (page-1)*limit     # （当前页数-1）*每页数量 = 每页的开始位置

    data_list = []
    body_dict = {}
    from src.lib import django_api
    django_api.DjangoApi().os_environ_update()
    result_dict = {'code': 500, 'success': False, 'message': "fail"}

    # 获取总条数，用于返回的json里面输出
    sql = "select count(`id`) as count from %s where `accesskey_id` like '%%%s%%' and status like '%%%s%%' and " \
          "cost_item_id like '%%%s%%'" % (table_name, accesskey_id, status, cost_item_id)
    try:
        print(sql)
        total_count = int(mysql_conn.select(sql)[0]['count'])
    except Exception as e:
        print("except: %s" % e)
        result_dict['message'] = "查询AK数量异常"
        total_count = -1
        mysql_conn.dispose()
    else:
        if total_count > 0:
            # 查询ak信息
            sql1 = "select * from %s where `accesskey_id` like '%%%s%%' and status like '%%%s%%' and " \
                  "cost_item_id like '%%%s%%' limit %s,%s" \
                  % (table_name, accesskey_id, status, cost_item_id, offset, limit)
            # 查询ak的使用场景
            sql2 = "select * from ak_use_info"
            # 查询ak申请人信息
            sql3 = "select * from ak_apply_list"
            try:
                print("sql: ", sql1)
                tmp_result1 = mysql_conn.select(sql1)
                tmp_result2 = mysql_conn.select(sql2)
                tmp_result3 = mysql_conn.select(sql3)
            except Exception as e:
                result_dict['message'] = "查询具体AK信息异常"
            else:
                result_dict['code'] = 0
                result_dict['message'] = "success"
                result_dict['success'] = True
                for record in tmp_result1:
                    record.pop('update_time')
                    ak_list_id = record['id']
                    use_count = 0   # ak使用场景的计数，默认未使用
                    use_list = []   # 使用场景的列表
                    use_list_detail = {}     # 使用场景的明细列表
                    apply_info = {}
                    if record['policies']:
                        policies_num = len(record['policies'].split(','))
                    if record['last_use_time']:
                        record['last_use_time'] = record['last_use_time'].strftime("%Y-%m-%d %H:%M:%S")
                    if record['ak_status_change_time']:
                        record['ak_status_change_time'] = record['ak_status_change_time'].strftime("%Y-%m-%d %H:%M:%S")
                    if record['account_last_login_time']:
                        record['account_last_login_time'] = record['account_last_login_time'].strftime("%Y-%m-%d %H:%M:%S")
                    if tmp_result2:
                        for i in tmp_result2:
                            if ak_list_id == i['ak_list_id']:
                                use_count += 1
                                use_name = i['use_name']
                                use_detail = i['use_detail']
                                use_list.append(use_name)
                                use_list_detail[use_name] = use_detail
                    if tmp_result3:
                        for j in tmp_result3:
                            if ak_list_id == j['ak_list_id']:
                                j.pop('update_time')
                                from src.lib import time_api
                                j['start_time'] = time_api.timestamp_to_datetime(j['start_time'])
                                apply_info = j
                    record['use_num'] = use_count
                    record['policies_num'] = policies_num
                    record['use_list'] = use_list
                    record['use_list_detail'] = use_list_detail
                    record['applyInfo'] = apply_info
                data_list = tmp_result1
            finally:
                mysql_conn.dispose()
        else:
            result_dict['code'] = 0
            result_dict['message'] = "success"
            result_dict['success'] = True

    body_dict['data'] = data_list
    body_dict['count'] = total_count
    result_dict['body'] = body_dict
    result_json = json.dumps(result_dict, ensure_ascii=False)
    print(result_json)
    return HttpResponse(result_json, content_type="application/json,charset=utf-8")


def update_ak_apply_info(request):    # 更新ak的申请人信息接口
    print('111')
    result_dict = {'code': -1, 'success': False, 'message': 'fail'}
    from src.lib import django_api
    django_api.DjangoApi().os_environ_update()

    print(request.body.decode())

    if request.method != 'PUT':  # 当提交表单时
        result_dict['message'] = '请求方法错误, 需求PUT'
        result_json = json.dumps(result_dict, ensure_ascii=False)
        return HttpResponse(result_json, content_type="application/json,charset=utf-8")

    mysql_conn = db_mysql.MyPymysqlPoolDict()
    table_name = 'ak_apply_list'
    ak_list_id = json.loads(request.body.decode()).get('id')
    apply_owner = json.loads(request.body.decode()).get('applyInfo').get('apply_owner')
    apply_owner_tl = json.loads(request.body.decode()).get('applyInfo').get('apply_owner_tl')
    apply_owner_department = json.loads(request.body.decode()).get('applyInfo').get('apply_owner_department')
    apply_type = json.loads(request.body.decode()).get('applyInfo').get('apply_type')
    apply_reason = json.loads(request.body.decode()).get('applyInfo').get('apply_reason')
    start_time = int(time.time())
    print(ak_list_id, apply_owner, apply_owner_tl, apply_owner_department, apply_type, apply_reason)
    sql = "select id from %s where ak_list_id=%s" % (table_name, ak_list_id)

    try:
        # 使用编辑操作统一了新增和更新，因此首先判断ak_list_id是否存在，存在则update，否则insert
        tmp_result = mysql_conn.select(sql)
        if tmp_result:
            update_sql = "UPDATE %s SET apply_owner='%s', apply_owner_tl = '%s', apply_owner_department='%s', " \
                         "apply_type='%s', apply_reason='%s' where `ak_list_id`=%s" % \
                         (table_name, apply_owner, apply_owner_tl, apply_owner_department, apply_type, apply_reason,
                          ak_list_id)
            print('update_sql: ', update_sql)
            mysql_conn.update(update_sql)
        else:
            insert_sql = "INSERT INTO %s SET ak_list_id=%s, apply_owner='%s', apply_owner_tl='%s', " \
                         "apply_owner_department='%s', apply_type='%s', apply_reason='%s', start_time=%s" % \
                         (table_name, ak_list_id, apply_owner, apply_owner_tl, apply_owner_department, apply_type,
                          apply_reason, start_time)
            print('insert_sql: ', insert_sql)
            mysql_conn.insert(insert_sql)
    except Exception as e:
        print('update task exception: ', e)
        result_dict['message'] = "写入申请人信息异常"
    else:
        result_dict['code'] = 200
        result_dict['success'] = True
        result_dict['message'] = "写入申请人信息成功"
    finally:
        mysql_conn.dispose()

    result_json = json.dumps(result_dict, ensure_ascii=False)
    print(result_json)
    return HttpResponse(result_json, content_type="application/json,charset=utf-8")


if __name__ == "__main__":
    query_ak_info_list('xxx')
