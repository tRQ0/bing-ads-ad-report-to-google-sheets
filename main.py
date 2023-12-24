import sys
import pandas as pd
import logging
import logger
import json
import os

from bingads.service_client import ServiceClient
from bingads.authorization import AuthorizationData, OAuthDesktopMobileAuthCodeGrant
from currency_converter import CurrencyConverter
from time import gmtime, strftime
from suds import WebFault
from urllib import parse
from datetime import datetime, timedelta, timezone
from bingads.v13 import *
from bingads.v13.reporting import *
from suds import WebFault
from suds.client import Client
from gs_interface import update_g_sheet 
from cleanup import clear_folder 

script_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# Get script path
script_dir = os.path.dirname(os.path.abspath(__file__))

logger.setup_logger(os.path.join(script_dir, "log/app.log"))

# Required
with open(os.path.join(script_dir, "credentials/env.json"), 'r') as file:
    ENVIRONMENT_INFO = json.load(file)
CLIENT_ID = ENVIRONMENT_INFO["CLIENT_ID"]
DEVELOPER_TOKEN = ENVIRONMENT_INFO["DEVELOPER_TOKEN"]
ENVIRONMENT = ENVIRONMENT_INFO["ENVIRONMENT"]
REFRESH_TOKEN = os.path.join(script_dir, "credentials/refresh.txt")

# Optional
CLIENT_STATE=None

# Optionally you can include logging to output traffic, for example the SOAP request and response.
# import logging
# logging.basicConfig(level=logging.INFO)
# logging.getLogger('suds.client').setLevel(logging.DEBUG)
# logging.getLogger('suds.transport.http').setLevel(logging.DEBUG)

def authenticate(authorization_data):

    customer_service=ServiceClient(
        service='CustomerManagementService', 
        version=13,
        authorization_data=authorization_data, 
        environment=ENVIRONMENT,
    )

    # You should authenticate for Bing Ads API service operations with a Microsoft Account.
    authenticate_with_oauth(authorization_data)

    # Set to an empty user identifier to get the current authenticated Microsoft Advertising user,
    # and then search for all accounts the user can access.
    user=get_user_response=customer_service.GetUser(
        UserId=None
    ).User
    accounts=search_accounts_by_user_id(customer_service, user.Id)

    # For this example we'll use the first account.
    authorization_data.account_id=accounts['AdvertiserAccount'][0].Id
    authorization_data.customer_id=accounts['AdvertiserAccount'][0].ParentCustomerId

def authenticate_with_oauth(authorization_data):

    authentication=OAuthDesktopMobileAuthCodeGrant(
        client_id=CLIENT_ID,
        env=ENVIRONMENT
    )

    # It is recommended that you specify a non guessable 'state' request parameter to help prevent
    # cross site request forgery (CSRF). 
    authentication.state=CLIENT_STATE

    # Assign this authentication instance to the authorization_data. 
    authorization_data.authentication=authentication   

    # Register the callback function to automatically save the refresh token anytime it is refreshed.
    # Uncomment this line if you want to store your refresh token. Be sure to save your refresh token securely.
    authorization_data.authentication.token_refreshed_callback=save_refresh_token

    refresh_token=get_refresh_token()

    try:
        # If we have a refresh token let's refresh it
        if refresh_token is not None:
            authorization_data.authentication.request_oauth_tokens_by_refresh_token(refresh_token)
        else:
            request_user_consent(authorization_data)
    except OAuthTokenRequestException:
        # The user could not be authenticated or the grant is expired. 
        # The user must first sign in and if needed grant the client application access to the requested scope.
        request_user_consent(authorization_data)

