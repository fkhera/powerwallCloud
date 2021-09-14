#!/usr/bin/env python
# Class to just get tesla tokens


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

import recaptchasolver
import pickledb
from datetime import datetime, timedelta
import dateutil

_LOGGER = logging.getLogger(__name__)
db = pickledb.load('token.db', True)

def getDateTimeFromISO8601String(s):
    d = dateutil.parser.parse(s)
    return d

def main(emailItem, passwordItem):
    #Change these items
    gateway_host = 'owner-api.teslamotors.com'
    email = emailItem
    password = passwordItem
    backup_reserve_percent = float("100.0")
    logging.basicConfig(filename='powerwall_site.log', level=logging.WARNING)

    attempts = 0
    tpw = powerwall_site(gateway_host, password, email)  
    while 'fail' in tpw.token and attempts < 6:
        print ("token auth attempts count: ", attempts)
        try:
            attempts = attempts + 1 
            # Get valid token from OAuth
            tpw.token = tpw.vaild_token_new() 

            # return access token to be used by other systems
            return tpw.token      
       
        except:
            # printing stack trace 
            traceback.print_exc()

    if attempts > 5: 
        print("Attempts exceeded")     


class powerwall_site(object):
    def __init__(self, gateway_host, password, email):

        self.gateway_host = gateway_host
        self.email = email
        self.password = password
        self.token = 'fail'

        self.base_path = 'https://' + self.gateway_host
        self.auth_header = {'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + self.token}
        self.TESLA_CLIENT_ID='81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384'
        self.TESLA_CLIENT_SECRET='c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3'

        self.verifier_bytes = os.urandom(32)
        self.challenge = base64.urlsafe_b64encode(self.verifier_bytes).rstrip(b'=')
        self.challenge_bytes = hashlib.sha256(self.challenge).digest()
        self.challengeSum = base64.urlsafe_b64encode(self.challenge_bytes).rstrip(b'=')

    def rand_str(self, chars=43):
        letters = string.ascii_lowercase + string.ascii_uppercase + string.digits + "-" + "_"
        return "".join(random.choice(letters) for i in range(chars))        
      
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

    def vaild_token_new(self):
        print "authenticating"

        try:      
            token_details = db.get(self.email)

            # Need some try catch here to just authenticate and reset

            if token_details:
                print ("Got token details")
                print (token_details)
                access_token = token_details["access_token"]
                refresh_token = token_details["refresh_token"]
                expiredate = token_details["expiredate"]
                expiredatetime = getDateTimeFromISO8601String(expiredate)

                # check if expired date is greater than today date
                if datetime.now().date() > expiredatetime.date():
                    # Time to go get new refresh token
                    print ("Token expiry date has passed, getting new token")
                    return self.getRefreshedToken(refresh_token)
                else:
                    # Can use existing token
                    return access_token


                # defined token
                # get acesss token, check if its expired
                # get expiry
                # get refresh token
            else:
                # no token in database, we need to get complete details for auth call
                # store auth token details to database
                return self.authenticate()
    
        except:
            traceback.print_exc()
            print("Something went wrong retrieving token so starting auth again")
            return self.authenticate()



    def saveToken(self, accessTokenObj):
        accessTokenObjToSave = accessTokenObj

        #{Sample Token object
        #"access_token": "ee4352c364cd1e78ed0a59734dd029d36910c455c8a0a5c14ef49546b18e99bf",
        #"token_type": "bearer",
        #"expires_in": 3888000,
        #"refresh_token": "c09b05b7b18fe2a90fc8024abf19539aad4e67da0955ec9ab736b138c346855f",
        #"created_at": 1541176299

        deltaExpiry = accessTokenObj["expires_in"]
        expireDate = datetime.now() + timedelta(seconds=deltaExpiry)
        accessTokenObjToSave['user'] = self.email
        accessTokenObjToSave['expiredate'] = expireDate.isoformat()
        print "Saving token data to db"
        print accessTokenObjToSave
        db.set(self.email, accessTokenObjToSave)
        return accessTokenObjToSave["access_token"]

    def getRefreshedToken(self, refresh_token):
        session = requests.Session()
        payload = {
            'grant_type': 'refresh_token',
            'client_id': '81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384',
            'client_secret': 'c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3',
            'refresh_token': refresh_token
            }

        resp = session.post("https://owner-api.teslamotors.com/oauth/token", json=payload)
        print resp
        print resp.json()
        return self.saveToken(resp.json()) 

    def getAccesTokenJwt(self, session, payload):
        headers = {}
        print "payload"
        print payload
        resp = session.post("https://auth.tesla.com/oauth2/v3/token", json=payload)
        print resp
        access_token = resp.json()["access_token"]

        headers["authorization"] = "bearer " + access_token
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": self.TESLA_CLIENT_ID,
        }
        resp = session.post("https://owner-api.teslamotors.com/oauth/token", headers=headers, json=payload)
        return self.saveToken(resp.json()) 

    def authenticate(self):
        try: 
            session = requests.Session()
            print "authenticate method"
            auth_url = self.authUrl();

            headers = {}
            resp = session.get(auth_url, headers=headers)
            #print (resp.text)
            recaptcha_site_key = re.search(r".*sitekey.* : '(.*)'", resp.text).group(1)
            print ('captcha sitekey: ' + recaptcha_site_key)
            print ('auth url: ' + auth_url)

            csrf = re.search(r'name="_csrf".+value="([^"]+)"', resp.text).group(1)
            transaction_id = re.search(r'name="transaction_id".+value="([^"]+)"', resp.text).group(1)
            captchacode = recaptchasolver.main(recaptcha_site_key, auth_url)

            data = {
                "_csrf": csrf,
                "_phase": "authenticate",
                "_process": "1",
                "transaction_id": transaction_id,
                "cancel": "",
                "identity": self.email,
                "credential": self.password,
                "g-recaptcha-response:": captchacode,
                "recaptcha": captchacode
            }

            print "Opening session with login"
            # Important to say redirects false cause this will result in 302 and need to see next data
            resp = session.post(auth_url, headers=headers, data=data, allow_redirects=False)
        
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

            return self.getAccesTokenJwt(session, payload)
     

        except: 
            # printing stack trace 
            traceback.print_exc()
            return "fail" 

if __name__ == "__main__":
    main()

