#!/usr/bin/env python3
#
# Copyright (c) 2020 Fondazione Bruno Kessler
# Author(s): Cristina Costa (ccosta@fbk.eu)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.

"""LoRa NS Discovery Protocol Server."""
import json
import tornado.websocket
import logging

LOG = logging.getLogger("LoRaNSDPMainHandler")

from empower.managers.lommmanager.datatypes.eui64 import EUI64

class LNSDPMainHandler(tornado.websocket.WebSocketHandler):

    HANDLERS = [r"/router-info"]
    LABEL    = "LoRaWAN NS Discovery Server"
        
    @classmethod
    def urls(cls, kwargs={}):
        return [
            #(r'/router-info/', cls, kwargs),  # Route/Handler/kwargs
            (h, cls, kwargs) for h in cls.HANDLERS  # Route/Handler/kwargs
        ]
    
    def check_origin(self, origin):
        """ 
        By default, [check_origin] rejects all requests with an origin on 
        a host other than this one.
        This is a security protection against cross site scripting 
        attacks on browsers, since WebSockets are allowed to bypass the 
        usual same-origin policies and don’t use CORS headers.
        This is an important security measure; don’t disable it without 
        understanding the security implications. 
        In particular, if your authentication is cookie-based, you must 
        either restrict the origins allowed by check_origin() or implement 
        your own XSRF-like protection for websocket connections. 
        See these articles for more:
        https://devcenter.heroku.com/articles/websocket-security
        http://www.tornadoweb.org/en/stable/websocket.html#configuration

        """
        ## Alternative code:
        #allowed = ["https://site1.tld", "https://site2.tld"]
        #if origin not in allowed:
        #        return False
        return True
        
    
    def initialize(self, server):
        """Hook for subclass initialization. Called for each request.
        Tornado will automatically call this method with your custom arguments"""
        self.lgtw_id = None
        self.lns_id   = None
        self.uri      = None
        self.error    = None
        self.server   = server
        LOG.info("%s initialized", self.LABEL)        

    def to_dict(self):
        """Return dict representation of object."""
        return_value = {}
        return_value["router"] = self.lgtw_id
        return_value["muxs"]   = self.lns_id
        return_value["uri"]    = self.uri
        if self.error:
            return_value["error"]  = self.error
        return return_value

    def open(self):
        """On socket opened."""
        LOG.info("New WS LNS Discovery Protocol connection opened")
        pass

    def encode_message(self, message):
        """Encode JSON message."""
        self.write_message(json.dumps(message))

    def on_message(self, message):
        """Handle incoming message."""
        try:
            msg = json.loads(message)
            self.handle_message(msg)
        except ValueError:
            LOG.error("Invalid input: %s", message)

    def handle_message(self, msg):
        """Handle incoming message."""
        try:
            self.lgtw_id = EUI64(msg['router']).id6 
        except KeyError:
            LOG.error("Bad message formatting, 'router' information (Radio GTW EUI) missing")
            #self.stream.close()
            return
        
        
        LOG.info("New LNS discovery request from %s: %s", self.lgtw_id,  json.dumps(msg))        
        
        #for tenant in RUNTIME.tenants.values():
        #    for app in tenant.components.values():
        #        app.lgtw_new_lns_discovery_request(self.lgtw_id) # defined in app.py or event.py
        self.send_lns_discovery_request_replay()
        
        return
     
    def send_lns_discovery_request_replay(self):
        """Execute a remote command on LGTW."""
        reply_message = {"router":self.lgtw_id}
        for lns_euid in self.server.lnss:
            if self.lgtw_id in self.server.lnss[lns_euid].lgtws:
                reply_message["muxs"]    = lns_euid
                reply_message["router"]  = self.lgtw_id
                reply_message["uri"]     = self.server.lnss[lns_euid].uri + self.lgtw_id
                break   
        else:
            reply_message["error"] = "Unknown LoRaWAN Radio GTW (" + self.lgtw_id +")"

        LOG.info("LNS Discovery Request reply: %s", json.dumps(reply_message)) 
        self.write_message(json.dumps(reply_message))
        #self.stream.close()
        
    def on_close(self):
        LOG.error("WebSocket connection with %s closed", self.lgtw_id)
        self.lgtw_id = None
        self.lns_id   = None
        self.uri      = None
        self.error    = None


