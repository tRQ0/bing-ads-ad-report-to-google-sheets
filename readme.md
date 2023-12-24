# Dependencies for the script:
## Bing Ads
- Change the client ID or client token if you ever choose to change the associated Bing Ads account
- Follow the guide:
    - to setup a client [guide](https://learn.microsoft.com/en-us/advertising/guides/authentication-oauth-register?view=bingads-13) 
    - to get a developer token [guide](https://learn.microsoft.com/en-us/advertising/guides/get-started?view=bingads-13) 
- These fields are located in main.py having the names `CLIENT_ID` and `DEVELOPER_TOKEN` respectively
```
# Required
CLIENT_ID = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
DEVELOPER_TOKEN='xxxxxxxxxx'
```
## Google Sheets
- Use this [guide](https://developers.google.com/sheets/api/quickstart/python) to create a Google Cloud project if not already and get the credentials for authentication
- Copy the credentials json file to the credentials folder (create the folder if not already) and rename the credentials file **'credentials/service-account-credentials-live.json'** in 
```
credentials_path = os.path.join(script_dir, "credentials/service-account-credentials-live.json")
``` 
located in `gs_interface.py` 
- After making a service account and generating a service account email make sure to give the email neccessary permissions for the spreadsheet by clicking on **Share** in the google sheet and sharing it to the service account email
- In the script `gs_interface.py`, change the fields `SPREADSHEET_ID` and `RANGE` if need be. 
- The `SPREADSHEET_ID` is found in the spreadshield url. For example in the spreadsheet `https://docs.google.com/spreadsheets/d/1234567890-rc12345vjtWAaQ`the part after `/d/` is the spreadsheet ID which in this case is `1234567890-rc12345vjtWAaQ`
- The `RANGE` variable contains the sheet name withing the spreadsheet and the cell ranges from where to where the data needs to change. For example here we have `RANGE = 'Sheet!A2:N'`, here **Sheet** is the name of the sheet `!` is the separator and **A2:N** is the cell range withing the excel sheet

# Setting up environment for executing the script
- Use the command `pip install -r requirements.txt` to install all the required dependencis
- On first execution of the script you need to authenticate the application with microsoft. This can be done by copying the authentication link that will be printed in the console upon first authentication and then following the instructions presented in the console
- If for any reason you cannot access the link in the console then the authentication link is logged inside **log/app.log**
- After authentication you need to copy the **code** query parameter from the link that is presented after successful authentication, the link may look like this `https://login.microsoftonline.com/common/oauth2/nativeclient?code=xxxxxxxx`
- The token is then to be copied into the **refresh.txt** file (make if not exists) inside **credentials** folder (make if not exists), after then the script should run correctly 

# Running the script
- Execute the `main.py` script by using the command `python3 main.py`

# ~~Default behaviour~~
- ~~This script was made with the purpose of updating the bing ads data for the past 7 days to a sheet named **tech** within a google [spreadsheet](https://docs.google.com/spreadsheets/)~~

# Logging
- The log for every execution can be found inside **log/app.log** file
- The log contains all necessary info, warning and error messages