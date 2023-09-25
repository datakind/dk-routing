from urllib.parse import parse_qs, urlparse
from googleapiclient.discovery import build
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
from apiclient import errors

def run_console_hack(flow):
    flow.redirect_uri = 'http://localhost:1'
    auth_url, _ = flow.authorization_url()
    print(
        "Visit the following URL:",
        auth_url,
        "After granting permissions, you will be redirected to an error page",
        "Copy the URL of that error page (http://localhost:1/?state=...)",
        sep="\n"
    )
    redir_url = input("URL: ")
    code = parse_qs(urlparse(redir_url).query)['code'][0]
    flow.fetch_token(code=code)
    return flow.credentials

def build_service(client_secret_file, api_service_name, api_version,*scopes):
        print(scopes)
        SCOPES = [scope for scope in scopes[0]]
        # If modifying scopes, delete the file token.pickle.
        cred = None
        token_name = f'{api_service_name}_{api_version}.pickle'
        if os.path.exists(token_name):
            with open(token_name, 'rb') as token:
                cred = pickle.load(token)

        if not cred or not cred.valid:
            if cred and cred.expired and cred.refresh_token:
                cred.refresh(Request())
            else:
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("YOU NEED TO RE-AUTHORIZE THIS APPLICATION TO USE GDRIVE")
                print("YOU MAY NEED TO DO THIS TWICE IN A ROW")
                print("STEP1: Click the link and allow")
                print("Get the authorization code and paste it into the terminal.")
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
                # Note run_console is need because of the docker contain
                cred = run_console_hack(flow)

            with open(token_name, 'wb') as token:
                pickle.dump(cred, f'gdrive_tests/{token}')

        try:
            service = build(api_service_name, api_version, credentials=cred)
            return service
        except Exception as e:
            print(e)
        return service

SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
                              'https://www.googleapis.com/auth/drive',
                              'https://www.googleapis.com/auth/drive.file',
                              'https://www.googleapis.com/auth/drive.appdata',
                              'https://www.googleapis.com/auth/drive.scripts',
                              'https://www.googleapis.com/auth/drive.metadata']



def main():
    print(SHEET_SCOPES)
    build_service('gdrive_tests/gdrive_creds.json','sheets', 'v4', SHEET_SCOPES) # customize path
    build_service('gdrive_tests/gdrive_creds.json','drive', 'v3', DRIVE_SCOPES) 

if __name__ == "__main__":
    main()