def request_user_consent(authorization_data):
    
    logger.log_message("user authentication required", level=logging.WARNING)

    auth_link = authorization_data.authentication.get_authorization_endpoint()
    print("\n")
    print("You need to provide consent for the application to access your Microsoft Advertising accounts by visiting the following link: ")
    print(auth_link)
    print("\n")
    logger.log_message(f"authentication link: {auth_link}", level=logging.WARNING)

    # Below code redirects to the browser window which is not ideal in a production environment
    # webbrowser.open(authorization_data.authentication.get_authorization_endpoint(), new=1)

    # For Python 3.x use 'input' instead of 'raw_input'
    if(sys.version_info.major >= 3):
        response_uri=input(
            "After you have granted consent in the web browser for the application to access your Microsoft Advertising accounts, " \
            "please enter the response URI that includes the authorization 'code' parameter: \n"
        )
    else:
        response_uri=raw_input(
            "You need to provide consent for the application to access your Microsoft Advertising accounts. " \
            "After you have granted consent in the web browser for the application to access your Microsoft Advertising accounts, " \
            "please enter the response URI that includes the authorization 'code' parameter: \n"
        )

    if authorization_data.authentication.state != CLIENT_STATE:
        logger.log_message("The OAuth response state does not match the client request state.", level=logging.ERROR)
        raise Exception("The OAuth response state does not match the client request state.")

    # Request access and refresh tokens using the URI that you provided manually during program execution.
    authorization_data.authentication.request_oauth_tokens_by_response_uri(response_uri=response_uri) 

def get_refresh_token():
    ''' 
    Returns a refresh token if found.
    '''
    file=None
    try:
        file=open(REFRESH_TOKEN)
        line=file.readline()
        file.close()
        return line if line else None
    except IOError:
        if file:
            file.close()
        return None

def save_refresh_token(oauth_tokens):
    ''' 
    Stores a refresh token locally. Be sure to save your refresh token securely.
    '''
    with open(REFRESH_TOKEN,"w+") as file:
        file.write(oauth_tokens.refresh_token)
        file.close()
    return None

def search_accounts_by_user_id(customer_service, user_id):
    predicates={
        'Predicate': [
            {
                'Field': 'UserId',
                'Operator': 'Equals',
                'Value': user_id,
            },
        ]
    }

    accounts=[]

    page_index = 0
    PAGE_SIZE=100
    found_last_page = False

    while (not found_last_page):
        paging=set_elements_to_none(customer_service.factory.create('ns5:Paging'))
        paging.Index=page_index
        paging.Size=PAGE_SIZE
        search_accounts_response = customer_service.SearchAccounts(
            PageInfo=paging,
            Predicates=predicates
        )

        if search_accounts_response is not None and hasattr(search_accounts_response, 'AdvertiserAccount'):
            accounts.extend(search_accounts_response['AdvertiserAccount'])
            found_last_page = PAGE_SIZE > len(search_accounts_response['AdvertiserAccount'])
            page_index += 1
        else:
            found_last_page=True

    return {
        'AdvertiserAccount': accounts
    }

def set_elements_to_none(suds_object):
    for (element) in suds_object:
        suds_object.__setitem__(element[0], None)
    return suds_object

def output_status_message(message):
    print(message)

def output_bing_ads_webfault_error(error):
    if hasattr(error, 'ErrorCode'):
        output_status_message("ErrorCode: {0}".format(error.ErrorCode))
    if hasattr(error, 'Code'):
        output_status_message("Code: {0}".format(error.Code))
    if hasattr(error, 'Details'):
        output_status_message("Details: {0}".format(error.Details))
    if hasattr(error, 'FieldPath'):
        output_status_message("FieldPath: {0}".format(error.FieldPath))
    if hasattr(error, 'Message'):
        output_status_message("Message: {0}".format(error.Message))
    output_status_message('')

