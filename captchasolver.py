import requests
from time import sleep
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import base64

# You will need pip install svglib

# It goes to say this work takes effort so please use my referral to support my work
# https://2captcha.com?from=11874928 
# The link above allows you to create a acount with 2captcha which is what we use
# If you know me we can share API key, just reach out to me  thanks
# Appreciate donations to keep 2captcha going, anything helps
API_KEY = ''  # Your 2captcha API KEY
CAPTCHA_ENABLE = True

def main(session, headers):

    if(CAPTCHA_ENABLE): 
        # Captcha is session based so use the same headers
        print 'Getting captcha'
        catpcha = session.get('https://auth.tesla.com/captcha', headers=headers)

        # Save captch as .png image to send 2Captcha service locally
        file = open("captcha.svg", "wb")
        file.write(catpcha.content)
        file.close()

        drawing = svg2rlg("captcha.svg")
        renderPM.drawToFile(drawing, "captcha.png", fmt="PNG")

        # Encode image base 64
        with open('captcha.png', 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read())

        # Now use the image file saved locally to post to captcha service and wait for response
        # here we post site key to 2captcha to get captcha ID (and we parse it here too)
        current_url = "http://2captcha.com/in.php"

        data = {
            "key": API_KEY,
            "method": "base64",
            "body": encoded_string,
            "regsense": 1,
            "textinstructions": "text",        
        }
           
        files = open('captcha.png', 'rb')
        resp = requests.post(current_url,
                    data=data)

        captcha_id = resp.text.split('|')[1]

        # Change data to be getting the answer from 2captcha
        data = {
            "key": API_KEY,
            "action": "get",
            "id": captcha_id
        }
        answer_url = "http://2captcha.com/res.php"
        resp = requests.get(answer_url,
                    params=data)

        captcha_answer = resp.text
        while 'CAPCHA_NOT_READY' in captcha_answer:
            sleep(5)
            captcha_answer = requests.get(answer_url,
                    params=data)
            print captcha_answer.text

        captcha_answer = captcha_answer.text.split('|')[1]
        print captcha_answer
        return captcha_answer
    # if captcha not enabled just return empty string
    else:
        print "Skipping captcha"
        return ""


if __name__ == "__main__":
    main()