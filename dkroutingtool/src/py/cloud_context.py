from abc import ABC, abstractmethod
import boto3
import pandas as pd
import os
import io
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import os.path
from apiclient import errors
import json
import datetime
import shutil

def initialize_cloud_client(scenario, manual_mapping_mode):
    # First retreive the cloud context environment variable
    try:
        context = os.environ["CLOUDCONTEXT"]
    except KeyError as e:
        raise Exception('!! No Cloud Context Supplied.. are you trying to run local? (--local) !!', e)

    print(f' *   Using Cloud Contex:  {context}')
    if context.upper() == 'AWS':
        cloud_client = AWSS3Context(scenario)
    elif context.upper() == 'GDRIVE':
        cloud_client = GoogleDriveContext(scenario)
    else:
        raise Exception(f"Context Not Implemented: {context}")
    cloud_client.get_input_data(manual=manual_mapping_mode)
    return cloud_client

class StorageContext(ABC):
    
    """
    Tool storage context base class 
    """

    @abstractmethod
    def build_service(self, dkocr):
        """
        Create connection to whatever storage we are using 
        """

        pass

    """ Optional APIs """

    def get_input_data(self):
        """
        List available models to this driver.
        """

        raise Exception("Unsupported")

    def upload_data(self):
        """
        Train a custom model
        """

        raise Exception("Unsupported")

    def upload_results(self, cloud_client, filenames=None, manual_filenames=None, scenario='input',
         manual=False):
        """
        docstring
        """

        client = cloud_client

        output_time = datetime.datetime.utcnow().isoformat().split(".")[0]

        if manual:
            shutil.copy(
                "/manual_edits/manual_solution.txt", "/manual_edits/maps/manual_solution.txt")

            shutil.make_archive(f"{output_time}-{scenario}-manual", "zip", "/manual_edits/maps/")

            to_upload = f"{output_time}-{scenario}-manual.zip"
            client.upload_data(to_upload, "output")

        else:
            if filenames is None:
                shutil.copy("solution.txt", "/maps/solution.txt")
                shutil.copy("instructions.txt", "/maps/instructions.txt")
                shutil.copy("data/config.json", "/maps/config.json")
                shutil.copy("data/gps_data_clean/dropped_flagged_gps_points.csv", "/maps/dropped_flagged_gps_points.csv")
                shutil.copy("/manual_edits/manual_routes_edits.xlsx", "/maps/manual_routes_edits.xlsx")

            shutil.make_archive(f"{output_time}-{scenario}", "zip", "/maps/")

            to_upload = f"{output_time}-{scenario}.zip"
            client.upload_data(to_upload, "output")

            if manual_filenames is None:
                manual_filenames = []
                manual_filenames.extend(glob.glob("/manual_edits/*.csv"))
                manual_filenames.extend(glob.glob("/manual_edits/*.xlsx"))

            for manual_filename in manual_filenames:
                client.upload_data(manual_filename,
                                   f"{scenario}-manual-input",
                                   filename=manual_filename.split('/')[-1])
        return

class FileDoesNotExistError(Exception):
    pass

class AWSS3Context(StorageContext):
    def __init__(self, scenario_name, file_manager):
        super().__init__(file_manager)
        self.bucket_name = os.environ['AWSBUCKETNAME']
        self.service = self.build_service()
        self.scenario_name = scenario_name
        
    def build_service(self):
        """Will need proper credential management, probably"""

        try:
            AWSKEY = os.environ["AWSACCESSKEYID"]
            SECRET = os.environ["AWSSECRETACCESSKEY"]
            service = boto3.client(
                's3',
                aws_access_key_id=AWSKEY,
                aws_secret_access_key=SECRET)
            return service
        except KeyError:
            raise Exception("AWS Environment Variables are Not Set or Faulty.")


    def get_input_data(self, manual):
        """Get input data for running the model"""

        filenames = [
            "customer_data.xlsx",
            "extra_points.csv",
            "config.json"]

        for filename in filenames:
            try:
                self.service.download_file(self.bucket_name,
                                       f"{self.scenario_name}/{filename}",
                                       f"data/{filename}")
            except Exception:
                raise FileDoesNotExistError(f'File: {filename} was not found on AWS - check that the file exists and it is in correct S3 Bucket')

        if manual:
            manual_filenames = [
                "manual_routes_edits.xlsx",
                "manual_vehicles.csv",
                "clean_gps_points.csv"
                ]

            for manual_filename in manual_filenames:
                try:
                    self.service.download_file(self.bucket_name, 
                                            f"{self.scenario_name}-manual-input/{manual_filename}",
                                            f"manual_edits/{manual_filename}")
                except Exception:
                    raise FileDoesNotExistError(f'File: {manual_filename} was not found on AWS - check that the file exists and it is in correct S3 Bucket')


    def upload_data(self, file_to_upload, out_folder, filename=None):

        if filename is None:
            filename = file_to_upload
        try:
            self.service.upload_file(file_to_upload, self.bucket_name, f"{out_folder}/"+filename)
        except Exception as e:
            print("Error-->", e)

