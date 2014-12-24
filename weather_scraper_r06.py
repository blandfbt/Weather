from urllib2 import urlopen
import re
import datetime
import itertools as IT
import tempfile
import os
from WBT_Enthalpy_r04 import WBT_and_Enthalpy
from sys import stdout
import pandas as pd
import numpy as np
import webbrowser

def daterange(start_date, end_date):
    '''
    This is a simple generator function for iterating over all the individual days in the 
    date range specified by the user.
    Right now, it leaves out the final date entered by the user, but I could change that setting.
    '''
    for n in range(int ((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)

def uniquify(path, sep = ''):
    '''
    This is a handy function that determines if there is already a file with the wanted name
    in the directory.  If there is, it called the name_sequence generator to build another 
    sequential number into the file name.  
    '''
    def name_sequence():
        count = IT.count()
        yield ''
        while True:
            yield '_r{s}{n:d}'.format(s = sep, n = next(count))
    orig = tempfile._name_sequence 
    with tempfile._once_lock:
        tempfile._name_sequence = name_sequence()
        path = os.path.normpath(path)
        dirname, basename = os.path.split(path)
        filename, ext = os.path.splitext(basename)
        fd, filename = tempfile.mkstemp(dir = dirname, prefix = filename, suffix = ext)
        tempfile._name_sequence = orig
    return filename

def get_weather_data(start_date, end_date, weather_station, target_file):
    '''
    This function is the main scraper function.  It opens the target file, writes a header line
    to it.  The headers are different based on which type of weather station is used. 
    Then is loops through each day from a generator function 'daterange'.  This builds the daily
    query for the URL.
    It stores the data in the local variable 'response' and makes sure that works.  Then for 
    each line in the response, it filters out the header and </br >, writing the line to the 
    target file. 
    It prints the date value after each loop, replacing the last screen printout.
    '''
    line_check = False
    with open(target_file, 'a') as f:
        if len(weather_station) == 4:
            header_line = "Time,DBT_F,DewpointF,Hum,Press,Visibility," \
               + "Wind_Dir,Wind_Speed,Gust_Speed,Precipitation,Events,Conditions," \
               + "WindDirDegrees,DateUTC" + '\r'
        else:
            header_line = 'Time,DBT_F,DewpointF,Press,Wind_Dir,' + \
                        'WindDirectionDegrees,Wind_Speed,Gust_Speed,Hum,' + \
                        'Precipitation_hourly,Conditions,Clouds,Precipitation_daily,SoftwareType,DateUTC' + '\r'

        f.write(header_line)
        for single_date in daterange(start_date, end_date):
            if len(str(single_date.day)) == 1:
                day_value = "0" + str(single_date.day)
            else:
                day_value = str(single_date.day)

            if len(weather_station) == 4:
                Query = weather_station + "/" + str(single_date.year) + "/"+ str(single_date.month) \
                        + "/" + day_value
                BASE_URL = "http://english.wunderground.com/history/airport/" + Query + \
                "/DailyHistory.html?req_city=NA&req_state=NA&req_statename=NA&format=1"
            else:
                BASE_URL = "http://www.wunderground.com/weatherstation/WXDailyHistory.asp?ID=" + \
                weather_station + "&day=" + str(single_date.day) + "&month=" + str(single_date.month) +\
                "&year="+ str(single_date.year) + "&graphspan=day&format=1"

            try:
                response = urlopen(BASE_URL)
            except:
                print "\n\nThe URL: \n" + BASE_URL
                print "\ndoesn't seem to be working.  If you are on a Siemens network,"
                print "it doesn't allow the program to access outside URLs.\n\n"
                os.system('pause')

            for line in response:
                if (not (re.search('Time', line))) and ((re.search(',', line))) and (not (re.search('-9999', line))):
                    if (len(line.strip()) > 0):
                        line_check = True
                    line = line.replace("<br />", "")
                    f.write(line)

            stdout.write('\r' + str(single_date.year) + "/"+ str(single_date.month) + "/" + day_value)
            stdout.flush()
    return line_check

def clean_up_pandas(filename, TimeDiff, accuracy):
    '''
    This function takes in the weather data file, calculates the time in the
    timezone given by TimeDiff, removes the UTC and TimeEST columns, and
    calculates the time differential.
    It also calculates the WBT and enthalpy, using a different function.
    Then it makes a new file, with the appended name _pandas to it. 
    '''
    output_filename = filename
    #output_filename = filename[:len(filename)-4] + '_pandas.csv'
    df = pd.read_csv(filename, index_col = False)
    df['DateEST'] = pd.to_datetime(df['DateUTC']) - datetime.timedelta(hours=TimeDiff)
    df = df.drop('Time', axis=1)
    df = df.drop('DateUTC', axis=1)
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]
    df['Hours'] = (df['DateEST']-df['DateEST'].shift()).fillna(0) / np.timedelta64(1, 'h')
    #call the WBT function to build two new arrays
    df['WBT_F'], df['Enthalpy'] = WBT_and_Enthalpy(df['DBT_F'].astype(float), 
                                                df['Hum'].astype(float), 
                                                df['Press'].astype(float), 
                                                accuracy)
    df.to_csv(output_filename, sep=',')
    return df

def BIN_Prompt(df, csv_filename):
    print '\nYou can now run a BIN on any of these parameters: \n'
    #selection = BIN_Selection_Prompt(df)
    keep_going = True
    while keep_going:
        selection = BIN_Selection_Prompt(df)
        if selection != 'q':
            BIN_df = BIN_pandas(df, selection)
            BIN_filename_temp = csv_filename[:-4] + '_' + selection + '_BIN.csv'
            BIN_filename = uniquify(BIN_filename_temp)
            BIN_df.to_csv(BIN_filename, sep=',')
        else:
            keep_going = False

def BIN_Selection_Prompt(df):
    #print '\nYou can now run a BIN on any of these parameters: \n'
    mydict = {}
    for index, item in enumerate(df):
        print index, ': ' , item
        mydict[index] = item
    #print '\n\n'
    isValid = False
    while not isValid:
        userIn = raw_input('\nPlease type the number of the parameter you would like to BIN' +
            ' or enter "q" to quit: ')
        if userIn.isdigit():
            try:
                selection = mydict[int(userIn)]
                isValid = True
            except:
                print '\nThat is not a correct number from the list.\n'
        elif userIn.upper() == 'Q':
            selection = 'q'
            isValid = True
        else:
            print "\nThat is not a number.\n"

    return selection

def BIN_pandas(df, bin_type):
    '''
    This function takes in the dataframe and the type of desired BIN, and it outputs another dataframe
    that is an array of the unique values and the hours spent at each.
    '''
    #BIN = pd.DataFrame(df.groupby(bin_type)['Hours'].sum())
    #BIN.columns = [bin_type, 'hours']
    #BIN_df = pd.DataFrame(BIN)
    return pd.DataFrame(df.groupby(bin_type)['Hours'].sum())

def Obtain_date(beg_end):
    '''
    This function obtains the user input for the date, and determines if it is a valid date entry.
    It also checks to see if the date listed is in the future, which won't work.
    '''
    isValid = False
    while not isValid:
        userIn = raw_input("Type " + beg_end + " mm/dd/yy: ")
        try:
            d = datetime.datetime.strptime(userIn, '%m/%d/%y')
            if d < datetime.datetime.now():
                isValid = True
            else:
                print '\nThat date is in the future.'
        except:
            print "\nThat date format is not correct, try again."
    return d

def Obtain_WeatherStation():  
    '''
    This function prompts the user for the desired weather station.  First, it prompts to see if
    the user would like to be directed to the Wundermap to see a list of all the possible weather
    stations. 
    Next it checks to see if the user input is valid (alphanumerics only)
    ''' 
    seeWunderground = raw_input('\nWould you like to see a list of all the' + 
        ' possible weather stations? (y/n): ')
    if seeWunderground.upper() =='Y':
        webbrowser.open_new('http://www.wunderground.com/wundermap/')

    isValid = False
    while not isValid:
        userIn = raw_input("\nType the weather station: ")
        try:
            if userIn.isalnum() and userIn > 4:
                isValid = True
            elif userIn.isalpha() and userIn == 4:
                userIn = userIn.upper()
                isValid = True
            else:
                print "\nThat isn't a valid weather station.  Try again."
        except:
            print "\nThat isn't a valid weather station.  Try again."
    return userIn

def main():
    beginning_date = Obtain_date('beginning')
    ending_date = Obtain_date('Ending')

    beginning_string = (str(beginning_date.year)+ str(beginning_date.month) + 
                       str(beginning_date.day) )
    ending_string = (str(ending_date.year) + str(ending_date.month) +
                   str(ending_date.day))

    weather_station = Obtain_WeatherStation()
    #this gets the current working directory
    storage_location = os.getcwd()
    #check for 'Data' folder
    if not os.path.exists(storage_location  + "\\" + '\Data\\'):
        os.makedirs(storage_location  + "\\" + '\Data\\')

    new_folder_name = storage_location + '\Data\\' + weather_station + '_' + \
                beginning_string + '_to_' + ending_string + '\\'

    if not os.path.exists(new_folder_name):
        os.makedirs(new_folder_name)

    CSV_name = weather_station + '_' + beginning_string + '_to_' + ending_string + '.csv'

    target_file = new_folder_name  + "\\" + CSV_name
    actual_filename = uniquify(target_file)
    
    line_check = get_weather_data(beginning_date, ending_date, weather_station, actual_filename)

    if line_check:
        accuracy_answer = raw_input("\nDo you want the run low accuracy? Type YES if so:  ").upper()
        if accuracy_answer == 'YES':
            accuracy = .1
        else:
            accuracy = .001

        TimeDiff = 5
        df = clean_up_pandas(actual_filename, TimeDiff, accuracy)
    else:
        print '\n\nNothing was downloaded.  Please verify your connection.'
        print 'Also please verify there is data for your weather station '
        print 'for the dates you selected.'
    
    BIN_Prompt(df, actual_filename)
    print '\nYou can find your files at: ', new_folder_name, '\n'
    os.system('pause')     

if __name__ == '__main__': 
    main()