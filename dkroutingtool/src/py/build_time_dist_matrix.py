# python 3.7
"""
Reads in xls of location data, cleans it and writes to a new file.
Computes time and distance matrices for all nodes and vehicles and writes 
to file.
"""
import os
import pathlib
import math
import pandas as pd
import logging
import numpy as np
import copy
from config.config_manager import ConfigManager
from config.gps_input_data import GPSInputData
from output.cleaned_node_data import CleanedNodeData
import time #looking at runtime
import ujson
import osrmbindings

osrm_filepath = os.environ['osm_filename']

verbose = False

class NodeData:
    """Container for all nodes, clean and removed/flagged. Keeps information
    about nodes including name, type, lat/long coordinates and load.
    Also has the ability to keep dictionaries of vehicle profile to OSRM (time 
    or distance) matrix.
    """
    #Define the column names to be used, must have all these columns!
    node_type = GPSInputData.GPS_TYPE_COLUMN_NAME #type of node (e.g. customer, depot)
    node_name = 'name' #name of node (e.g. customer ID or name of an office)
    lat_orig = 'lat_orig' #input lat
    long_orig = 'long_orig'#input long
    flag = 'flag' #label of flag for flagged nodes with potential issue
    zone = 'zone'
    buckets = 'buckets'
    closed = 'closed'

    
    standard_columns = [node_type, node_name, lat_orig, long_orig, closed, zone, buckets]
    standard_columns_bad = standard_columns.copy()
    standard_columns_bad.append(flag)
    
    df_gps_verbose = pd.DataFrame(data=None, columns=standard_columns)
    df_bad_gps_verbose = pd.DataFrame(data=None, columns=standard_columns_bad)
    
    veh_time_osrmmatrix_dict=None
    veh_dist_osrmmatrix_dict=None

    def __init__(self, df_gps, df_bad_gps=None, veh_time_osrmmatrix_dict=None, veh_dist_osrmmatrix_dict=None):
        """
        Instantiates the NodeData class.
        
        Args:
            df_gps (pd dataframe): dataframe conatining all clean/good nodes,
            must contain all columns in NodeData.standard_columns
            df_bad_gps (pd dataframe, default None): all removed/flagged nodes,
            must contain all columns in NodeData.standard_columns_bad
            veh_time_osrmmatrix_dict (dict, default None): dictionary of vehicle profile:time OSRMMatrix objects
            veh_dist_osrmmatrix_dict (dict, default None):dictionary of vehicle profile: distance OSRMMatrix objects
        Returns:
            None
        """
        
        #incoming dataframes must contain the predefined ("standard") columns
        if not set(self.standard_columns).issubset(df_gps.columns):
            raise Exception('Data must contain all the standard column labels')
        if df_bad_gps is not None:
            if not set(self.standard_columns_bad).issubset(df_bad_gps.columns):
                raise Exception('Data must contain all the standard column labels')
        
        self.df_gps_verbose = df_gps
        self.df_bad_gps_verbose = df_bad_gps
        
        #make sure time/dist array sizes line up correctly with number of nodes
        if veh_time_osrmmatrix_dict != None:
            for key, this_orsm_mat in veh_time_osrmmatrix_dict.items():
                array_shape = this_orsm_mat.time_dist_mat.shape
                num_rows = array_shape[0]
                num_cols = array_shape[1]
                if (num_rows != self.df_gps_verbose.shape[0]) or (num_cols != self.df_gps_verbose.shape[0])\
                or (len(array_shape) != 2):
                    raise Exception('Time/Distance matrix size must be the same as the number of nodes')
                    
            self.veh_time_osrmmatrix_dict = veh_time_osrmmatrix_dict
            
        if veh_dist_osrmmatrix_dict != None:
            for key, this_orsm_mat in veh_dist_osrmmatrix_dict.items():
                array_shape = this_orsm_mat.time_dist_mat.shape
                num_rows = array_shape[0]
                num_cols = array_shape[1]
                if (num_rows != self.df_gps_verbose.shape[0]) or (num_cols != self.df_gps_verbose.shape[0])\
                or (len(array_shape) != 2):
                    raise Exception('Time/Distance matrix size must be the same as the number of nodes')
                    
            self.veh_dist_osrmmatrix_dict = veh_dist_osrmmatrix_dict
        
    
    def filter_nodedata(self, dict_filter, filter_name_str=None):
        """
        Creates a new NodeData instance of a subset of the nodes.
        
        Args:
            dict_filter (dict): dict. of str:str or str:list(str) key,val pairs where key is attribute by which to filter
            (must be contained in self.df_gps_verbose, self.df_bad_gps_verbose) and the val is the value
            of the selectable attribute
            filter_name_str (str, default None): optional name of filter to be used for writing to file
        Returns:
            NodeData instance for subset of nodes
        """
        
        #create a boolean series of wanted rows, initialize all to False
        bool_filter_good = pd.Series([False]*self.df_gps_verbose.shape[0], index = self.df_gps_verbose.index)
        bad_df = self.df_bad_gps_verbose
        if bad_df is None:
            bad_df = self.df_gps_verbose.iloc[:0, :].copy()
        bool_filter_bad = pd.Series([False]*bad_df.shape[0], index=bad_df.index)

        for label, val_list in dict_filter.items():
            
            #if single, convert to list
            if isinstance(val_list, str):
                val_list = [val_list]
            
            #iterate through all values
            for val in val_list:
                if (label in ['start', 'end']) or ('unload' in label):
                    label = 'name'
                #create a boolean series from wanted rows for this selection
                this_bool_filter_good = self.df_gps_verbose[label] == val
                this_bool_filter_bad = bad_df[label] == val
            
                #Do an element-wise OR between global mask and this one
                bool_filter_good = bool_filter_good | this_bool_filter_good
                bool_filter_bad = bool_filter_bad | this_bool_filter_bad
    
    
        #select the subtable of time/dist matrices
        veh_time_osrmmatrix_dict_new = {}
        veh_dist_osrmmatrix_dict_new = {}
        for veh, this_orsm_mat in self.veh_time_osrmmatrix_dict.items():
            veh_time_osrmmatrix_dict_new[veh] = OSRMMatrix.get_filtered_osrm_mat(this_orsm_mat, bool_filter_good)
        for veh, this_orsm_mat in self.veh_dist_osrmmatrix_dict.items():
            veh_dist_osrmmatrix_dict_new[veh] = OSRMMatrix.get_filtered_osrm_mat(this_orsm_mat, bool_filter_good)

        #filter the nodes
        df_gps_verbose_new = self.df_gps_verbose.loc[bool_filter_good]
        df_bad_gps_verbose_new = bad_df.loc[bool_filter_bad]
        if len(bad_df) == 0:
            df_bad_gps_verbose_new = None

        #Create new NodeDate object to return
        filtered_node_data = NodeData(
            df_gps_verbose_new, df_bad_gps_verbose_new,
            veh_time_osrmmatrix_dict_new, veh_dist_osrmmatrix_dict_new)

        #Update str used for filename printing
        if filter_name_str is not None:
            filtered_node_data.post_filename_str = filter_name_str
        
        return filtered_node_data
    
        
    def get_time_or_dist_mat(self, veh, time_or_dist='time'):
        """
        Gets time or distance matrix.
        
        Args:
            veh (str): Vehicle profile string for OSRM matrix.
            time_or_dist (str, default 'time'): String identifying is return object is time
            or distance matrix. If 'time', time matrix is returned. If 'dist',
            distance matrix is returned.
        Returns:
            Numpy array of time or dist matrix
        """
        if time_or_dist == 'time':
            return self.veh_time_osrmmatrix_dict[veh].time_dist_mat
        elif time_or_dist == 'dist':
            return self.veh_dist_osrmmatrix_dict[veh].time_dist_mat
        else:
            raise Exception('Please provide appropriate time_or_dist variable.')
        
            
    def get_snapped_gps_coords(self, veh):
        """
        Gets snapped GPS coordinates from time OSRMMatrix derivation.
        
        Args:
            veh (str): Vehicle profile string for OSRM matrix
        Returns:
            Numpy array of sanpped lat-long coordinates for all nodes.
        """
        return self.veh_time_osrmmatrix_dict[veh].snapped_gps_coords
    
    @property
    def lat_long_coords(self):
        """
        Gets original lat-long coordinates for all "clean" nodes.

        Args:
            None
        Returns:
            Numpy array of lat-long coordinates for all nodes.
        """
        return self.df_gps_verbose[[self.lat_orig, self.long_orig]].values	
        
        
    def set_lat_long_coords(self, lat_long_coords):
        """
        Set the lat long coordinates for all nodes.
        
        Args:
            lat_long_coords (nx2 numpy array): array of all lat-long coordinates
        Returns:
            None
        """
        self.df_gps_verbose[[self.lat_orig, self.long_orig]] = lat_long_coords
        
    def get_attr(self, attr):
        """
        Returns an attribute in the NodeData class. Attribute must exist as a field
        in the self.df_gps_verbose.
        
        Args:
            attr (String): name of field
        Returns:
            Numpy array of specified attr for all nodes.
        """
        return self.df_gps_verbose[attr].values
        
    def get_attr_by_index(self, attr, indices):
        """
        Returns an attribute in the NodeData class. Attribute must exist as a field
        in the self.df_gps_verbose.

        Args:
            attr (String): name of field
        Returns:
            Numpy array of specified attr for all nodes.
        """
        return self.df_gps_verbose[attr][indices]
    
    @property
    def type_name(self):
        """
        Gets the type and name for each "clean" node.
        
        Args:
            None
        Returns:
            Numpy array of type/name for all nodes.
        """
        return self.df_gps_verbose[[self.node_type, self.node_name]].values
    
    @property	
    def names(self):
        """
        Gets the names (ID) of all "clean" nodes.
        
        Args:
            None
        Returns:
            Numpy array of names for all nodes.
        """
        return self.df_gps_verbose[self.node_name].values
        
    def get_names_by_index(self, indices):
        """
        Gets the names (ID) by df index.

        Args:
            None
        Returns:
            Numpy array of names for all nodes.
        """
        return self.df_gps_verbose[self.node_name][indices]
            
    @property
    def all_clean_nodes(self):
        """
        Gets all important information for "clean" nodes in one matrix.
        
        Args:
            None
        Returns:
            Numpy array of all standard column values for all "clean" nodes.
        """
        return self.df_gps_verbose[self.standard_columns].values
    
    def write_nodes_to_file(self, f_path_good, f_path_bad=None, verbose=False):
        """Writes nodes to CSV files post-processing. Two files are created: one with clean nodes
        good for use in OSRM, one with nodes that were removed because they would cause cause errors
        with OSRM in the future or flagged (but left in clean nodes) by a user later.
        
        Args:
            f_path_good (str or pathlib.Path): Filename where good clean node information to be written.
            f_path_bad (str or pathlib.Path, default None): Filename where node with issues to be written.
            verbose (boolean, default False): If False, only writes key elements needed down the pipeline.
            If True, writes all information retained from the provided node files.
        Returns:
            None
        """
        if verbose==True:
            self.df_gps_verbose.to_csv(f_path_good, index=False)
            if f_path_bad != None:
                self.df_bad_gps_verbose.to_csv(f_path_bad, index=False)
        else:
            self.df_gps_verbose.to_csv(f_path_good, columns=self.standard_columns, index=False)
            if f_path_bad != None:
                self.df_bad_gps_verbose.to_csv(f_path_bad, columns=self.standard_columns_bad, index=False)

    def __reduce__(self):
        """Helps with pickling."""
        return (NodeData, (self.df_gps_verbose, self.df_bad_gps_verbose, self.veh_time_osrmmatrix_dict, self.veh_dist_osrmmatrix_dict))

    
