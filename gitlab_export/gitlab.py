from __future__ import print_function
import requests
import urllib
import sys
import time
import os
import re


class Api:
    '''Api class for gitlab'''

    def __init__(self, gitlab_url, token, ssl_verify=True):
        '''Init config object'''
        self.headers = {"PRIVATE-TOKEN": token}
        self.api_url = gitlab_url + "/api/v4"
        self.download_url = None
        self.project_array = False
        self.ssl_verify = ssl_verify

    def __api_archive(self, project_url):
        '''Send archive request to API'''
        self.download_url = None
        try:
            return requests.post(
                self.api_url + "/projects/" +
                project_url + "/archive",
                headers=self.headers,
                verify=self.ssl_verify)
        except requests.exceptions.RequestException as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def __api_export(self, project_url):
        '''Send export request to API'''
        self.download_url = None
        try:
            return requests.post(
                self.api_url + "/projects/" +
                project_url + "/export",
                headers=self.headers,
                verify=self.ssl_verify)
        except requests.exceptions.RequestException as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def __api_import(self, project_name, namespace, filename):
        '''Send import request to API'''
        data = {
            "path": project_name,
            "namespace": namespace,
            "overwrite": True}
        try:
            return requests.post(
                self.api_url + "/projects/import",
                data=data,
                files={"file": open(filename, 'rb')},
                verify=self.ssl_verify,
                headers=self.headers)
        except requests.exceptions.RequestException as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def __api_archive_status(self, project_url):
        '''Check project archive status'''
        r = requests.get(
            self.api_url+"/projects/" + project_url,
            verify=self.ssl_verify,
            headers=self.headers)

        status_archive = False

        if ((float(r.status_code) >= 200) and (float(r.status_code) < 300)):
            # Api good, check for status
            s = ""

            # Check API reply status
            if (r.status_code == requests.codes.ok):
                json = r.json()

                # Check export status
                if "archived" in json.keys():
                    s = json["archived"]
                    # If is set to true means project is archived
                    if s == True:
                        status_archive = True
            else:
                print("API not respond well with %s %s" % (
                    str(r.status_code),
                    str(r.text)),
                    file=sys.stderr)
                return False
        else:
            print("API not respond well with %s %s" % (
                str(r.status_code),
                str(r.text)),
                file=sys.stderr)
            return False

        return status_archive

    def __api_status(self, project_url):
        '''Check project status'''
        return requests.get(
            self.api_url + "/projects/" +
            project_url + "/export",
            verify=self.ssl_verify,
            headers=self.headers)

    def __api_get(self, endpoint):
        ''' Get api endpoint data '''
        try:
            return requests.get(
                self.api_url + endpoint,
                verify=self.ssl_verify,
                headers=self.headers)
        except requests.exceptions.RequestException as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def __api_post(self, endpoint, data):
        ''' POST api endpoint data '''
        try:
            return requests.post(
                self.api_url + endpoint,
                data=data,
                verify=self.ssl_verify,
                headers=self.headers)
        except requests.exceptions.RequestException as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def __api_import_status(self, project_url):
        '''Check project import status'''
        return requests.get(
            self.api_url+"/projects/" +
            project_url + "/import",
            verify=self.ssl_verify,
            headers=self.headers)

    def project_archive(self, project_path):
        ''' Archive project in Gitlab'''
        url_project_path = urllib.parse.quote(project_path, safe='')

        # Check if project is not already archived.
        status_archive = self.__api_archive_status(url_project_path)

        # If it is not archived...
        if not status_archive:
            print('not archived yet')
            r = self.__api_archive(url_project_path)
            if ((float(r.status_code) >= 200) and (float(r.status_code) < 300)):
                # Check status again after archive
                time.sleep(5) # Wait a little bit
                status_archive = self.__api_archive_status(url_project_path)
                if not status_archive:
                    print('{} has not been archived - something went wrong.'.
                            format(os.path.basename(project_path)))
                    sys.exit(1)
                else:
                    print('{} project has been successfully archived in old location.'.
                            format(os.path.basename(project_path)))
            else:
                print("API not respond well with %s %s" % (
                    str(r.status_code),
                    str(r.text)),
                    file=sys.stderr)
                sys.exit(1)
        else:
            print('{} project is already archived.'.format(os.path.basename(project_path)))

        return status_archive

    def project_list(self, path_glob="", membership="True"):
        ''' List projects based on glob path '''
        urlpath = '/projects?simple=True&membership=%s&per_page=50' % (membership)
        page = 1
        output = []
        if not self.project_array:
            while True:
                r = self.__api_get(urlpath + "&page=" + str(page))
                if r.status_code == 200:
                    json = r.json()
                    if len(json) > 0:
                        for project_data in r.json():
                            ppath = project_data["path_with_namespace"]
                            output.append(ppath)
                        page += 1
                    else:
                        break
                else:
                    print("API returned %s" % (str(r.status_code)), file=sys.stderr)
                    return False
            self.project_array = output

        # Compare glob to projects
        output = []
        for project in self.project_array:
            if re.match(path_glob, project):
                output.append(project)

        return output

    def project_export(self, project_path, max_tries_number):
        ''' Export Gitlab project
        When project export is finished, store download URLs
        in objects variable download_url ready to be downloaded'''

        url_project_path = urllib.parse.quote(project_path, safe='')

        # Let's export project
        r = self.__api_export(url_project_path)
        if ((float(r.status_code) >= 200) and (float(r.status_code) < 300)):
            # Api good, check for status
            max_tries = max_tries_number
            s = ""
            status_export = False
            while max_tries != 0:
                # Decrement tries
                max_tries -= 1

                try:
                    r = self.__api_status(url_project_path)
                except requests.exceptions.RequestException as e:
                    print(e, file=sys.stderr)
                    return False

                # Check API reply status
                if (r.status_code == requests.codes.ok):
                    json = r.json()

                    # Check export status
                    if "export_status" in json.keys():
                        s = json["export_status"]
                        # Export finished and _links appear in response
                        if s == "finished" and "_links" in json.keys():
                            status_export = True
                            break

                        if s == "queued" or s == "finished" or s == "started" or s == "regeneration_in_progress":
                            # Reset counter, we are waiting for export
                            max_tries = max_tries_number
                    else:
                        s = "unknown"

                else:
                    print("API not respond well with %s %s" % (
                        str(r.status_code),
                        str(r.text)),
                        file=sys.stderr)
                    break

                # Wait litle bit
                time.sleep(5)

            if status_export:
                if "_links" in json.keys():
                    self.download_url = json["_links"]
                    return True
                else:
                    print("Unable to find download link in API response: %s" % (str(json)))
                    return False
            else:
                print("Export failed, %s" % (str(r.text)), file=sys.stderr)
                return False

        else:
            print("API not respond well with %s %s" % (
                str(r.status_code),
                str(r.text)),
                file=sys.stderr)
            return False

    def project_import(self, project_path, filepath):
        ''' Import project to GitLab from file'''
        url_project_path = urllib.parse.quote(project_path, safe='')
        project_name = os.path.basename(project_path)
        namespace = os.path.dirname(project_path)

        # Let's import project
        r = self.__api_import(project_name, namespace, filepath)
        if ((float(r.status_code) >= 200) and (float(r.status_code) < 300)):
            # Api good, check for status
            s = ""
            status_export = False
            while True:
                r = self.__api_import_status(url_project_path)

                # Check API reply status
                if (r.status_code == requests.codes.ok):
                    json = r.json()

                    # Check export status
                    if "import_status" in json.keys():
                        s = json["import_status"]
                        if s == "finished":
                            status_import = True
                            break
                        elif s == "failed":
                            status_import = False
                            break
                    else:
                        s = "unknown"

                else:
                    print("API not respond well with %s %s" % (
                        str(r.status_code),
                        str(r.text)),
                        file=sys.stderr)
                    break

                # Wait litle bit
                time.sleep(1)

            if status_import:
                return True
            else:
                print("Import failed, %s" % (str(r.text)), file=sys.stderr)
                return False

        else:
            print("API not respond well with %s %s" % (
                str(r.status_code),
                str(r.text)),
                file=sys.stderr)
            print(r.text, file=sys.stderr)
            return False
