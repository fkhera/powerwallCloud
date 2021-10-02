#!/usr/bin/env python
"""
Python class to interface with local Tesla Powerwall JSON API
https://github.com/piersdd/tesla-powerwall-json-py


Example:

import powerwall_site
gateway_host = '192.168.5.6'
password = 'ST17I0012345'
backup_reserve_percent = float("5.1")

tpw = powerwall_site.main('192.168.5.6', 'ST17I0012345')

"""


import json, time
import requests
from requests.exceptions import HTTPError, Timeout
import urllib3
urllib3.disable_warnings() # For 'verify=False' SSL warning
import logging
import urllib
import traceback
import os
import hashlib
import base64
import re
import urlparse
import random
import string

import authtoken
import sendEmail


# Tomorrow we fix time of use checking

_LOGGER = logging.getLogger(__name__)

# How the flow will change, there will be a refresh token
# Script will wake up, and check, refresh token, for the email item
# Validate is refresh token expired
# How do you know refresh token is expired?
# Maybe you don't know so you use refresh token everyday to get an access token
# Use Access Token to Exchange for Real Token
# If you get to a place to get a refresh token, save the token for the email
# If you do not have a refresh token, start the AUTH part to get a refresh token
# If you have a refresh token, use the refresh token to get new token


def main(emailItem, passwordItem):
    #Change these items
    gateway_host = 'owner-api.teslamotors.com'
    email = emailItem
    password = passwordItem
    backup_reserve_percent = float("0.0")

    logging.basicConfig(filename='powerwall_site.log', level=logging.WARNING)

    attempts = 0
    tpw = powerwall_site(gateway_host, password, email)  
    while 'fail' in tpw.token and attempts < 6:
        print ("attempts count: ", attempts)
        try:
            attempts = attempts + 1 
            # Get valid token from OAuth
            tpw.token = tpw.vaild_token_new()       
       

        # Get Product List
            tpw.productlist()

        # ## Set Battery to Charge with defined reserve percent - Uses 5% defined above
            real_mode = 'autonomous'
            tpw.operation_set(real_mode, backup_reserve_percent)
        except:
            # printing stack trace 
            traceback.print_exc()

    if attempts > 5: 
        print("Attempts exceeded")
        sendEmail.main(emailItem, 'Unable to set powerwall check reserve %, 5 attempts failed')


class powerwall_site(object):
    """Tesla Powerwall Sitemaster

    Attributes:
        token: for access to Powerwall gateway.
        running: Boolean
        uptime: in seconds
        connected_to_tesla: Boolean
        gateway_host: fqdn or IP address of gateway
        password: derivative of serial number
        battery_soc: percentage charge in battery
        backup_reserve_percent: backup event reserve limit for discharge

    """

    def __init__(self, gateway_host, password, email):
        """Return a new Powerwall_site object."""
        self.email = email
        self.token = 'fail'
        self.running = False
        # self.uptime = 0
        # self.connected_to_tesla = False
        self.gateway_host = gateway_host
        self.password = password
        self.battery_soc = 0
        self.backup_reserve_percent = 13.14159265358979
        self.real_mode = ''

        self.base_path = 'https://' + self.gateway_host
        self.auth_header = {'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + self.token}
        self.TESLA_CLIENT_ID='81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384'
        self.TESLA_CLIENT_SECRET='c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3'
        self.haveCar = True
        
        self.energy_site_id = []
        self.energy_base_url = self.base_path + '/api/1/energy_sites/'

        self.verifier_bytes = os.urandom(32)
        self.challenge = base64.urlsafe_b64encode(self.verifier_bytes).rstrip(b'=')
        self.challenge_bytes = hashlib.sha256(self.challenge).digest()
        self.challengeSum = base64.urlsafe_b64encode(self.challenge_bytes).rstrip(b'=')

    def vaild_token_new(self):
        try: 
            print "authenticating"
            return self.authenticate()
        except: 
            # printing stack trace 
            traceback.print_exc() 
        

    def authenticate(self):
        try: 
            owner_access_token = authtoken.main(self.email, self.password)
            self.token = owner_access_token
            self.auth_header = {'Authorization': 'Bearer ' + self.token} 
            return "success"      

        except: 
            # printing stack trace 
            traceback.print_exc()
            return "fail"         

    def productlist(self):
        endpoint = '/api/1/products'
        url = self.base_path + endpoint
        batterySiteId = ''
        productItem = {}
        energySiteAddress = 0
        productListItems = []
        foundEnergySite = False

        try:
            result = requests.get(url, headers=self.auth_header, verify=False, timeout=50)
            result = json.loads(result.text)
            #print("Product List: ", result)
            productListItems = result["response"]
            count = int(result["count"])
            #This assumes the last product is the Powerwall 
            #print()
            for x in range(count):
                productItem = productListItems[x]
                #print ("Checking product item for site address: ", productItem)
                print()
                if("energy_site_id" in productItem):
                    foundEnergySite = True
                    energySiteAddress = x
                    print ("Found energy site @ product: ", energySiteAddress)
                    result = productListItems[energySiteAddress]
                    print("Energy item: ", result)
                    print("Site Id: ", result["energy_site_id"])
                    if(result.has_key("battery_type")):
                        self.energy_site_id.append(result["energy_site_id"])
                
        except requests.exceptions.RequestException:
            print('HTTP Request failed')


    ## Set Powerwall Operation to Charge (Backup) or Discharge (self_consumption)
    #  Pause PERHAPS WITH (self_consumption) w/ Current SoC as backup_reserve_percent
    def operation_set(self, real_mode, backup_reserve_percent):
        # auth_header = {'Authorization': 'Bearer ' + self.token}
        payload = {"backup_reserve_percent": backup_reserve_percent}
        #payload = json.dumps({"real_mode": real_mode, "backup_reserve_percent": backup_reserve_percent})

        
        for energy_site_id in self.energy_site_id:

            print ("Setting mode: " + json.dumps(payload))
            set_endpoint = '/backup'
            get_url = self.energy_base_url + str(energy_site_id) + '/site_info'
            set_url = self.energy_base_url + str(energy_site_id) + set_endpoint
            print ("Setting Operation for Site Id: ", energy_site_id)
            print ("Trying URL: ", set_url)

            print ("Setting mode: " + json.dumps(payload))

            try:
                print ("Trying URL: ", get_url)
                result = requests.get(get_url, json=payload, headers=self.auth_header, timeout=50)
                print("Get result output: ", result.content)
                result = json.loads(result.text)
                get_reserve_percent = result["response"]
                get_reserve_percent = get_reserve_percent["backup_reserve_percent"]
                print("Current reserve percent: ", get_reserve_percent)
                #okay check here, if reserve % not 0, then set it back
                if get_reserve_percent != 0:
                    bodyText = 'Powerwall reserve may not be set, would be good to check, we have sent a retry, current reserve: ' + str(get_reserve_percent) + '%'
                    sendEmail.main(self.email, bodyText)
                    print "Found reserve % to be off setting it"
                    print ("Trying URL: ", set_url)
                    result = requests.post(set_url, json=payload, headers=self.auth_header, timeout=50)
                    print("Set result output: ", result.content)
                    if result.status_code == 201:
                        print("Successfully changed reserve mode")
                else:
                    print("Reserve is set correctly, skipping")


            except HTTPError as err:
                print("Error: {0}".format(err))
            except Timeout as err:
                print("Request timed out: {0}".format(err))

if __name__ == "__main__":
    main()