def output_webfault_errors(ex):
    if not hasattr(ex.fault, "detail"):
        logger.log_message("Unknown WebFault", level=logging.ERROR)
        raise Exception("Unknown WebFault")

    error_attribute_sets = (
        ["ApiFault", "OperationErrors", "OperationError"],
        ["AdApiFaultDetail", "Errors", "AdApiError"],
        ["ApiFaultDetail", "BatchErrors", "BatchError"],
        ["ApiFaultDetail", "OperationErrors", "OperationError"],
        ["EditorialApiFaultDetail", "BatchErrors", "BatchError"],
        ["EditorialApiFaultDetail", "EditorialErrors", "EditorialError"],
        ["EditorialApiFaultDetail", "OperationErrors", "OperationError"],
    )

    for error_attribute_set in error_attribute_sets:
        if output_error_detail(ex.fault.detail, error_attribute_set):
            return

    # Handle serialization errors, for example: The formatter threw an exception while trying to deserialize the message, etc.
    if hasattr(ex.fault, 'detail') \
        and hasattr(ex.fault.detail, 'ExceptionDetail'):
        api_errors=ex.fault.detail.ExceptionDetail
        logger.log_message("--------------- BEGIN ads API errors ---------------", level=logging.ERROR)
        if isinstance(api_errors, list):
            for api_error in api_errors:
                logger.log_message(api_error.Message, level=logging.ERROR)
                output_status_message(api_error.Message)
        else:
            logger.log_message(api_error.Message, level=logging.ERROR)
            output_status_message(api_errors.Message)
        logger.log_message("--------------- END Bing ads API errors ---------------", level=logging.ERROR)
        return

    raise Exception("Unknown WebFault")

def output_error_detail(error_detail, error_attribute_set):
    api_errors = error_detail
    for field in error_attribute_set:
        api_errors = getattr(api_errors, field, None)
    if api_errors is None:
        return False
    logger.log_message("--------------- BEGIN ads API errors ---------------", level=logging.ERROR)
    if isinstance(api_errors, list):
        for api_error in api_errors:
            logger.log_message(api_error.Message, level=logging.ERROR)
            output_bing_ads_webfault_error(api_error)
    else:
        logger.log_message(api_error.Message, level=logging.ERROR)
        output_bing_ads_webfault_error(api_errors)
    logger.log_message("--------------- END Bing ads API errors ---------------", level=logging.ERROR)
    return True

def output_array_of_long(items):
    if items is None or items['long'] is None:
        return
    output_status_message("Array Of long:")
    for item in items['long']:
        output_status_message("{0}".format(item))

def output_customerrole(data_object):
    if data_object is None:
        return
    output_status_message("* * * Begin output_customerrole * * *")
    output_status_message("RoleId: {0}".format(data_object.RoleId))
    output_status_message("CustomerId: {0}".format(data_object.CustomerId))
    # output_status_message("AccountIds:")
    # output_array_of_long(data_object.AccountIds)
    # output_status_message("LinkedAccountIds:")
    # output_array_of_long(data_object.LinkedAccountIds)
    output_status_message("* * * End output_customerrole * * *")

def output_array_of_customerrole(data_objects):
    if data_objects is None or len(data_objects) == 0:
        return
    for data_object in data_objects['CustomerRole']:
        output_customerrole(data_object)

def output_keyvaluepairofstringstring(data_object):
    if data_object is None:
        return
    output_status_message("* * * Begin output_keyvaluepairofstringstring * * *")
    output_status_message("key: {0}".format(data_object.key))
    output_status_message("value: {0}".format(data_object.value))
    output_status_message("* * * End output_keyvaluepairofstringstring * * *")

def output_array_of_keyvaluepairofstringstring(data_objects):
    if data_objects is None or len(data_objects) == 0:
        return
    for data_object in data_objects['KeyValuePairOfstringstring']:
        output_keyvaluepairofstringstring(data_object)

def output_personname(data_object):
    if data_object is None:
        return
    output_status_message("* * * Begin output_personname * * *")
    output_status_message("FirstName: {0}".format(data_object.FirstName))
    output_status_message("LastName: {0}".format(data_object.LastName))
    output_status_message("MiddleInitial: {0}".format(data_object.MiddleInitial))
    output_status_message("* * * End output_personname * * *")

def output_address(data_object):
    if data_object is None:
        return
    output_status_message("* * * Begin output_address * * *")
    output_status_message("City: {0}".format(data_object.City))
    output_status_message("CountryCode: {0}".format(data_object.CountryCode))
    output_status_message("Id: {0}".format(data_object.Id))
    output_status_message("Line1: {0}".format(data_object.Line1))
    output_status_message("Line2: {0}".format(data_object.Line2))
    output_status_message("Line3: {0}".format(data_object.Line3))
    output_status_message("Line4: {0}".format(data_object.Line4))
    output_status_message("PostalCode: {0}".format(data_object.PostalCode))
    output_status_message("StateOrProvince: {0}".format(data_object.StateOrProvince))
    output_status_message("TimeStamp: {0}".format(data_object.TimeStamp))
    output_status_message("BusinessName: {0}".format(data_object.BusinessName))
    output_status_message("* * * End output_address * * *")