class NodeLoader:
    """Reads node data, cleans it and creates NodeData class.
    Example of data cleaning includes removing nodes w/o
    GPS coordinates and flagging nodes whose OSRM snapped
    locations are > 200m away from original coordinates."""
    
    #pd dataframe to hold all clean nodes
    df_gps_verbose = pd.DataFrame(data=None, columns=NodeData.standard_columns)
    #pd dataframe to hold removed and flagged nodes
    df_bad_gps_verbose = pd.DataFrame(data=None, columns=NodeData.standard_columns_bad)
    
    #dictionaries with key:val pairs as vehicle profile string: OSRMMatrix object 
    veh_time_osrmmatrix_dict = {}
    veh_dist_osrmmatrix_dict = {}
    
    def __init__(self,
                 config_manager: ConfigManager,
                 zone_configs=None,
                 num_containers_default=3):
        """Initializes the NodeData class.
            Args:
                OSRM time/dist matrices
            Returns:
                None
        """
        self.config_manager = config_manager
        gps_input_data = config_manager.get_gps_inputs_data()
        df_gps_customers = gps_input_data.get_df_gps_customers()
        df_gps_extra = gps_input_data.get_df_gps_extra()

        # Create unload nodes
        unload_depots = []
        unload_idx = 0
        for zone_config in zone_configs:
            if verbose:
                logging.info('Zone config', zone_config)
            if zone_config['enable_unload']:

                # Get all possible start / end locations for the vehicles
                # All start / end locations are assumed to be unload locations
                all_start_end_options = []

                unload_capacity = 0
                for v in zone_config['unload_vehicles']:
                    all_start_end_options.extend(v[2:])
                    if -v[1] < unload_capacity:
                        unload_capacity = -v[1]
                all_start_end_options =  list(set(all_start_end_options))

                zone = zone_config['optimized_region'][0]
                df_temp = df_gps_customers[df_gps_customers['zone'] == zone].copy()
                df_temp['buckets'] = df_temp['buckets'].replace(0, num_containers_default)
                total_demand = sum(df_temp['buckets'])
                unload_number = int(math.ceil(total_demand/-unload_capacity))

                if 'custom_unload_points' in zone_config:
                    custom_unload_list = zone_config['custom_unload_points']
                else:
                    custom_unload_list = []

                for start_end in all_start_end_options + custom_unload_list:
                    df_start_end = df_gps_extra[df_gps_extra['name'] == start_end]
                    start_end_lat, start_end_lon = df_start_end.iloc[0][['lat_orig', 'long_orig']]

                    for _ in range(unload_number):
                        # Will eventually put that into a function that just accepts a couple of parameters...
                        unload_depots.append({'lat_orig': start_end_lat,
                                              'long_orig': start_end_lon,
                                              'name': f'UNLOAD-{start_end}-{unload_idx}',
                                              'Start Date': '2000-01-01',
                                              'closed': 0,
                                              'buckets': unload_capacity,
                                              'zone': zone,
                                              'type' : 'Customer',
                                              'time_windows': np.nan})

                        unload_idx += 1


        if verbose:
            logging.info("Unload depots", unload_depots)

        if len(unload_depots) > 0:
            unload_to_append = pd.DataFrame(unload_depots)
            df_gps_customers = df_gps_customers.append(unload_to_append, ignore_index=True, sort=False)


        #Merge the customer and extra data
        self.df_gps_verbose = df_gps_customers.append(df_gps_extra, ignore_index=True, sort=False)

        self.df_gps_verbose['name'] = self.df_gps_verbose['name'].astype(str)

        #Clean customer data
        self.clean_nodes(max_dist=300)
        #self.clean_nodes()

        #Backfill number of buckets to be max
        self.df_gps_verbose.loc[(self.df_gps_verbose['type'] == 'Customer') & (self.df_gps_verbose['buckets'] == 0), 'buckets'] = num_containers_default
        logging.info(f"Num buckets Assumed: {num_containers_default}")

        #Build the time and distance matrices for all vehicle profiles
        nodes = NodeData(self.df_gps_verbose)
        self.veh_time_osrmmatrix_dict, self.veh_dist_osrmmatrix_dict = NodeLoader.build_veh_matrices(
            config_manager=config_manager, nodes=nodes
        )

    @staticmethod
    def build_veh_matrices(config_manager, nodes):
        veh_time_osrmmatrix_dict = {}
        veh_dist_osrmmatrix_dict = {}
        for veh in config_manager.get_build_parameters().get_vehicle_profiles():
            durations, distances, snapped_gps_coords = NodeLoader.get_matrices(nodes.lat_long_coords, veh)
            veh_time_osrmmatrix_dict[veh] = OSRMMatrix(nodes, durations, snapped_gps_coords)
            veh_dist_osrmmatrix_dict[veh] = OSRMMatrix(nodes, distances, snapped_gps_coords)
        return veh_time_osrmmatrix_dict, veh_dist_osrmmatrix_dict

    def clean_nodes(self, max_dist=None):
        """
        Cleans all the node data. Data cleaning includes removing nodes
        whose contracts closed, dropping points without GPS coordinates
        and and checking to see that the snapped location is within a
        threshold distance.
        
        Args:
            max_dist (int or float, default None): Maximum distance in meters to
            flag for snapped locations too far from original point. If None,
            max distance is not checked as part of the data cleaning.
        Returns:
            None
        """
        
        #Remove lines without a customer id
        self.df_gps_verbose.dropna(subset=[NodeData.node_name], inplace=True)
        
        #Remove points with closed contracts
        # if self.df_gps_verbose[NodeData.cust_contract_close_date].dtypes == datetime.datetime:
        # 	close_contact_index = self.df_gps_verbose[(self.df_gps_verbose[NodeData.cust_contract_close_date] < datetime.datetime.today())].index
        # elif self.df_gps_verbose[NodeData.cust_contract_close_date].dtypes == float:
        # 	close_contact_index = self.df_gps_verbose[(self.df_gps_verbose[NodeData.cust_contract_close_date] == 1.0)].index
        close_contact_index = self.df_gps_verbose[(self.df_gps_verbose[NodeData.closed] == 1.0)].index
        temp_contract_closed_df = self.df_gps_verbose.drop(close_contact_index)
        self.flag_nodes(temp_contract_closed_df, 'Removed - Contract Closed')
        
        #Drop any point that do not have a GPS coordinate and store tham in the bad points
        temp_no_coords_df = self.df_gps_verbose.dropna(subset=[NodeData.lat_orig, NodeData.long_orig])
        self.flag_nodes(temp_no_coords_df, 'Removed - No GPS Coordinates')
                
        #Flag any 'customer' point with no buckets
        temp_no_buckets_df = self.df_gps_verbose.drop(self.df_gps_verbose[(self.df_gps_verbose[NodeData.node_type] == 'Customer') & (self.df_gps_verbose[NodeData.buckets] == 0)].index)
        self.flag_nodes(temp_no_buckets_df, 'Flagged - No containers at location', remove_node=False)
        
        #If doing a check of snapped locations
        if max_dist != None and max_dist > 0:

            flagged_indices = []
            removed_indices = []           
            
            for profile in self.config_manager.get_build_parameters().get_vehicle_profiles():
                veh = profile
                osrmbindings.initialize(f"/{veh}/{osrm_filepath}")
                snapped_lat_profile = []
                snapped_long_profile = []
                snapped_dist_profile = []
            
                for index, df_row in self.df_gps_verbose.iterrows():
                    osrm_nearest_response = osrmbindings.nearest(df_row[NodeData.long_orig], df_row[NodeData.lat_orig])
                    osrm_nearest_response = ujson.loads(osrm_nearest_response)
                
                    if osrm_nearest_response['code'] == "Ok":
                        snapped_lat_profile.append(osrm_nearest_response['waypoints'][0]['location'][1])
                        snapped_long_profile.append(osrm_nearest_response['waypoints'][0]['location'][0])
                        snapped_dist_profile.append(osrm_nearest_response['waypoints'][0]['distance'])
                        
                        if max_dist != None:
                            if osrm_nearest_response['waypoints'][0]['distance'] > max_dist:
                                flagged_indices.append(index)
                    
                    else:
                        snapped_lat_profile.append(None)
                        snapped_long_profile.append(None)
                        snapped_dist_profile.append(None)
                        removed_indices.append(index)
                    
                #Add profile snapped GPS coordinates to df
                self.df_gps_verbose[f'lat_snapped_{veh}'] = snapped_lat_profile
                self.df_gps_verbose[f'long_snapped_{veh}'] = snapped_long_profile
                self.df_gps_verbose[f'snapped_dist_{veh}'] = snapped_dist_profile
        
            
            try:
                removed_indices_series = pd.Series(removed_indices).value_counts()
                flagged_indices_series = pd.Series(flagged_indices).value_counts()
            
                removed_indices = removed_indices_series[removed_indices_series>1].index.to_list()
                flagged_indices = flagged_indices_series[flagged_indices_series>1].index.to_list()
            
                #Remove nodes with bad server code
                temp_bad_code_df = self.df_gps_verbose.drop(index=removed_indices)
                self.flag_nodes(temp_bad_code_df, 'Removed - Bad Server Code')

                #Flag nodes with distance too great
                temp_too_far_df = self.df_gps_verbose.drop(index=flagged_indices)
                self.flag_nodes(temp_too_far_df, 'Flagged - Snapped node location too far from original GPS coordinates.', remove_node=False)
            except:
                logging.error("Could not remove problematic customer nodes")
                
        
        
    def flag_nodes(self, new_df, flag_label, remove_node=True):
        """Flags nodes that encountered any issues.
        
        Args:
            new_df (pandas Dataframe): Filtered Dataframe object containing nodes
            NOT flagged for removal or inspection.
            flag_label (str): Label for the issue with this node
        Returns:
            None
        """
        bad_indices_mask = ~self.df_gps_verbose.index.isin(new_df.index)
        if True in bad_indices_mask:
            removed_df = self.df_gps_verbose[bad_indices_mask].copy()
            removed_df[NodeData.flag] = pd.Series(flag_label, index = removed_df.index)
            self.df_bad_gps_verbose = self.df_bad_gps_verbose.append(removed_df, sort=False)
            #Now, actually remove the rows
            if remove_node:
                self.df_gps_verbose.drop(index = removed_df.index, inplace=True)
                
    def get_nodedata(self):
        """
        Creates a NodeData instance from variables of the NodeLoader class.
        
        Args:
            None
        Returns:
            NodeData object derived from NodeLoader
        """
        
        return NodeData(self.df_gps_verbose, self.df_bad_gps_verbose, self.veh_time_osrmmatrix_dict, self.veh_dist_osrmmatrix_dict)
    
    @staticmethod
    def get_matrices(lat_long_coords, veh):
        """Retrieves the time and distance matrices from OSRM.
        
        Args:
            clean_nodes (NodeData object): all clean nodes
            veh_prof (str): vehicle profile for matrix
        Returns:
            durations (np array): time matrix
            distances (np array): distance matrix
            snapped_gps_coords (np array): snapped gps coordinates
        """
        
        osrmbindings.initialize(f"/{veh}/{osrm_filepath}")

        latitudes = lat_long_coords[:,0].tolist()
        longitudes = lat_long_coords[:,1].tolist()

        response = osrmbindings.table(longitudes, latitudes)
        parsed = ujson.loads(response)

        durations = np.array(parsed["durations"])
        distances = np.array(parsed["distances"])

        snapped_gps_coords = [source["location"] for source in parsed["sources"]]
        snapped_gps_coords = np.fliplr(snapped_gps_coords)

        return durations, distances, snapped_gps_coords

    @staticmethod
    def from_clean_gps_node_data(config_manager, node_data_df) -> NodeData:
        """
        Create a NodeData object from a loaded pre-cleaned dataframe
        """
        veh_time_osrmmatrix_dict, veh_dist_osrmmatrix_dict = NodeLoader.build_veh_matrices(
            config_manager=config_manager, nodes=NodeData(node_data_df)
        )
        return NodeData(node_data_df, None, veh_time_osrmmatrix_dict, veh_dist_osrmmatrix_dict)

