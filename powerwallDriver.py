import powerwallBackup
import powerwallTimeOfUse

import sys
import time
import datetime
from pandas.tseries.holiday import *

FILE_TO_READ = "accounts.txt"

class SRPCalendar(AbstractHolidayCalendar):
   rules = [
     Holiday('New Year', month=1, day=1, observance=sunday_to_monday),
     Holiday('Memorial Day' , month=5 , day=25, offset=DateOffset(weekday=MO(1))),
     Holiday('Labor Day', month=9, day=1, offset=DateOffset(weekday=MO(1))),
     Holiday('July 4th', month=7, day=4, observance=nearest_workday),
     #Holiday('All Saints Day', month=11, day=1), Test Holiday
     Holiday('Thanksgiving Day' , month=11 , day=1, offset=DateOffset(weekday=TH(4))),
     Holiday('Christmas', month=12, day=25, observance=nearest_workday)
   ]


def main(mode):
    #Change these items

    with open(FILE_TO_READ) as f:
        lines = f.readlines()
        lines = [x.strip() for x in lines] 
        for line in lines:
            try:
                accountComponents = line.split(':')
                email = accountComponents[0]
                password = accountComponents[1]
                #print "Processing: ", email, password
                print "Invoking mode: ", mode

                #TO DO IF IT IS HOLIDAY JUST INVOKE ACTION
                cal = SRPCalendar()
                holidays = cal.holidays(start='2020-01-01', end='2050-12-31').to_pydatetime()
                TODAY = datetime.today()
                TODAY = datetime(TODAY.year,TODAY.month,TODAY.day)

                if TODAY in holidays:
                    print "Today is a holiday keep invoking back up"
                    powerwallBackup.main(email, password)
                else:
                    #TODAY IS NOT A HOLIDAY foward on to action
                    if(mode == "backup"):
                        powerwallBackup.main(email, password)

                    if(mode == "tou"):
                        powerwallTimeOfUse.main(email, password)

                #Delay between accounts to not flag warning signs
                time.sleep(1)
            except:
                print("Unexpected error:", sys.exc_info()[0])

if __name__ == "__main__":
    main(sys.argv[1])