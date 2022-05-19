#!/usr/bin/env python3

from __future__ import print_function
import sys
import os
import argparse
import yaml
from datetime import date
import requests
# Find our libs
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from gitlab_export import config
from gitlab_export import gitlab as gitlab_cls

return_code = 0

if __name__ == '__main__':
    # Parsing arguments
    parser = argparse.ArgumentParser(
        description="""
        GitLab Project Import is
        small project using Gitlab API for exporting whole gitlab
        project with wikis, issues etc.
        Good for migration or simple backup your gitlab projects.
        """,
        epilog='Created by Robert Vojcik <robert@vojcik.net>')

    # Arguments
    parser.add_argument(
        '-c', dest='config', default='config.yaml',
        help='config file')
    parser.add_argument(
        '-f', dest='filepath', default=False,
        help='Path to gitlab exported project file')
    parser.add_argument(
        '-p', dest='project_path', default=False,
        help='Project path')
    parser.add_argument(
        '-d', dest='debug', default=False, action='store_const', const=True,
        help='Debug mode')
    parser.add_argument(
        '-a', dest='archive_project_path', default=False,
        help='Project you want to archive')

    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print("Unable to find config file %s" % (args.config))

    c = config.Config(args.config)
    token = c.config["gitlab"]["access"]["token"]
    gitlab_url = c.config["gitlab"]["access"]["gitlab_url"]
    ssl_verify = c.config["gitlab"]["access"]["ssl_verify"]

    # Init gitlab api object
    if args.debug:
        print("%s, token" % (gitlab_url))
    gitlab = gitlab_cls.Api(gitlab_url, token, ssl_verify)

    # import project
    if args.project_path and args.filepath and os.path.isfile(args.filepath):
        if args.debug:
            print("Importing %s" % (args.project_path))
        status = gitlab.project_import(args.project_path, args.filepath)

        # Import successful
        if status:
            print("Import success for %s" % (args.project_path))
            # If we want to archive already imported project in it's old location.
            if args.archive_project_path:
                print('{} project will be archived in old location.'.format(args.project_path))
                try:
                    archive_token = c.config["gitlab"]["archive"]["token"]
                    archive_gitlab_url = c.config["gitlab"]["archive"]["gitlab_url"]
                except KeyError as key:
                    print('{} key does not exist in the config file.'.format(key))
                    sys.exit(1)

                # Let's check if project we want to archive exists in new location after import.
                if gitlab:
                    project_dir = os.path.dirname(args.project_path)
                    project_list = gitlab.project_list(path_glob=project_dir)

                    if args.project_path in project_list:
                        # Now we can archive project we imported.
                        archive_gitlab = gitlab_cls.Api(archive_gitlab_url, archive_token, ssl_verify)

                        if archive_gitlab:
                            status = archive_gitlab.project_archive(project_path=args.archive_project_path)
                    else:
                        print('{} has not been imported to Gitlab so cannot be archived in former location.'
                                .format(args.project_path))
                        sys.exit(1)
            sys.exit(0)
        else:
            print("Import was not successful")
            sys.exit(1)
    else:
        print("Error, you have to specify correct project_path and filepath")
        sys.exit(1)