class OSRMMatrix:
    """
    A time or distance matrix as generated by OSRM.
    """
    def __init__(self, clean_nodes, time_dist_mat, snapped_gps_coords):
        """Instantiates OSRMMatrix object.

            Args:
                clean_nodes (NodeData object): all clean nodes
                time_or_dist_mat (np array): time or distance matrix
                snapped_gps_coords (np array): snapped GPS coordinates
            Returns:
                None
        """
        self.clean_nodes = clean_nodes
        self.time_dist_mat = time_dist_mat
        self.snapped_gps_coords = snapped_gps_coords
    
    @staticmethod	
    def get_filtered_osrm_mat(orig_osrm_mat, bool_filter):
        """
        Creates a submatrix of a larger OSRM matrix. Helpful for filtering nodes by some attribute (e.g. zone).
        
        Args:
            orig_osrm_mat (OSRM obj): Original OSRMMatrix
            indices (array of ints): indices of desired subset of nodes
        Returns:
            OSRMMatrix object for subset of nodes
        """
        new_osrm_mat = copy.deepcopy(orig_osrm_mat)
        indices = np.ix_(bool_filter)
        new_osrm_mat.clean_nodes.df_gps_verbose = orig_osrm_mat.clean_nodes.df_gps_verbose.loc[bool_filter]
        new_osrm_mat.time_dist_mat = orig_osrm_mat.time_dist_mat[indices[0], :][:, indices[0]]
        new_osrm_mat.snapped_gps_coords = orig_osrm_mat.snapped_gps_coords[indices, :][0]
        return new_osrm_mat
        

    def write_to_file(self, f_path_mat, f_path_gps=None):
        """Writes matrix and snapped gps coordinates to CSV file.
            Args:
                f_path_mat (str or pathlib.Path): Filename where matrix to be written.
                f_path_gps (str or pathlib.Path, default None): Filename where nodes info to be written.
            Returns:
                None
        """
        pd.DataFrame(self.time_dist_mat).to_csv(f_path_mat, index=False, index_label=False, header=False)

        if f_path_gps != None:
            pd.DataFrame(self.snapped_gps_coords,\
            index=self.clean_nodes.names).to_csv(f_path_gps, index=True, index_label=False, header=False)

def process_nodes(config_manager,
                  node_loader_options=None,
                  zone_configs=None) -> NodeData:
    """Reads node data and outputs matrices necessary for optimization."""

    # read in file which contains lat long of each pt
    if node_loader_options != None:
        node_data = NodeLoader(config_manager, zone_configs, **node_loader_options).get_nodedata()
    else:
        node_data = NodeLoader(config_manager).get_nodedata()

    return node_data

start_time = time.time()
if __name__ == '__main__':
    # read in file which contains lat long of each pt
    self.process_nodes()
    
