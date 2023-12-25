import app.src.bingads_implementation as bingads_implementation
import sys

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

        customer_service=customer_service

        # You should authenticate for Bing Ads API service operations with a Microsoft Account.
        self.__authenticate_with_oauth(authorization_data)

        # Set to an empty user identifier to get the current authenticated Microsoft Advertising user,
        # and then search for all accounts the user can access.
        user=get_user_response=customer_service.GetUser(
            UserId=None
        ).User
        accounts=self.__search_accounts_by_user_id(customer_service, user.Id)

        print(accounts)
        # For this example we'll use the first account.
        authorization_data.account_id=accounts['AdvertiserAccount'][0].Id
        authorization_data.customer_id=accounts['AdvertiserAccount'][0].ParentCustomerId

        self.__set_authorization_data(authorization_data)

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
        log_message("user authentication required", level=logging.WARNING)

        auth_link = authorization_data.authentication.get_authorization_endpoint()
        print("\n")
        print("You need to provide consent for the application to access your Microsoft Advertising accounts by visiting the following link: ")
        print(auth_link)
        print("\n")
        # logger.log_message(f"authentication link: {auth_link}", level=logging.WARNING)

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
            # logger.log_message("The OAuth response state does not match the client request state.", level=logging.ERROR)
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

    
    def bootstrap(self):
        self.authenticate(self.__get_authorization_data(), self.__get_customer_service())