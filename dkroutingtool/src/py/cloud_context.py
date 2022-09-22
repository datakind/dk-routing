from abc import ABC, abstractmethod
import logging
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
import json

def initialize_cloud_client(scenario, file_manager):
    try:
        context = os.environ["CLOUDCONTEXT"]
    except KeyError as e:
        raise Exception('!! No Cloud Context Supplied.. are you trying to run local? (--local) !!', e)

    logging.info(f'Using Cloud Contex:  {context}')
    if context.upper() == 'GDRIVE':
        cloud_client = GoogleDriveContext(scenario, file_manager)
    else:
        raise Exception(f"Context Not Implemented: {context}")

    return cloud_client


class GoogleDriveContext():
    def __init__(self, scenario_name: str, file_manager):
        super().__init__()
        self.file_manager = file_manager
        try:
            customer_file_id = os.environ["GDRIVECUSTOMERFILEID"]
            facility_file_id = os.environ["GDRIVEEXTRAFILEID"]
            root_folder_id = os.environ["GDRIVEROOTFOLDERID"]
            creds_file = os.environ.get("GDRIVECREDSFILE", "gdrive_creds.json")
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
        self.sheet_service = self.build_service(creds_file, 'sheets', 'v4', self.SHEET_SCOPES) #Make sure json is there
        self.drive_service = self.build_service(creds_file, 'drive', 'v3', self.DRIVE_SCOPES)
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
                logging.warning("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                logging.warning("YOU NEED TO RE-AUTHORIZE THIS APPLICATION TO USE GDRIVE")
                logging.warning("YOU MAY NEED TO DO THIS TWICE IN A ROW")
                logging.warning("STEP1: Click the link and allow - sign in using an authorizer user for Gdrive")
                logging.warning("Get the authorization code and paste it into the terminal.")
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
                # Note run_console is need because of the docker contain
                cred = flow.run_console()

            with open(token_name, 'wb') as token:
                pickle.dump(cred, token)

        try:
            service = build(api_service_name, api_version, credentials=cred)
            return service
        except Exception as e:
            logging.error(e)
        return service

    def download_input_data(self, local_dir):
        """Get input data for running the model"""
        # Load Data
        customer_data = self._get_sheet_by_id(self.customer_file_id,
                                              self._update_rangename('Customer Data'))
        facility_data = self._get_sheet_by_id(self.facility_file_id,
                                              self._update_rangename('extra_points'))
        # Save Data
        customer_data.to_excel(f"{local_dir}/customer_data.xlsx", index=False)
        facility_data.to_csv(f"{local_dir}/extra_points.csv", index=False)
        config_file_id = self._get_file_id_from_name('config.json', folder_id=self.scenario_folder_id)
        self._load_and_save_json_file(config_file_id, local_dir)

    def download_manual_edits_data(self, local_dir):
        source_folder_name = f'{self.scenario_name}-manual-input'
        source_folder_id = self._get_folder_id_from_name(source_folder_name)
        local_dir = f"{local_dir}/manual_edits"
        os.makedirs(local_dir, exist_ok=True)
        files = [
            self.file_manager.output_config.manual_edit_gps_path.name,
            self.file_manager.output_config.manual_edit_route_xlsx_path.name,
            self.file_manager.output_config.manual_edit_vehicles_path.name,
        ]
        for file in files:
            logging.info(f"Downloading {file} from {source_folder_name} to {local_dir}")
            if file.endswith("csv"):
                dl_fn = self._load_and_save_csv_file
            else:
                dl_fn = self._load_and_save_sheet_file
            dl_fn(
                self._get_file_id_from_name(file, folder_id=source_folder_id),
                file,
                local_dir
            )

    def upload_data(self, file_to_upload, out_folder, filename=None):
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
            logging.error('No data found.')
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
            logging.error(e)
    
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
        logging.info('Sheet successfully Updated')
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

    def _load_and_save_json_file(self, file_id, local_dir):
        service = self.drive_service
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk() 
        fh.seek(0)
        config = json.loads(fh.read())
        with open(f"{local_dir}/config.json", 'w') as outfile:
            json.dump(config, outfile)
        return 

    def _load_and_save_csv_file(self, file_id, filename, output='data'):
        service = self.drive_service
        assert file_id is not None
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
