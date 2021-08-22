import smtplib
import traceback

# You may neeed to enable non secure, disable 2FA on gmail
gmail_user = 'gmailemail'
gmail_password = 'gmailpass'



def main(emailItem, bodyText):
    try:
        # configure email
        sent_from = 'Powerwall Reminder Service'
        to = [emailItem]
        recipients = ",".join(to)
        subject = 'Powerwall reserve not set'
        email_text = 'From:{}\nTo:{}\nSubject:{}\n\n{}'.format(sent_from, recipients, subject, bodyText)
        

        # send email out
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.sendmail(sent_from, to, email_text)
        server.close()

        print 'Email sent!'
    except:
        traceback.print_exc()
        print 'Something went wrong...'