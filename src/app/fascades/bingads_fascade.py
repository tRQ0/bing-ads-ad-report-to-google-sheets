import src.bingads_implementation as bingads_implementation
import sys
import pandas as pd

import src.app.utils.utils as utils
import src.app.factories.AdsReportFactory as AdsReportFactory

from datetime import datetime, timedelta
from bingads.v13.reporting import *
from bingads.authorization import AuthorizationData, OAuthDesktopMobileAuthCodeGrant 
from bingads.service_client import ServiceClient

class BingadsFascade():

    def __init__(self, app_env, logger = None):
        self.logger = logger or None
        self.__set_app_env(app_env)
        self.__set_authorization_data(self.__authorization_data_factory())       
        self.__set_customer_service(self.__customer_service_factory())       

    """
    FACTORIES
    """
    def __authorization_data_factory(self):
        authorization_data=AuthorizationData(
            account_id=None,
            customer_id=None,
            developer_token=self.__get_developer_token(),
            authentication=None,
        )
        return authorization_data

    def __customer_service_factory(self):
        customer_service = ServiceClient(
            service='CustomerManagementService', 
            version=13,
            authorization_data=self.__get_authorization_data(), 
            environment=self.__get_environment(),
        )
        return customer_service

    """
    Setters definition start
    """

    def __set_app_env(self, app_env):
        self.app_env = app_env

    def __set_authorization_data(self, authorization_data):
        self.authorization_data = authorization_data

    def __set_customer_service(self, customer_service):
        self.customer_service = customer_service

    
    """
    Getters definition start
    """

    def __get_client_id(self):
        return self.app_env["CLIENT_ID"]

    def __get_developer_token(self):
        return self.app_env["DEVELOPER_TOKEN"]

    def __get_environment(self):
        return self.app_env["ENVIRONMENT"]

    def __get_refresh_token_path(self):
        return self.app_env["REFRESH_TOKEN"]

    def __get_client_state(self):
        return self.app_env["CLIENT_STATE"]

    def __get_authorization_data(self):
        return self.authorization_data
    
    def __get_customer_service(self):
        return self.customer_service
    
    """
    Business logic
    """

    def authenticate(self, authorization_data, customer_service):
        # You should authenticate for Bing Ads API service operations with a Microsoft Account.
        self.__authenticate_with_oauth(authorization_data)

        # Set to an empty user identifier to get the current authenticated Microsoft Advertising user,
        # and then search for all accounts the user can access.
        user = customer_service.GetUser(
            UserId=None
        ).User
        accounts=self.__search_accounts_by_user_id(customer_service, user.Id)

        # Collect all associated accounts with name and id
        authorization_data.accounts = [{"Id": account["Id"], "Name": account["Name"]} for account in accounts["AdvertiserAccount"]]
        authorization_data.customer_id=accounts['AdvertiserAccount'][0].ParentCustomerId
        account_ids = [account_data["Id"] for account_data in authorization_data.accounts]

        # Print the list of IDs
        print(account_ids)
        return authorization_data

    def __authenticate_with_oauth(self, authorization_data):
        authentication=OAuthDesktopMobileAuthCodeGrant(
            client_id=self.__get_client_id(),
            env=self.__get_environment()
        )

        # It is recommended that you specify a non guessable 'state' request parameter to help prevent
        # cross site request forgery (CSRF). 
        authentication.state=self.__get_client_state

        # Assign this authentication instance to the authorization_data. 
        authorization_data.authentication=authentication   

        # Register the callback function to automatically save the refresh token anytime it is refreshed.
        # Uncomment this line if you want to store your refresh token. Be sure to save your refresh token securely.
        authorization_data.authentication.token_refreshed_callback = self.__save_refresh_token_to_file

        refresh_token = self.__get_refresh_token_from_file(self.__get_refresh_token_path())

        try:
            # If we have a refresh token let's refresh it
            if refresh_token is not None:
                authorization_data.authentication.request_oauth_tokens_by_refresh_token(refresh_token)
                self.__set_authorization_data(authorization_data)
            else:
                self.__request_user_consent(authorization_data)
        except OAuthTokenRequestException:
            # The user could not be authenticated or the grant is expired. 
            # The user must first sign in and if needed grant the client application access to the requested scope.
           self.__request_user_consent(authorization_data)

    def __request_user_consent(self, authorization_data):
        self.logger.log_message("user authentication required", level=logging.WARNING)

        auth_link = authorization_data.authentication.get_authorization_endpoint()
        print("\n")
        print("You need to provide consent for the application to access your Microsoft Advertising accounts by visiting the following link: ")
        print(auth_link)
        print("\n")
        self.logger.log_message(f"authentication link: {auth_link}", level=logging.WARNING)

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

        if authorization_data.authentication.state != self.__get_client_state():
            # self.logger.log_message("The OAuth response state does not match the client request state.", level=logging.ERROR)
            raise Exception("The OAuth response state does not match the client request state.")

        # Request access and refresh tokens using the URI that you provided manually during program execution.
        authorization_data.authentication.request_oauth_tokens_by_response_uri(response_uri=response_uri) 

    def __get_refresh_token_from_file(self, file_name):
        ''' 
        Returns a refresh token if found.
        '''
        file=None
        try:
            file=open(file_name)
            line=file.readline()
            file.close()
            return line if line else None
        except IOError:
            if file:
                file.close()
            return "Error while reading refresh token"

    def __save_refresh_token_to_file(self, oauth_tokens):
        ''' 
        Stores a refresh token locally. Be sure to save your refresh token securely.
        '''
        with open(self.__get_refresh_token_path(),"w+") as file:
            file.write(oauth_tokens.refresh_token)
            file.close()
        return None
    
    def __search_accounts_by_user_id(self, customer_service, user_id):
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
            paging=self._set_elements_to_none(customer_service.factory.create('ns5:Paging'))
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
    
    def _set_elements_to_none(self, suds_object):
        for (element) in suds_object:
            suds_object.__setitem__(element[0], None)
        return suds_object

    # def get_ads_report(
    #         self,
    #         authorization_data,
    #         start_date,
    #         end_date,
    #         qry_type,
    #         request_report_columns = [
    #             # 'AccountId',
    #             'AccountName',
    #             'TimePeriod',
    #             'CurrencyCode', 
    #             'CampaignType', 
    #             'Network', 
    #             'DeviceType', 
    #             'Clicks',
    #             'Impressions',
    #             'Ctr', 
    #             'AverageCpc', 
    #             'Spend', 
    #             'Conversions',
    #             'Revenue',
    #             ],
            
    #         ):
    #     try:
    #         startDate = self.date_validation(start_date)
    #         dt = startDate+timedelta(1)
    #         week_number = dt.isocalendar()[1]
    #         endDate = self.date_validation(end_date)

    #         reporting_service = self.__get_customer_service()

    #         if qry_type in ["day","daily"]:
    #             aggregation = 'Daily'
    #         elif qry_type in ["week","weekly"]:
    #             aggregation = 'Weekly'
    #         exclude_column_headers=False
    #         exclude_report_footer=True
    #         exclude_report_header=False
    #         time=reporting_service.factory.create('ReportTime')
    #         start_date=reporting_service.factory.create('Date')
    #         start_date.Day=startDate.day
    #         start_date.Month=startDate.month
    #         start_date.Year=startDate.year
    #         time.CustomDateRangeStart=start_date

    #         end_date=reporting_service.factory.create('Date')
    #         end_date.Day=endDate.day
    #         end_date.Month=endDate.month
    #         end_date.Year=endDate.year
    #         time.CustomDateRangeEnd=end_date
    #         time.ReportTimeZone='PacificTimeUSCanadaTijuana'
    #         return_only_complete_data=False
            
    #         report_request=reporting_service.factory.create('AdPerformanceReportRequest')
    #         report_request.Aggregation=aggregation
    #         report_request.ExcludeColumnHeaders=exclude_column_headers
    #         report_request.ExcludeReportFooter=exclude_report_footer
    #         report_request.ExcludeReportHeader=exclude_report_header
    #         report_request.Format='Csv'
    #         report_request.ReturnOnlyCompleteData=return_only_complete_data
    #         report_request.Time=time    
    #         report_request.ReportName="Ads Performance Report"
    #         scope=reporting_service.factory.create('AccountThroughAdGroupReportScope')
    #         scope.AccountIds={'long': [account["Id"] for account in authorization_data.accounts] }
    #         scope.Campaigns=None
    #         report_request.Scope=scope     

    #         # Primary columns required in the API
    #         report_columns=reporting_service.factory.create('ArrayOfAdPerformanceReportColumn')
    #         report_columns.AdPerformanceReportColumn.append(request_report_columns)
    #         report_request.Columns=report_columns

    #         #return campaign_performance_report_request
    #         return report_request
    #     except:
    #         self.logger.log_message(f"MS_ADS_REPORT : report processing Failed : {sys.exc_info()}", level=logging.ERROR)
    #         print("\nMS_ADS_REPORT : report processing Failed : ", sys.exc_info())

    def date_validation(self, date_text):
        try:
            while date_text != datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d'):
                date_text = input('Please Enter the date in YYYY-MM-DD format\t')
            else:
                return datetime.strptime(date_text,'%Y-%m-%d').date()
        except:
            self.logger.log_message("linkedin_campaign_processing : year does not match format yyyy-mm-dd", level=logging.ERROR)
            raise Exception('linkedin_campaign_processing : year does not match format yyyy-mm-dd')

    def download_ads_report(self, report_request,authorization_data,start_date,end_date,qry_type):
        try:
            save_path = utils.resolve_sys_path("data")
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            startDate = self.date_validation(start_date)
            dt = startDate+timedelta(1)
            week_number = dt.isocalendar()[1]
            endDate = self.date_validation(end_date)

            reporting_download_parameters = ReportingDownloadParameters(
                    report_request=report_request,
                    result_file_directory = save_path, 
                    result_file_name = "ads_report_" + start_date + "_" + end_date + ".csv", 
                    overwrite_result_file = True, # Set this value true if you want to overwrite the same file.
                    timeout_in_milliseconds=3600000, # You may optionally cancel the download after a specified time interval.
                )
            
            #global reporting_service_manager
            reporting_service_manager = ReportingServiceManager(
                authorization_data=authorization_data, 
                poll_interval_in_milliseconds=5000, 
                environment=self.__get_environment(),
            )
            report_container = reporting_service_manager.download_report(reporting_download_parameters)
            columns = report_request.Columns.AdPerformanceReportColumn[0]

            report_record_iterable = report_container.report_records
# CUT HERE
            ads_analytics_data = []
            data_list = []

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
            self.logger.log_message(f"DOWNLOAD_ADS_REPORT : processing Failed : {sys.exc_info()}", level=logging.ERROR)
            print("\nDOWNLOAD_ADS_REPORT : processing Failed : ", sys.exc_info())


    def bootstrap(self):
        ads_report_factory = AdsReportFactory()

        authorization_data = self.authenticate(self.__get_authorization_data(), self.__get_customer_service())
        self.__set_authorization_data(authorization_data)
        # Get todays date
        current_date = datetime.now()

        current_date = current_date - timedelta(days=1)
        formatted_date_today = current_date.strftime('%Y-%m-%d')

        # Calculate the date and time 7 days ago
        seven_days_ago = current_date - timedelta(days=6)
        seven_days_ago = seven_days_ago.strftime('%Y-%m-%d')

        # logger.log_message(f"fetching data for date range: {formatted_date_today} to {seven_days_ago}")

        # Generate reprot_request object
        request_report_columns = [
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
                ],
        
        report_request = ads_report_factory.get_ads_report(
            authorization_data,
            seven_days_ago,
            formatted_date_today,
            'daily',
            request_report_columns,
            )
        print(report_request)
    