#!/usr/bin/env python

import json
import os
import socket
import sys
import tornado.httpclient
import unittest
import SOAPpy
import tarfile

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../lib"))
import appscale_info

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))
import helper
import hermes

from flexmock import flexmock

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../AppServer'))
from google.appengine.api.appcontroller_client import AppControllerClient

from hermes import deploy_sensor_app
from hermes import poll
from hermes import send_cluster_stats
from hermes import shutdown
from hermes import signal_handler
from tornado.ioloop import IOLoop

class TestHelper(unittest.TestCase):
  """ A set of test cases for Hermes top level functions. """

  DEPLOYMENT_ID = "deployment_id"

  def test_poll(self):
    # Assume deployment is not registered.
    flexmock(helper).should_receive('get_deployment_id').and_return(None)
    poll()

    flexmock(helper).should_receive('get_deployment_id').\
      and_return('deployment_id')
    br_nodes = [
      {helper.NodeInfoTags.HOST: 'node1'},
      {helper.NodeInfoTags.HOST: 'node2'},
    ]
    flexmock(helper).should_receive('get_node_info').and_return(br_nodes)

    # Assume backup and recovery service is down.
    http_client = flexmock()
    http_client.should_receive('fetch').and_raise(socket.error)
    flexmock(tornado.httpclient).should_receive('HTTPClient').\
      and_return(http_client)
    poll()

    # Assume backup and recovery service is up.
    response = flexmock(body=json.dumps({'status': 'up'}))
    http_client.should_receive('fetch').and_return(response)
    flexmock(tornado.httpclient).should_receive('HTTPClient').\
      and_return(http_client)
    flexmock(json).should_receive('dumps').and_return('{}')
    flexmock(helper).should_receive('create_request').and_return()

    # Assume request to the AppScale Portal is successful.
    flexmock(helper).should_receive('urlfetch').\
      and_return({"success": True, "body": {}})
    flexmock(helper).should_receive('urlfetch_async').and_return()
    poll()

    # Assume request to the AppScale Portal is successful.
    flexmock(helper).should_receive('urlfetch').\
      and_return({"success": False, "reason": "error"})
    poll()

  def test_send_all_stats(self):
    # Assume deployment is not registered.
    flexmock(helper).should_receive('get_deployment_id').and_return(None)
    send_cluster_stats()

    flexmock(helper).should_receive('get_deployment_id').\
      and_return('deployment_id')

    fake_stats = {}
    flexmock(helper).should_receive('get_cluster_stats').and_return(fake_stats)
    flexmock(helper).should_receive('create_request').and_return()
    flexmock(helper).should_receive('urlfetch').\
      and_return({"success": True, "body": {}})
    send_cluster_stats()

  def test_signal_handler(self):
    flexmock(IOLoop.instance()).should_receive('add_callback').and_return()\
      .times(1)
    signal_handler(15, None)

  def test_shutdown(self):
    flexmock(IOLoop.instance()).should_receive('stop').and_return().times(1)
    shutdown()

  def test_sensor_app_not_deployed_when_deployment_not_registered(self):
    # Test sensor app is not deployed when deployment is not registered.
    flexmock(helper).should_receive('get_deployment_id').and_return(None)
    flexmock(hermes).should_receive('create_appscale_user').and_return().\
      times(0)
    flexmock(hermes).should_receive('create_xmpp_user').and_return().\
      times(0)
    flexmock(AppControllerClient).should_receive('upload_app').and_return().\
      times(0)
    deploy_sensor_app()

    # Test sensor app is not deployed when it is already running.
    flexmock(helper).should_receive('get_deployment_id').and_return(
      self.DEPLOYMENT_ID)
    flexmock(appscale_info).should_receive('get_secret').and_return(
      "fake_secret")
    flexmock(appscale_info).should_receive('get_db_master_ip').and_return()
    fake_uaserver = flexmock(name='fake_uaserver')
    # Assume appscalesensor app already running.
    fake_uaserver.should_receive('is_app_enabled').with_args(
      'appscalesensor', 'fake_secret').and_return("true")
    flexmock(SOAPpy)
    SOAPpy.should_receive('SOAPProxy').and_return(fake_uaserver)
    flexmock(AppControllerClient).should_receive('upload_app').and_return(). \
      times(0)
    deploy_sensor_app()

    # Test sensor app is not deployed when the app is not currently running but
    # there was an error in creating a new user.
    fake_uaserver.should_receive('is_app_enabled').with_args(
      'appscalesensor', 'fake_secret').and_return("false")
    # Assume error while creating a new user.
    fake_uaserver.should_receive('does_user_exist').and_return("false")
    fake_uaserver.should_receive('commit_new_user').and_return("false")
    flexmock(hermes).should_receive('create_appscale_user').and_return(). \
      times(1)
    flexmock(AppControllerClient).should_receive('upload_app').and_return(). \
      times(0)
    deploy_sensor_app()

    # Test sensor app is deployed after successfully creating a new user or
    # with an existing user.
    fake_uaserver.should_receive('commit_new_user').and_return("true")
    flexmock(tarfile).should_receive('open').and_return(tarfile.TarFile)
    flexmock(tarfile.TarFile).should_receive('add').and_return()
    flexmock(tarfile.TarFile).should_receive('close').and_return()
    flexmock(appscale_info).should_receive('get_appcontroller_client').and_return(
      AppControllerClient)
    flexmock(hermes).should_receive('create_appscale_user').and_return(True)
    flexmock(hermes).should_receive('create_xmpp_user').and_return(True)
    flexmock(AppControllerClient).should_receive('upload_app').and_return(). \
      times(1)
    deploy_sensor_app()

if __name__ == "__main__":
  unittest.main()