def output_contactinfo(data_object):
    if data_object is None:
        return
    output_status_message("* * * Begin output_contactinfo * * *")
    output_status_message("Address:")
    output_address(data_object.Address)
    output_status_message("ContactByPhone: {0}".format(data_object.ContactByPhone))
    output_status_message("ContactByPostalMail: {0}".format(data_object.ContactByPostalMail))
    output_status_message("Email: {0}".format(data_object.Email))
    output_status_message("EmailFormat: {0}".format(data_object.EmailFormat))
    output_status_message("Fax: {0}".format(data_object.Fax))
    output_status_message("HomePhone: {0}".format(data_object.HomePhone))
    output_status_message("Id: {0}".format(data_object.Id))
    output_status_message("Mobile: {0}".format(data_object.Mobile))
    output_status_message("Phone1: {0}".format(data_object.Phone1))
    output_status_message("Phone2: {0}".format(data_object.Phone2))
    output_status_message("* * * End output_contactinfo * * *")

def output_user(data_object):
    if data_object is None:
        return
    output_status_message("* * * Begin output_user * * *")
    output_status_message("ContactInfo:")
    output_contactinfo(data_object.ContactInfo)
    output_status_message("CustomerId: {0}".format(data_object.CustomerId))
    output_status_message("Id: {0}".format(data_object.Id))
    output_status_message("JobTitle: {0}".format(data_object.JobTitle))
    output_status_message("LastModifiedByUserId: {0}".format(data_object.LastModifiedByUserId))
    output_status_message("LastModifiedTime: {0}".format(data_object.LastModifiedTime))
    output_status_message("Lcid: {0}".format(data_object.Lcid))
    output_status_message("Name:")
    output_personname(data_object.Name)
    output_status_message("Password: {0}".format(data_object.Password))
    output_status_message("SecretAnswer: {0}".format(data_object.SecretAnswer))
    output_status_message("SecretQuestion: {0}".format(data_object.SecretQuestion))
    output_status_message("UserLifeCycleStatus: {0}".format(data_object.UserLifeCycleStatus))
    output_status_message("TimeStamp: {0}".format(data_object.TimeStamp))
    output_status_message("UserName: {0}".format(data_object.UserName))
    output_status_message("ForwardCompatibilityMap:")
    output_array_of_keyvaluepairofstringstring(data_object.ForwardCompatibilityMap)
    output_status_message("* * * End output_user * * *")

def get_ads_report(authorization_data,account_id,start_date,end_date,qry_type):
    try:
        startDate = date_validation(start_date)
        dt = startDate+timedelta(1)
        week_number = dt.isocalendar()[1]
        endDate = date_validation(end_date)

        reporting_service = ServiceClient(
            service='ReportingService', 
            version=13,
            authorization_data=authorization_data, 
            environment='production',
            )

        if qry_type in ["day","daily"]:
            aggregation = 'Daily'
        elif qry_type in ["week","weekly"]:
            aggregation = 'Weekly'
        exclude_column_headers=False
        exclude_report_footer=True
        exclude_report_header=False
        time=reporting_service.factory.create('ReportTime')
        start_date=reporting_service.factory.create('Date')
        start_date.Day=startDate.day
        start_date.Month=startDate.month
        start_date.Year=startDate.year
        time.CustomDateRangeStart=start_date

        end_date=reporting_service.factory.create('Date')
        end_date.Day=endDate.day
        end_date.Month=endDate.month
        end_date.Year=endDate.year
        time.CustomDateRangeEnd=end_date
        time.ReportTimeZone='PacificTimeUSCanadaTijuana'
        return_only_complete_data=False
        
        report_request=reporting_service.factory.create('AdPerformanceReportRequest')
        report_request.Aggregation=aggregation
        report_request.ExcludeColumnHeaders=exclude_column_headers
        report_request.ExcludeReportFooter=exclude_report_footer
        report_request.ExcludeReportHeader=exclude_report_header
        report_request.Format='Csv'
        report_request.ReturnOnlyCompleteData=return_only_complete_data
        report_request.Time=time    
        report_request.ReportName="Ads Performance Report"
        scope=reporting_service.factory.create('AccountThroughAdGroupReportScope')
        scope.AccountIds={'long': account_id }
        scope.Campaigns=None
        report_request.Scope=scope     

        # Primary columns required in the API
        report_columns=reporting_service.factory.create('ArrayOfAdPerformanceReportColumn')
        report_columns.AdPerformanceReportColumn.append([
            # 'AccountId',
            'AccountName',
            'TimePeriod',
            'CurrencyCode', 
            'CampaignType', 
            'Network', 
            'DeviceType', 
            'Clicks',
            'Impressions',
            'Ctr', 
            'AverageCpc', 
            'Spend', 
            'Conversions',
            'Revenue',
            ])
        report_request.Columns=report_columns

        #return campaign_performance_report_request
        return report_request
    except:
        logger.log_message(f"MS_ADS_REPORT : report processing Failed : {sys.exc_info()}", level=logging.ERROR)
        print("\nMS_ADS_REPORT : report processing Failed : ", sys.exc_info())