class GoogleDriveContext(StorageContext):
    def __init__(self, scenario_name, file_manager):
        super().__init__(file_manager)

        try:
            customer_file_id = os.environ["GDRIVECUSTOMERFILEID"]
            facility_file_id = os.environ["GDRIVEEXTRAFILEID"]
            root_folder_id = os.environ["GDRIVEROOTFOLDERID"]
        except KeyError as e:
            raise Exception('Customer, Facility ID or Root Folder ID not found', e)

        self.customer_file_id = customer_file_id
        self.facility_file_id = facility_file_id
        self.scenario_name = scenario_name
        self.SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
                              'https://www.googleapis.com/auth/drive',
                              'https://www.googleapis.com/auth/drive.file',
                              'https://www.googleapis.com/auth/drive.appdata',
                              'https://www.googleapis.com/auth/drive.scripts',
                              'https://www.googleapis.com/auth/drive.metadata']
        self.sheet_service = self.build_service('gdrive_creds.json', 'sheets', 'v4', self.SHEET_SCOPES) #Make sure json is there
        self.drive_service = self.build_service('gdrive_creds.json', 'drive', 'v3', self.DRIVE_SCOPES)
        self.root_folder = root_folder_id
        self.scenario_folder_id = self._get_folder_id_from_name(scenario_name)

    def build_service(self, client_secret_file, api_service_name, api_version, *scopes):
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
                print("STEP1: Click the link and allow - sign in using an authorizer user for Gdrive")
                print("Get the authorization code and paste it into the terminal.")
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
                # Note run_console is need because of the docker contain
                cred = flow.run_console()

            with open(token_name, 'wb') as token:
                pickle.dump(cred, token)

        try:
            service = build(api_service_name, api_version, credentials=cred)
            return service
        except Exception as e:
            print(e)
        return service

    def get_input_data(self, manual):
        """Get input data for running the model"""

        # Load Data
        customer_data = self._get_sheet_by_id(self.customer_file_id,
                                              self._update_rangename('Customer Data'))
        facility_data = self._get_sheet_by_id(self.facility_file_id,
                                              self._update_rangename('extra_points'))
        # Save Data
        customer_data.to_excel('data/customer_data.xlsx', index=False)
        facility_data.to_csv('data/extra_points.csv', index=False)        
        config_file_id = self._get_file_id_from_name('config.json', folder_id=self.scenario_folder_id)
        self._load_and_save_json_file(config_file_id)
 
        if manual:
            source_folder_name = f'{self.scenario_name}-manual-input'
            source_folder_id = self._get_folder_id_from_name(source_folder_name)
            self._load_and_save_csv_file(
                self._get_file_id_from_name('clean_gps_points.csv', 
                                            folder_id=source_folder_id),
                                             'clean_gps_points.csv',
                                             'manual_edits'
                )

            self._load_and_save_csv_file(
                self._get_file_id_from_name('manual_vehicles.csv', 
                                            folder_id=source_folder_id),
                                            'manual_vehicles.csv',
                                            'manual_edits'
                )

            self._load_and_save_sheet_file(
                self._get_file_id_from_name('manual_routes_edits.xlsx', 
                                            folder_id=source_folder_id),
                                            'manual_routes_edits.xlsx',
                                            'manual_edits'
                )

    def upload_data(self, file_to_upload, out_folder, filename=None):

        drive_service = self.drive_service
        sheet_service = self.sheet_service

        if filename is None:
            filename = file_to_upload

        parent_folder = self._get_folder_id_from_name(out_folder) 
        if parent_folder==False:
            parent_folder = self._create_folder(self.root_folder, out_folder)
        
        if file_to_upload.endswith('.csv'):
            # Do simple file upload 
            self._upload_raw_file_to_drive(file_to_upload, parent_folder, filename)

        elif file_to_upload.endswith('.xlsx'):
            # use excel upload function 
            self._upload_raw_file_to_drive(file_to_upload, parent_folder, filename)

        elif file_to_upload.endswith('.zip'):
            self._upload_raw_file_to_drive(file_to_upload, parent_folder, filename)
        return

    def _update_rangename(self, worksheet_name):
        return f'{worksheet_name}!A1:Z'
    
    def _get_sheet_by_id(self, SPREADSHEET_ID, RANGE_NAME):
        """Get data of sheet
        """
        service = self.sheet_service
        spreadsheets = service.spreadsheets()
        # Call the Sheets API
        result = spreadsheets.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=RANGE_NAME).execute()
        values = result.get('values', [])
        if not values:
            print('No data found.')
        return pd.DataFrame(values[1:], columns = values[0])

    def _create_sheet(self, parent_folder, sheetname):
        service = self.drive_service
        file_metadata = {
            'name': sheetname,
            'parents': [parent_folder],
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }
        res = service.files().create(body=file_metadata).execute()
        return 
    
    def _create_folder(self, parent_folder, folder_name):
        service = self.drive_service
        file_metadata = {
            'name': folder_name,
            'parents': [parent_folder],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        file = service.files().create(body=file_metadata,
                                            fields='id').execute()
        return file.get('id')
    
    def _add_worksheets_to_sheet(self, sheet_id, sheet_name):
        service = self.drive_service
        spreadsheets = service.spreadsheets()
        try:
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }

            response = spreadsheets.batchUpdate(
                spreadsheetId=sheet_id,
                body=request_body
            ).execute()
            return response 
        except Exception as e:
            print(e)
    
    def _save_data_to_worksheet(self, sheet_id, workbook_name, df):
        service = self.sheet_service
        response_date = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            valueInputOption='RAW',
            range=f'{workbook_name}!A1:AZ',
            body=dict(
                majorDimension='ROWS',
                values=df.T.reset_index().T.values.tolist())
        ).execute()
        print('Sheet successfully Updated')
        return 
        
    def _get_folder_id_from_name(self, folder_name):
        # TODO add a parent here - want to make sure we are grabbing the right folder
        service = self.drive_service

        page_token = None
        while True:
            
            response = service.files().list(q=f"parents in '{self.root_folder}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                                                  spaces='drive',
                                                  fields='nextPageToken, files(id, name)',
                                                  pageToken=page_token).execute()
            for file in response.get('files', []):
                if file.get('name') == folder_name:
                    return file.get('id')
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return False
    
    def _retrieve_all_files(self):
        """Retrieve a list of File resources.

        Args:
        service: Drive API service instance.
        Returns:
        List of File resources.
        """
        service = self.drive_service
        result = []
        page_token = None
        while True:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            files = service.files().list(**param).execute()
            print(files)
            result.extend(files['files'])
            page_token = files.get('nextPageToken')
            if not page_token:
                break
        return result
    
    def _get_file_id_from_name(self, filename, folder_id=None):
        service = self.drive_service
        page_token = None
        while True:
            response = service.files().list(q= f"'{folder_id}' in parents",
                                                  spaces='drive',
                                                  fields='nextPageToken, files(id, name)',
                                                  pageToken=page_token).execute()
            for file in response.get('files', []):
                # Process change
                if file.get('name') == filename:
                    return file.get('id')
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return None

    def _load_and_save_json_file(self, file_id):
        service = self.drive_service
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk() 
        fh.seek(0)
        config = json.loads(fh.read())
        with open('data/config.json', 'w') as outfile:
            json.dump(config, outfile)
        return 

    def _load_and_save_csv_file(self, file_id, filename, output='data'):
        service = self.drive_service
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk() 
        fh.seek(0)
        f = fh.read()
        s=str(f,'utf-8')
        data = io.StringIO(s) 
        pd.read_csv(data).to_csv(f'{output}/{filename}', index=False)

        return 

    def _load_and_save_sheet_file(self, file_id, filename, output='data'):
        service = self.drive_service
        excel_mime ='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        request = service.files().export_media(fileId=file_id, 
                                               mimeType=excel_mime)
        with open(f'{output}/{filename}', 'wb') as f:
            f.write(request.execute())  

        return 
  
    def _upload_raw_file_to_drive(self, filename, parent_folder, output_filename):
        service = self.drive_service
        mime_type = 'application/vnd.google-apps.spreadsheet' if filename.endswith('.xlsx') else '*/*'
        file_metadata = {
            'name': output_filename,
            'mimeType': mime_type,
            'parents': [parent_folder]
        }
        media = MediaFileUpload(filename,
                                mimetype='*/*',
                                resumable=True)

        existing_file = self._get_file_id_from_name(output_filename, 
                                                    folder_id=parent_folder)
        # Lets overwrite
        if existing_file is not None:
            file = service.files().get(fileId=existing_file).execute()
            del file['id']  # 'id' has to be deleted
            service.files().update(
                    fileId=existing_file,
                    body=file,
                    media_body=media).execute()
        # Create new
        else:
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
