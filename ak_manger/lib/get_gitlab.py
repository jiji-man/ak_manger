#!/usr/bin/env python3
# coding:utf-8

import gitlab
import os
import configparser
import time
# 从配置文件里读取gitlab的地址和token
file_path = os.path.join(os.path.dirname(__file__), "../../conf/key.conf")
cf = configparser.ConfigParser()
cf.read(file_path,encoding='utf-8')
section = 'gitlab'
url = cf.get(section, 'url')
token = cf.get(section, 'token')

class GitlabAPI(object):
    def __init__(self, *args, **kwargs):
        #self.gl = gitlab.Gitlab.from_config('git', ['python-gitlab.cfg'])
        print(url, token)
        self.gl = gitlab.Gitlab(url, token)
    #得到所有project id 列表
    def get_allprojects_list(self):
        projects = self.gl.projects.list(all=True)
        print(projects)
        project_id_list = []
        for project in projects:
            project_id_list.append(project.id)
        return project_id_list

    def allgroups(self):
        #######获取gitlab的所有group名称以及ID###
        all_groups = self.gl.groups.list(all=True)
        for group in all_groups:
            print(group.name,group.id)

    def allusers(self):
        #######获取gitlab的所有user名称以及ID###
        users = self.gl.users.list(all=True)
        for user in users:
            print(user.username,user.id,user.name,user.state)

    # 获取gitlab指定组内所有user以及project名称以及ID信息，本例中组ID为58###
    def assgroup(self,gid):
        group = self.gl.groups.get(gid)
        print(group.name)
        #members = group.members.list(all=True)
        #for me in members:
        #    print me.username,me.id
        projects = group.projects.list(all=True)
        for project in projects:
            print(group.name,project.name)
        #######################################
    #通过用户名获取用户id
    def get_user_id(self, username):
        user = self.gl.users.get_by_username(username)
        return user.id
    #通过组名获取组id
    def get_group_id(self, groupname):
        group = self.gl.groups.get(groupname, all=True)
        return group.id
    #获取用户所拥有的项目
    def get_user_projects(self, userid):
        projects = self.gl.projects.owned(userid=userid, all=True)
        result_list = []
        for project in projects:
            result_list.append(project.http_url_to_repo)
        return result_list

    #获取组内项目
    def get_group_projects(self, groupname):
        group = self.gl.groups.get(groupname, all=True)
        projects = group.projects.list(all=True)
        return projects

    #通过项目id获取文件内容
    def getContent(self, projectID):
        projects = self.gl.projects.get(projectID)
        f = projects.files.get(file_path='git-test.log', ref='master')
        content = f.decode()
        print(content)
        return content.decode('utf-8')

    #获取所有群组
    def get_all_group(self):
        return self.gl.groups.list(all=True)

    # 获取项目分支列表
    def get_project_branch(self,project_id):
        project = self.gl.projects.get(project_id)
        #print(project)
        self.branch_list = project.branches.list()
        #print(self.branch_list)
        return self.branch_list
    # 获取项目名
    def get_project_name(self,project_id):
        project = self.gl.projects.get(project_id)
        #print(project)
        self.project_name = project.name
        #print(self.branch_list)
        return self.project_name
    # 代码中查找ak
    def search_ak(self,project_id,ak):
        project = self.gl.projects.get(project_id)
        self.result = project.search('blobs', ak,ref = '')
        return self.result

    # 用项目id获取项目
    def get_project_id(self,project_id):
        project = self.gl.projects.get(project_id)
        return project

    # 由于是递归方式下载的所以要先创建项目相应目录
    def create_dir(self, dir_name):
        if not os.path.isdir(dir_name):
            print("\033[0;32;40m开始创建目录: \033[0m{0}".format(dir_name))
            os.makedirs(dir_name)
            time.sleep(0.1)
    #下载代码
    def start_get(self,project_id):
        project = self.get_project_id(project_id)
        info = project.repository_tree(all=True, recursive=True, as_list=True)
        print('info',info)
        file_list = []
        if not os.path.isdir(self.root_path):
            os.makedirs(self.root_path)
        os.chdir(self.root_path)
        # 调用创建目录的函数并生成文件名列表
        for info_dir in range(len(info)):
            if info[info_dir]['type'] == 'tree':
                dir_name = info[info_dir]['path']
                self.create_dir(dir_name)
            else:
                file_name = info[info_dir]['path']
                file_list.append(file_name)
        for info_file in range(len(file_list)):
            # 开始下载
            getf = project.files.get(file_path=file_list[info_file], ref='master')
            content = getf.decode()
            with open(file_list[info_file], 'wb') as code:
                print("\033[0;32;40m开始下载文件: \033[0m{0}".format(file_list[info_file]))
                code.write(content)


if __name__ == "__main__":
    a = GitlabAPI()
    project = a.get_project_id(1408)
    print(project)
