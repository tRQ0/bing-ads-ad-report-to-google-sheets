'''Google Sheets Interface

This module is used to interface with the google sheets and 
update the specified google sheets
'''
from __future__ import print_function

import os.path
import logging
import logger

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def update_g_sheet(
    data, 
    meta, 
    spreadsheet_id,
    range,
    append_mode = False,
    log_to_sheet = False,
    ):

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    # credentials = service_account.Credentials.from_service_account_file('credentials/service-account-credentials.json', scopes=SCOPES)

    # Get script path
    script_dir = os.path.dirname(os.path.abspath(__file__))

    credentials_path = os.path.join(script_dir, "credentials/service-account-credentials-live.json")
    '''LIVE CREDENTIALS'''
    credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)

    try:
        service = build('sheets', 'v4', credentials=credentials)

        # Call the Sheets API
        sheet = service.spreadsheets()

        if not append_mode:
            # Clear the sheet
            print("Clearing old values...")
            sheet.values().clear(
                spreadsheetId=spreadsheet_id,
                range=range
                ).execute()

        values = data
        body = {"values": values}

        if not values:
            if log_to_sheet:
                body = {'values': [
                    ['Status: FAIL'],
                    ['Reason: no data to upload']
                ]}
                result = (
                    sheet
                    .values()
                    .append(
                        spreadsheetId=spreadsheet_id,
                        range=range,
                        valueInputOption='USER_ENTERED',
                        body=body,
                    )
                    .execute()
                )

            print('No data to upload.')
            logger.log_message('No data to upload.', level=logging.WARNING)
            return
        
        # Call the Sheets API
        result = (
            sheet
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range,
                valueInputOption='USER_ENTERED',
                body=body,
            )
            .execute()
        )
        # time.sleep(2)
        if(result):
            update_range = result["updatedRange"].split('!', 2)[1]
            update_row_count = result["updatedRows"]
            logger.log_message(f"google spreadsheet updated")
            logger.log_message(f"range: {update_range}, rows updated: {update_row_count}")

            print("Updating new values...")
            # time.sleep(2)
            print("\nUpdate Done!")
            print("\tUpdated Range: %s" % (update_range))
            print("\tUpdated Rows: %s" % update_row_count)
            body = {'values': [
                # [f'Rows Range: {update_range}'],
                # [f'Rows Updated: {update_row_count}'],
                ['Status: SUCCESS'],
                [f"Script Execution began at: {meta['script_start_time']} {meta['timezone']}"],
            ]}
            if log_to_sheet:
                result = (
                    sheet
                    .values()
                    .append(
                        spreadsheetId=spreadsheet_id,
                        range=range,
                        valueInputOption='USER_ENTERED',
                        body=body,
                    )
                    .execute()
                )
        elif log_to_sheet:
            body = {'values': [
                ['Status: FAIL'],
                ['Reason: unable to upload data']
            ]}
            result = (
                sheet
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range,
                    valueInputOption='USER_ENTERED',
                    body=body,
                )
                .execute()
            )
    except HttpError as err:
        logger.log_message(err, level=logging.ERROR)
        print(err)