def date_validation(date_text):
    try:
        while date_text != datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d'):
            date_text = input('Please Enter the date in YYYY-MM-DD format\t')
        else:
            return datetime.strptime(date_text,'%Y-%m-%d').date()
    except:
        logger.log_message("linkedin_campaign_processing : year does not match format yyyy-mm-dd", level=logging.ERROR)
        raise Exception('linkedin_campaign_processing : year does not match format yyyy-mm-dd')

def download_ads_report(report_request,authorization_data,start_date,end_date,qry_type):
    try:
        if not os.path.exists(os.path.join(script_dir, "data")):
            os.makedirs(os.path.join(script_dir, "data"))
        startDate = date_validation(start_date)
        dt = startDate+timedelta(1)
        week_number = dt.isocalendar()[1]
        endDate = date_validation(end_date)
        reporting_download_parameters = ReportingDownloadParameters(
                report_request=report_request,
                result_file_directory = os.path.join(script_dir, "data"), 
                result_file_name = "ads_report_" + start_date + "_" + end_date + ".csv", 
                overwrite_result_file = True, # Set this value true if you want to overwrite the same file.
                timeout_in_milliseconds=3600000, # You may optionally cancel the download after a specified time interval.
            )
        
        #global reporting_service_manager
        reporting_service_manager = ReportingServiceManager(
            authorization_data=authorization_data, 
            poll_interval_in_milliseconds=5000, 
            environment=ENVIRONMENT,
        )
        ads_analytics_data = []
        report_container = reporting_service_manager.download_report(reporting_download_parameters)
        columns = report_request.Columns.AdPerformanceReportColumn[0]

        data_list = []
        report_record_iterable = report_container.report_records

        curr_converter = CurrencyConverter()

        for record in report_record_iterable:
            converted_spend_cost = record.value("Spend")
            converted_avg_cpc = record.value("AverageCpc")
            converted_conversions = record.value("Conversions")
            if record.value("CurrencyCode") != "GBP":
                converted_spend_cost = curr_converter.convert(converted_spend_cost, record.value("CurrencyCode"), "GBP")
                converted_avg_cpc = curr_converter.convert(converted_avg_cpc, record.value("CurrencyCode"), "GBP")
                converted_conversions = curr_converter.convert(converted_conversions, record.value("CurrencyCode"), "GBP")

            tmp_dict = {
                # "AccountId": record.value("AccountId"),
                "AccountName": record.value("AccountName"),
                "TimePeriod": record.value("TimePeriod"),
                "CurrencyCode": record.value("CurrencyCode"),
                "CampaignType": record.value("CampaignType"),
                "Network": record.value("Network"),
                "DeviceType": record.value("DeviceType"),
                "Clicks": int(record.value("Clicks")),
                "Impressions": int(record.value("Impressions")),
                "Ctr": record.value("Ctr"),
                "AverageCpc": float(record.value("AverageCpc")),
                "Spend": float(record.value("Spend")),
                "Conversions": float(record.value("Conversions")),
                "Revenue": float(record.value("Revenue")),
                "AverageCpc (converted)": float(converted_avg_cpc),  
                "Cost (converted)": float(converted_spend_cost),  
                "Total conv. value": float(converted_conversions),  
            }
            data_list.append(tmp_dict)
           
        ads_analytics_data = pd.DataFrame(data_list, columns=columns.append([
            "AverageCpc (converted)", 
            "Cost (converted)", 
            "Total conv. value",
        ]))
        ads_analytics_data = ads_analytics_data.fillna('')
        ads_analytics_data['Ctr'] = ads_analytics_data['Ctr'].str.rstrip('%').astype('float') / 100.0

        # Sort data in descending order of date
        ads_analytics_data = ads_analytics_data.sort_values(by=['AccountName'], ascending=[True])
        #list comprehenser
        groups = [group for name, group in ads_analytics_data.groupby("TimePeriod")]
        # Concatenate the groups into a single DataFrame
        ads_analytics_data = pd.concat(reversed(groups), ignore_index=True)

        # Duplicate the dataframe and extact data for last day
        ads_analytics_data_aggregated = ads_analytics_data[ads_analytics_data['TimePeriod'] == end_date]
        ads_analytics_data_aggregated = ads_analytics_data_aggregated.groupby(['AccountName', 'CampaignType']).agg({
            'TimePeriod': lambda x: x.iloc[0],
            'Clicks': 'sum',
            'Impressions': 'sum',
            'Ctr': 'sum',
            'AverageCpc': 'sum',
            'Spend': 'sum',
            'Conversions': 'sum',
            'Revenue': 'sum',
            'AverageCpc (converted)': 'sum',
            'Cost (converted)': 'sum',
            'Total conv. value': 'sum',
        }).reset_index()

        # Calculate totals of aggregated values
        total_row = pd.DataFrame(ads_analytics_data_aggregated.sum(numeric_only=False)).transpose()
        total_row.loc[0, "AccountName"] = "Grand Total"
        total_row.loc[0, "CampaignType"] = " "
        total_row.loc[0, "TimePeriod"] = " "
        total_row.loc[0, "Ctr"] = (total_row.loc[0, "Clicks"]/total_row.loc[0, "Impressions"])
        # total_row.loc[0, "Ctr"] = np.nan_to_num(ads_analytics_data_aggregated['CTR'], nan=0.0, posinf=0.0, neginf=0.0)
        total_row.loc[0, "AverageCpc"] = (total_row.loc[0, "Spend"]/total_row.loc[0, "Clicks"])
        # total_row.loc[0, "AverageCpc"] = np.nan_to_num(ads_analytics_data_aggregated['AverageCpc'], nan=0.0, posinf=0.0, neginf=0.0)
        total_row.loc[0, "AverageCpc (converted)"] = (total_row.loc[0, "Cost (converted)"]/total_row.loc[0, "Clicks"])
        # total_row.loc[0, "AverageCpc (converted)"] = np.nan_to_num(ads_analytics_data_aggregated['AverageCpc (converted)'], nan=0.0, posinf=0.0, neginf=0.0)

        # Combine aggregated data and totals
        ads_analytics_data_aggregated = pd.concat([ads_analytics_data_aggregated, total_row], ignore_index=True)

        # Type cast to string to prevent auto-formatting 
        columns_to_convert = [
            'Impressions', 'Clicks', 'Ctr', 'AverageCpc', 'Spend',
            'Conversions', 'Revenue', 'AverageCpc (converted)',
            'Cost (converted)', 'Total conv. value'
        ]

        ads_analytics_data_aggregated[columns_to_convert] = ads_analytics_data_aggregated[columns_to_convert].astype(str)



        return ads_analytics_data, ads_analytics_data_aggregated
    except:
        logger.log_message(f"DOWNLOAD_ADS_REPORT : processing Failed : {sys.exc_info()}", level=logging.ERROR)
        print("\nDOWNLOAD_ADS_REPORT : processing Failed : ", sys.exc_info())


