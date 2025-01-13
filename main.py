from flask import Flask, render_template
import pandas as pd
import gspread
import logging
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

import numpy as np

app = Flask(__name__)


GOOGLE_SHEET_URL='https://docs.google.com/spreadsheets/d/10vXJRdLfP2WQwUidacy6o8NZH2ZFP5CzIZBAly5XvXE/edit?gid=0#gid=0'
GOOGLE_SHEET_JSON_KEYFILE_PATH='/home/manoranjan99/mysite/smooth-aura-427907-f1-ec431d988386.json'

google_sheet_url = GOOGLE_SHEET_URL
json_keyfile_path = GOOGLE_SHEET_JSON_KEYFILE_PATH

def append_in_data_structure(schedule):

    classes_array = []
    temp = schedule.iloc[:, :]
    class_info = temp.applymap(lambda x: x if pd.notna(x) else "")

    for row in class_info.values:
        # Initialize an empty list to hold the formatted room-subject pairs for this row
        row_classes = []
        # Iterate over the columns (rooms) and corresponding subjects in the current row
        for room, subject in zip(class_info.columns, row):
            # Assuming room is a tuple with two values
            if isinstance(room, tuple) and len(room) == 2:
                room_name = f"{room[0]} ({room[1]})"
            else:
                room_name = str(room)

            room_name = room_name.replace('PGP 28 Term-I Class Schedule ', '')
            # Format the room-subject pair and append to the row_classes list
            if subject:
                row_classes.append(f"{subject}")
            else:
                row_classes.append(f"--")

        # Append the row_classes list to the main classes_today_2d list
        classes_array.append(row_classes)
    return classes_array

def get_schedule_from_date(schedule_df, date):
    try:
        schedule = schedule_df[schedule_df['Date'] == date]
    except KeyError as e:
        print(f"KeyError: {e}. Please check the column names in the Excel sheet.")
    return schedule

def get_schedule_from_sheet():

    # Setup the Google Sheets API client
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_file(json_keyfile_path, scopes=scope)

    try:
        credentials = Credentials.from_service_account_file(json_keyfile_path, scopes=scope)
        gc = gspread.authorize(credentials)
        logging.info("Successfully authorized with Google Sheets API")
    except Exception as e:
        logging.error(f"Failed to authorize with Google Sheets API: {e}")
        raise

    try:
        sheet = gc.open_by_url(google_sheet_url).sheet1
    except gspread.exceptions.NoValidUrlKeyFound:
        # Extract the key from the URL
        sheet_key = google_sheet_url.split("/d/")[1].split("/")[0]
        sheet = gc.open_by_key(sheet_key).sheet1

    # Fetch all values from the sheet
    all_values = sheet.get_all_values()
    schedule_df = pd.DataFrame(all_values)

    # Set the new header and drop the row that is now used as header
    schedule_df = schedule_df.iloc[2:].reset_index(drop=True)
    schedule_df.columns = schedule_df.iloc[0]
    schedule_df = schedule_df.drop(0).reset_index(drop=True)

   # Replace blank values with NaN only in merged cells (starting from the third column)
    for row in schedule_df.index:
        for col in range(2, len(schedule_df.columns)):
            if schedule_df.iat[row, col] == '' and schedule_df.iat[row, col-1] != '':
                schedule_df.iat[row, col] = np.nan


    # Replace blank values with NaN starting from the third column
    schedule_df.iloc[:, 2:] = schedule_df.iloc[:, 2:].replace('', np.nan)

    # Forward fill the NaN values starting from the third column
    # schedule_df.iloc[:, 2:] = schedule_df.iloc[:, 2:].ffill(axis=1)

    # Get today's date in the same format as the schedule
    today = (datetime.now()).strftime("%A, %B %d, %Y").replace(',', ', ')

    # Handling Windows systems where %-d might not be supported
    if '%-d' not in datetime.now().strftime("%A, %B %d, %Y"):
        today = datetime.now().strftime("%A, %B %d, %Y").replace(' 0', ' ')

    # Tomorrow date
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%A, %B %d, %Y").replace(',', ', ').replace(' 0', ' ')

    # Handling Windows systems where %-d might not be supported
    if '%-d' not in datetime.now().strftime("%A, %B %d, %Y"):
        tomorrow = (datetime.now()+timedelta(days=1)).strftime("%A, %B %d, %Y").replace(' 0', ' ')

    # Filter the dataframe
    today_schedule = get_schedule_from_date(schedule_df, today)
    next_day_schedule = get_schedule_from_date(schedule_df, tomorrow)

    today_class = append_in_data_structure(today_schedule)
    next_day_class = append_in_data_structure(next_day_schedule)

    return today,tomorrow,today_class,next_day_class


@app.route('/')
def index():
    today, tomorrow, schedule, tomorrow_schedule = get_schedule_from_sheet()
    return render_template('index.html', today=today, tomorrow=tomorrow, schedule=schedule, tomorrow_schedule=tomorrow_schedule)


if __name__ == '__main__':
    app.run(debug=True)
