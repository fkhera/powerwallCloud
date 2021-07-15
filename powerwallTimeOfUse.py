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

import captchasolver




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
        
        self.energy_site_id = ""
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
            session = requests.Session()
            print "authenticate method"
            auth_url = self.authUrl();

            headers = {
                'User-Agent' : 'PowerwallDarwinManager' 
            }
            # headers = {}
            resp = session.get(auth_url, headers=headers)

            csrf = re.search(r'name="_csrf".+value="([^"]+)"', resp.text).group(1)
            transaction_id = re.search(r'name="transaction_id".+value="([^"]+)"', resp.text).group(1)



            captchacode = captchasolver.main(session, headers)
            print("captchacode: ", captchacode)

            data = {
                "_csrf": csrf,
                "_phase": "authenticate",
                "_process": "1",
                "transaction_id": transaction_id,
                "cancel": "",
                "identity": self.email,
                "credential": self.password,
                "captcha" : captchacode
            }
            print "Opening session with login"
            # Important to say redirects false cause this will result in 302 and need to see next data
            resp = session.post(auth_url, headers=headers, data=data, allow_redirects=False)
            # Determine if user has MFA enabled
            # In that case there is no redirect to `https://auth.tesla.com/void/callback` and app shows new form with Passcode / Backup Passcode field
            is_mfa = True if resp.status_code == 200 and "/mfa/verify" in resp.text else False

            print "isMFA: " + str(is_mfa)

            if is_mfa:
                getVars = {'transaction_id': transaction_id }
                url = 'https://auth.tesla.com/oauth2/v3/authorize/mfa/factors'
                mfaUrl = url + "?" + urllib.urlencode(getVars)
                resp = session.get(mfaUrl, headers=headers)
                # {
                #     "data": [
                #         {
                #             "dispatchRequired": false,
                #             "id": "41d6c32c-b14a-4cef-9834-36f819d1fb4b",
                #             "name": "Device #1",
                #             "factorType": "token:software",
                #             "factorProvider": "TESLA",
                #             "securityLevel": 1,
                #             "activatedAt": "2020-12-07T14:07:50.000Z",
                #             "updatedAt": "2020-12-07T06:07:49.000Z",
                #         }
                #     ]
                # }
                print(resp.text)
                factor_id = resp.json()["data"][0]["id"]

                # Can use Passcode
                data = {"transaction_id": transaction_id, "factor_id": factor_id, "passcode": "YOUR_PASSCODE"}
                resp = session.post("https://auth.tesla.com/oauth2/v3/authorize/mfa/verify", headers=headers, json=data)
                # ^^ Content-Type - application/json
                print(resp.text)
                # {
                #     "data": {
                #         "id": "63375dc0-3a11-11eb-8b23-75a3281a8aa8",
                #         "challengeId": "c7febba0-3a10-11eb-a6d9-2179cb5bc651",
                #         "factorId": "41d6c32c-b14a-4cef-9834-36f819d1fb4b",
                #         "passCode": "985203",
                #         "approved": true,
                #         "flagged": false,
                #         "valid": true,
                #         "createdAt": "2020-12-09T03:26:31.000Z",
                #         "updatedAt": "2020-12-09T03:26:31.000Z",
                #     }
                # }
                if "error" in resp.text or not resp.json()["data"]["approved"] or not resp.json()["data"]["valid"]:
                    raise ValueError("Invalid passcode.")

                # Can use Backup Passcode
                data = {"transaction_id": transaction_id, "backup_code": "ONE_OF_BACKUP_CODES"}
                resp = session.post(
                    "https://auth.tesla.com/oauth2/v3/authorize/mfa/backupcodes/attempt", headers=headers, json=data
                )
                # ^^ Content-Type - application/json
                print(resp.text)
                # {
                #     "data": {
                #         "valid": true,
                #         "reason": null,
                #         "message": null,
                #         "enrolled": true,
                #         "generatedAt": "2020-12-09T06:14:23.170Z",
                #         "codesRemaining": 9,
                #         "attemptsRemaining": 10,
                #         "locked": false,
                #     }
                # }
                if "error" in resp.text or not resp.json()["data"]["valid"]:
                    raise ValueError("Invalid backup passcode.")

                data = {"transaction_id": transaction_id}
                resp = session.post(
                    "https://auth.tesla.com/oauth2/v3/authorize",
                    headers=headers,
                    params=params,
                    data=data,
                    allow_redirects=False,
                )


            # If not MFA This code plays instead , which is parising location
            print "Coming to non MFA flow:"
            code_url = resp.headers["location"]
            parsed = urlparse.urlparse(code_url)
            code = urlparse.parse_qs(parsed.query)['code']

            payload = {
                "grant_type": "authorization_code",
                "client_id": "ownerapi",
                "code_verifier": self.rand_str(108),
                "code": code,
                "redirect_uri": "https://auth.tesla.com/void/callback",
            }

            resp = session.post("https://auth.tesla.com/oauth2/v3/token", headers=headers, json=payload)
            access_token = resp.json()["access_token"]

            headers["authorization"] = "bearer " + access_token
            payload = {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "client_id": self.TESLA_CLIENT_ID,
            }
            resp = session.post("https://owner-api.teslamotors.com/oauth/token", headers=headers, json=payload)
            owner_access_token = resp.json()["access_token"]

            self.token = owner_access_token
            self.auth_header = {'Authorization': 'Bearer ' + self.token} 
            return "success"      

        except: 
            # printing stack trace 
            traceback.print_exc()
            return "fail" 

    def rand_str(self, chars=43):
        letters = string.ascii_lowercase + string.ascii_uppercase + string.digits + "-" + "_"
        return "".join(random.choice(letters) for i in range(chars))        

    def listDevices(self, transaction_id):
        print "getting url"
        getVars = {'transaction_id': transaction_id }
        url = 'https://auth.tesla.com/oauth2/v3/authorize/mfa/factors'

        # Python 2:
        result = url + "?" + urllib.urlencode(getVars)
        print(result)
        headers = {
                'User-Agent' : 'PowerwallDarwinManager' 
        }
        resp = self.session.get(result, headers=headers)
        print self.session.cookies
        print resp
        print resp.content
        # Next steps I need the devices

        
    def authUrl(self):
        print "getting url"
        getVars = {'client_id': 'ownerapi', 
                   'code_challenge': self.challengeSum,
                   'code_challenge_method' : "S256",
                   'redirect_uri' : "https://auth.tesla.com/void/callback",
                   'response_type' : "code",
                   'scope' : "openid email offline_access",
                   'state' : "tesla_exporter"
        }
        url = 'https://auth.tesla.com/oauth2/v3/authorize'

        # Python 2:
        result = url + "?" + urllib.urlencode(getVars)
        print(result)
        return result

        # Python 3:
        # print(url + urllib.parse.urlencode(getVars))

    ### Returns current valid token or new valid token
    def valid_token(self):
        endpoint = '/oauth/token'
        url = self.base_path + endpoint 

        status_endpoint = '/api/status'
        status_url = self.base_path + status_endpoint 

        print ("Token expired getting new one")
        headers = {
            'Content-Type': 'application/json',
            'User-Agent' : 'PowerwallDarwinManager' 
       }
        json_data = {
            'grant_type' : 'password',
            'client_id' : self.TESLA_CLIENT_ID,
            'client_secret' : self.TESLA_CLIENT_SECRET,
            'password' : self.password,
            'email' : self.email
        }
        data = json.dumps(json_data)
        #print(data)
        #print(json_data)
        print("Asking for token: ", url)

        result = requests.post(url, headers=headers, data=data)
        #print ("Got response")
        #print(result.content)
        result = json.loads(result.text)
        #print(result)
        #print(result["access_token"])
        #Store new token
        self.token = result["access_token"]
        self.auth_header = {'Authorization': 'Bearer ' + self.token}
        
            ## Returns Sitemaster status
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


    ## Returns Sitemaster status
    def sitemaster(self):
        endpoint = '/api/sitemaster'
        url = self.base_path + endpoint 

        try:
            result = requests.get(url, headers=self.auth_header, verify=False, timeout=50)
            print("Site Master result, ", result)
            return json.loads(result.text)

        except requests.exceptions.RequestException:
            print('HTTP Request failed')




    ## Start the Powerwall(s) & Gateway (usually after getting an authentication token)
    def sitemaster_run(self):
        endpoint = '/api/sitemaster/run'
        url = self.base_path + endpoint 

        try:
            result = requests.get(url, headers=self.auth_header, verify=False, timeout=50)

            print("## Debug sitemaster_run()")
            print("## result.status_code:" + str(result.status_code))
            
            if result.status_code == 202:
                self.running = True

        except requests.exceptions.RequestException:
            print('HTTP Request failed')



    ## Reads aggregate meter information.
    def meters_aggregates(self):
        endpoint = '/api/meters/aggregates'
        url = self.base_path + endpoint 
        result = requests.get(url, headers=self.auth_header, verify=False, timeout=50)

        return result.json()




    ## Read State of Charge (in percent)
    def stateofenergy(self):

        # When Sitemaster is not running, caught:
        # Error: 502 Server Error: Bad Gateway for url: https://powerwall.local/api/system_status/soe
        endpoint = '/api/system_status/soe'
        url = self.base_path + endpoint 

        try:
            result = requests.get(url, headers=self.auth_header, verify=False, timeout=50)

            # raise_for_status will throw an exception if an HTTP error
            # code was returned as part of the response
            result.raise_for_status()

            return result.json()

        except HTTPError as err:
            print("Error: {0}".format(err))
        except Timeout as err:
            print("Request timed out: {0}".format(err))

    ## Read Powerwall Operation Mode (real_mode)
    def operation(self):
        #endpoint = '/api/operation'
        endpoint = self.energy_base_url + self.energy_site_id + '/operation'
        url = self.base_path + endpoint

        try:
            result = requests.get(url, headers=self.auth_header, timeout=50)

            if result.status_code == 200:
                self.real_mode = result.json()['real_mode']
                print("## Debug valid_token()")
                print("self.real_mode: " + self.real_mode)

            return result.json()

        except HTTPError as err:
            print("Error: {0}".format(err))
        except Timeout as err:
            print("Request timed out: {0}".format(err))#




    ## Pause Powerwall Operation
    #   Discharge (self_consumption) w/ Current SoC as backup_reserve_percent
    def operation_pause(self):

        _set_endpoint = '/api/operation'
        _set_url = self.base_path + _set_endpoint
        _enable_endpoint = '/api/config/completed'
        _enable_url = self.base_path + _enable_endpoint 

        try:
            print ('Committing change to server')
            result = requests.get(_enable_url, headers=self.auth_header, timeout=50)
            
            print('Response HTTP Status Code: {status_code}'.format(status_code=result.status_code))
            print('Response HTTP Response Body: {content}'.format(content=result.content))
            print ("Setting old token again")
            self.token = 'nWc26nWM7T6ZLH6MQQUYzyabeSn56IBWfj_i0JtFUQS1A1wEZ1ZaPBkFHYFf8LxDJqrU6fgesY2TOFLKm99xnw=='
            self.auth_header = {'Authorization': 'Bearer ' + self.token}
                

        except HTTPError as err:
            print("Error: {0}".format(err))
        except Timeout as err:
                print("Request timed out: {0}".format(err))#


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


## Meter class to store meter_aggregates JSON
class meters(object):
    def __init__(self, d):
        if type(d) is str:
            d = json.loads(d)
        self.convert_json(d)

    def convert_json(self, d):
        self.__dict__ = {}
        for key, value in d.items():
            if type(value) is dict:
                value = meters(value)
            self.__dict__[key] = value

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getitem__(self, key):
        return self.__dict__[key]

if __name__ == "__main__":
    main()