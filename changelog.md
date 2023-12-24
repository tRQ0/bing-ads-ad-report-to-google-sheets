# Changelog for Bing Ads script

## v1

- For authentication now the application does not redirects directly to the web browser, instead authenticaion link is printed in the console
- Cleanup is now a part of the main script and does not require a separate cron
- Implement logger
- Add next script execution time to spreadsheet
- fix static paths in the main script
- fix unable to create data folder and log/app.log file if not exist
- Sort data in descending order of data
- Remove script related outputs
- Data should not inlude todays date data

### v1.1
- Installed new dependency package i.e **CurrencyConverter**
- Change sorting order for data, now data is sorted date wise i.e. all account data is shown for a single date
- Add new column (**Cost (converted)**) that contains converted **SPEND** value 
- Add new column (**Avg. CPC (converted)**) that contains converted **AverageCpc** value 
- Add new column (**Total conv. value**) that contains converted **Spend** value 
- Create pivot table for previous day data in **Sheet 6**

## ToDo

- Add environment file
- fix error flow
- add accurate script execution status
- implement logging to external script or word file 