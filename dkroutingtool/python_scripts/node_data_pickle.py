# python 3.7

from build_time_dist_matrix import NodeData
from file_config import PickleNodeDataOutput
import build_time_dist_matrix
import pickle

def main():
	node_data = build_time_dist_matrix.process_nodes()
	pickle.dump(NodeData(node_data.df_gps_verbose, node_data.df_bad_gps_verbose, node_data.veh_time_osrmmatrix_dict, node_data.veh_dist_osrmmatrix_dict), open(PickleNodeDataOutput().get_filename() , 'wb'))

if __name__ == '__main__':
	main()