def main(authorization_data):

    try:
        # output_status_message("-----\nGetUser:")
        get_user_response=customer_service.GetUser(
            UserId=None
        )
        user = get_user_response.User
        customer_roles=get_user_response.CustomerRoles
        # output_status_message("User:")
        # output_user(user)
        output_status_message("CustomerRoles:")
        output_array_of_customerrole(customer_roles)

        # Search for the accounts that the user can access.
        # To retrieve more than 100 accounts, increase the page size up to 1,000.
        # To retrieve more than 1,000 accounts you'll need to add paging.

        accounts=search_accounts_by_user_id(customer_service, user.Id)

        customer_ids=[]
        customer_name=[]
        for account in accounts['AdvertiserAccount']:
            customer_ids.append(account.Id)
            customer_name.append(account.Name)

    except WebFault as ex:
        logger.log_message(ex, level=logging.ERROR)
        output_webfault_errors(ex)
    except Exception as ex:
        logger.log_message(ex, level=logging.ERROR)
        output_status_message(ex)

    current_date = datetime.now()

    # Get todays date
    current_date = current_date - timedelta(days=1)
    formatted_date_today = current_date.strftime('%Y-%m-%d')

    # Calculate the date and time 7 days ago
    seven_days_ago = current_date - timedelta(days=6)
    seven_days_ago = seven_days_ago.strftime('%Y-%m-%d')

    logger.log_message(f"fetching data for date range: {formatted_date_today} to {seven_days_ago}")

    # Generate reprot_request object
    report_request = get_ads_report(authorization_data, customer_ids, seven_days_ago, formatted_date_today, 'daily')

    # Download report
    ads_analytics_data, ads_analytics_data_aggregated = download_ads_report(report_request, authorization_data,seven_days_ago, formatted_date_today, 'daily')

    try:
        if not ads_analytics_data.empty:
            logger.log_message("data pulled from bing ads api")
    # print("\nads_analytics_data :\n", ads_analytics_data)
    except:
        pass    

    try:
        update_g_sheet(
            ads_analytics_data.values.tolist(),
            {'script_start_time': script_start_time, 'timezone': timezone},
            spreadsheet_id = ENVIRONMENT_INFO["DEFAULT_SPREADSHEET_ID"],
            range = ENVIRONMENT_INFO["DEFAULT_SPREADSHEET_RANGE"],
            )
    except Exception as ex:
        logger.log_message("Error occured while updating 'tech' sheet", level=logging.ERROR)
        logger.log_message(ex, level=logging.ERROR)
        output_status_message(ex)

    try:
        update_g_sheet(
            data = [ads_analytics_data_aggregated.columns.values.tolist()] + ads_analytics_data_aggregated.values.tolist(), 
            meta = {'script_start_time': script_start_time, 'timezone': timezone},
            spreadsheet_id = ENVIRONMENT_INFO["DEFAULT_SPREADSHEET_ID"],
            range = 'Sheet6!A1:O',
            )
    except Exception as ex:
        logger.log_message("Error occured while updating sheet 'Sheet6'", level=logging.ERROR)
        logger.log_message(ex, level=logging.ERROR)
        output_status_message(ex)    

# Main execution
if __name__ == '__main__':

    print("Loading the web service client proxies...")

    authorization_data=AuthorizationData(
        account_id=None,
        customer_id=None,
        developer_token=DEVELOPER_TOKEN,
        authentication=None,
    )

    customer_service=ServiceClient(
        service='CustomerManagementService', 
        version=13,
        authorization_data=authorization_data, 
        environment=ENVIRONMENT,
    )


    if datetime.now().day == 1:
        folder_to_clear = 'data'
        folder_path = os.path.join(script_dir, "data")
        # Call the function to clear the folder
        logger.log_message(clear_folder(folder_path))

    date_time_formatted = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timezone = datetime.now(timezone.utc).tzinfo
    logger.log_message(f"-+-+-+-BEGIN for {date_time_formatted} {timezone}")

    authenticate(authorization_data)

    main(authorization_data)

    logger.log_message("-+-+-+-END")
