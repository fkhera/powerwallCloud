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


def main(emailItem, passwordItem, reserve_percent):
    #Change these items
    gateway_host = 'owner-api.teslamotors.com'
    email = emailItem
    password = passwordItem
    backup_reserve_percent = float(reserve_percent)

    logging.basicConfig(filename='powerwall_site.log', level=logging.WARNING)

    attempts = 0
    tpw = powerwall_site(gateway_host, password, email)  
    while 'fail' in tpw.token and attempts < 5:
        print ("back up attempts count: ", attempts)
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



class powerwall_site(object):
    def __init__(self, gateway_host, password, email):
        self.email = email
        self.token = 'fail'
        self.gateway_host = gateway_host
        self.password = password
        self.battery_soc = 0
        self.backup_reserve_percent = 13.14159265358979
        self.real_mode = ''

        self.base_path = 'https://' + self.gateway_host
        self.auth_header = {'Content-Type': 'application/json','Authorization': 'Bearer ' + self.token}
        self.haveCar = True
        
        self.energy_site_id = ""
        self.energy_base_url = self.base_path + '/api/1/energy_sites/'

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
                    
            if(foundEnergySite):
                result = productListItems[energySiteAddress]
                print("Energy item: ", result)
                print("Site Id: ", result["energy_site_id"])
                self.energy_site_id = result["energy_site_id"]
                
        except requests.exceptions.RequestException:
            print('HTTP Request failed')


    ## Set Powerwall Operation to Charge (Backup) or Discharge (self_consumption)
    #  Pause PERHAPS WITH (self_consumption) w/ Current SoC as backup_reserve_percent
    def operation_set(self, real_mode, backup_reserve_percent):
        # auth_header = {'Authorization': 'Bearer ' + self.token}
        payload = {"backup_reserve_percent": backup_reserve_percent}
        #payload = json.dumps({"real_mode": real_mode, "backup_reserve_percent": backup_reserve_percent})

        set_endpoint = '/backup'
        set_url = self.energy_base_url + str(self.energy_site_id) + set_endpoint
        print ("Setting Operation for Site Id: ", self.energy_site_id)
        print ("Trying URL: ", set_url)

        print ("Setting mode: " + json.dumps(payload))

        try:
            result = requests.post(set_url, json=payload, headers=self.auth_header, timeout=50)
            print("Set result output: ", result.content)
            if result.status_code == 201:
                print("Successfully changed reserve mode")
        except HTTPError as err:
            print("Error: {0}".format(err))
        except Timeout as err:
            print("Request timed out: {0}".format(err))#

if __name__ == "__main__":
    main()