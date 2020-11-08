Welcome to powerwall cloud!

# Introduction

# Instructions
* Install PIP and Pandas since it uses holidays, and possibly requests
* Run python powerwallDriver.py backup or python powerwallDriver.py tou
* Create a cron schedule to track your work



# Setting up PI
* Find the IP Address of your Rasberry PI by checking router or run `ifconfig` on PI itself
* Enable PI on Raspberry SSH , username: pi, password: raspberry
* ssh pi@192.168.1.197
* scp powerwall/* pi@192.168.1.197:
* Install Pandas by running command below
    * sudo apt-get install python-pandas


# Cron Schedule
* Here are some sample crons we used for the SRP Utility, but you can use whatever suits you::
* Important to only set this up as crontab and eventually have a process to rotate log files

crontab -e

```
#Summer

40 13 * 5-10 1-5 python /home/pi/powerwallDriver.py tou > logTou.txt
1 20 * 5-10 1-5 python /home/pi/powerwallDriver.py backup > logBackup.txt

#Winter
40 4 * 1-4,11-12 1-5  python /home/pi/powerwallDriver.py tou > logTou.txt
1 09 * 1-4,11-12 1-5 python /home/pi/powerwallDriver.py backup > logBackup.txt
40 16 * 1-4,11-12 1-5  python /home/pi/powerwallDriver.py tou > logTou.txt
1 21 * 1-4,11-12 1-5 python /home/pi/powerwallDriver.py backup > logBackup.txt
```

# About code
* powerwallDriver.py - main driver file
* powerwallBackup.py  - runs back up for given account (set reserve to 100%) forces charge
* powerwallTimeOfUser.py - runs time of use given account (set reserve to 0%) forces discharge