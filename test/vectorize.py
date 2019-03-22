
from deeprocess.vectorize import extract_vector


input_vrt = "mosaic.vrt"
output_vrt = "output"


extract_vector(input_vrt = input_vrt,output_name=output_vrt, save_as='geojson')
print ('Task is completed!')

