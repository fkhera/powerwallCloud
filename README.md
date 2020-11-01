Welcome to powerwall cloud!

# Introduction

# Instructions
* Install PIP and Pandas since it uses holidays, and possibly requests
* Run python powerwallDriver.py backup or python powerwallDriver.py tou
* Create a cron schedule to track your work

# Cron Schedule
Here are some sample crons we used for the SRP Utility, but you can use whatever suits you::

# Setting up PI

Enable PI on Raspberry SSH , username: pi, password: raspberryssh pi@192.168.1.197sudo ap-get install python-pandaas
farooq@Farooqs-MBP Downloads % scp powerwall/* pi@192.168.1.197:

crontab -e

#Summer

45 4 * 5-10 1-5  python /home/pi/powerwallDriver.py backup
45 13 * 5-10 1-5 python /home/pi/powerwallDriver.py tou 
1 20 * 5-10 5 python /home/pi/powerwallDriver.py backup

#Winter

45 4 * 1,2,3,4,11,12 1-5  python /home/pi/powerwallDriver.py tou
1 09 * 1,2,3,4,11,12 1-5 /home/pi/powerwallDriver.py backup
45 16 * 1,2,3,4,11,12 1-5  python /home/pi/powerwallDriver.py tou
1 21 * 1,2,3,4,11,12 5 python /home/pi/powerwallDriver.py backup