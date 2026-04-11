import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN/install/vln_nav2_bridge'
