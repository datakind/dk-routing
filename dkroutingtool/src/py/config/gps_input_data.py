import attr
import pandas as pd
import logging
import ruamel.yaml
import numpy as np
import pathlib

@attr.s
class GPSInputPaths(object):
    gps_file = attr.ib(type=str)
    custom_header_file = attr.ib(type=str)
    gps_extra_input_file = attr.ib(type=str)

class GPSInput(object):
    def __init__(self, filename, label_map):
        self.filename = filename
        self.label_map = label_map

    def get_filename(self):
        return self.filename

    def get_label_map(self):
        return self.label_map

class CustomerGPSInput(GPSInput):
    def __init__(self, gps_path, custom_header_path):
        # read in file which contains lat long of each customer locations
        yaml = ruamel.yaml.YAML(typ='safe')
        with open(custom_header_path, 'r') as opened:
            loaded_yaml = yaml.load(opened)
            self.cust_label_map = {
                value: key for key, value in loaded_yaml.items()
            } # Simply reverse the mapping

        super().__init__(gps_path, self.cust_label_map)

class ExtraGPSInput(GPSInput):
    extra_label_map = {'GPS (Latitude)':'lat_orig', \
                       'GPS (Longitude)':'long_orig', \
                       'name': 'name', \
                       'type': 'type'
                       }
    def __init__(self, path):
        super().__init__(path, self.extra_label_map)

class GPSInputData(object):

    GPS_TYPE_COLUMN_NAME = 'type'

    def __init__(self, df_gps_customers, df_gps_extra):
        self.df_gps_customers = df_gps_customers
        self.df_gps_extra = df_gps_extra

    def get_df_gps_customers(self) -> pd.DataFrame:
       return self.df_gps_customers

    def get_df_gps_extra(self) -> pd.DataFrame:
       return self.df_gps_extra

    @staticmethod
    def load(paths: GPSInputPaths):
        customer_gps_data = CustomerGPSInput(paths.gps_file, paths.custom_header_file)
        extra_gps_data = ExtraGPSInput(paths.gps_extra_input_file)
        df_gps_customers = GPSInputData.read_node_file(customer_gps_data.get_filename(),
                                                       customer_gps_data.get_label_map())
        #Add a column describing the type of point
        df_gps_customers[GPSInputData.GPS_TYPE_COLUMN_NAME] = pd.Series('Customer', index=df_gps_customers.index)

        df_gps_extra = GPSInputData.read_node_file(extra_gps_data.get_filename(),
                                                   extra_gps_data.get_label_map())
        return GPSInputData(
            df_gps_customers, df_gps_extra
        )


    @staticmethod
    def read_node_file(f_path, label_map=None):
        """
        Reads file containing node information and maps

        Args:
            f_path (str or pathlib.Path): File with node information.
            label_map (dictionary, default None): dictionary maps file labels to NodeData attributes
        Returns:
            pandas Dataframe containing all nodes from file
        """

        #If filename is f_path, convert to pathlib.Path object
        if isinstance(f_path, str):
            f_path = pathlib.Path(f_path)

        #if file doesn't exist, throw exception
        if not f_path.exists():
            raise FileNotFoundError(f_path)
        else:
            #read in the file
            if str(f_path).endswith('.xlsx'):
                df_gps_all = pd.read_excel(f_path)
            elif str(f_path).endswith('.csv'):
                #Check different encoding possiblities
                #Encoding possilbities
                csv_encodings = ['utf-8', 'cp1252', 'latin1']
                try:
                    df_gps_all = pd.read_csv(f_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df_gps_all = pd.read_csv(f_path, encoding='cp1252')
            else:
                raise Exception('File should be either a .xlsx or .csv file.')

        #Standardizing colummn labels
        if label_map != None:
            for key,val in label_map.items():
                if key not in df_gps_all.columns:
                    logging.info(f'Missing {(key,val)}, adding substition')
                    if val == 'closed':
                        df_gps_all[key] = 0
                    elif val == 'time_windows':
                        df_gps_all[key] = np.nan
                    else:
                        df_gps_all[key] = ''
                    #raise Exception('Label not found.')
            df_gps_all.rename(index=str, columns=label_map, inplace=True)

        return df_gps_all
