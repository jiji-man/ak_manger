#!/usr/bin/env python
#coding=utf-8

import json
from django.http import HttpResponse
from src.task.ak_manger import get_ak_info


# 将返回值打包成字典转为json格式
def to_json_result(code,message,success,data):
    dict_response = {'code' : code, 'success' : success, 'message' : message, 'body' : data}
    result = json.dumps(dict_response)
    return result


def ak_sync(request):
    from src.lib import django_api
    django_api.DjangoApi().os_environ_update()
    data_list = []
    code = 500
    success = False
    status_message = 'access keys update is fail.'
    if request.method == 'GET':  # 当提交表单时
        get_ram_info = get_ak_info.GetRamInfo()
        result = get_ram_info.get_ak_list()
        if result:
            code = 200
            success = True
            status_message = 'access keys update is success.'
    else:
        status_message = 'error : Please use get request.'
    result_json = to_json_result(code, status_message, success, data_list)
    return HttpResponse(result_json)


if __name__ == "__main__":
    ak_sync('xxx')
