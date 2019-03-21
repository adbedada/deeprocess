

import fiona
import shapely
import rasterio
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from fiona.crs import from_string
from skimage.morphology import skeletonize
from shapely.ops import linemerge
from shapely.geometry import MultiLineString
from shapely.geometry import mapping
from shapely.affinity import affine_transform
from shapely.geometry import asMultiLineString


def vectorize(img, stride=1, tolerance=1, preserve_topology=True, remove_hair=0):
    '''
     converts image to stringline shapely geometry

    :param img: input image to skeletonize
    :param stride: window stride defaulted to 1
    :param tolerance: line simplification tolerance
    :param preserve_topology: maintain the shape of the input
    :param remove_hair: removes deadends created by skeletonization
    :return: multi-string shapely geometry
    '''

    'src-code: https://github.com/SpaceNetChallenge/RoadDetector/blob/master/pfr-solution/code/rd.py'

    # grab all non-zero values
    i,j = np.nonzero(img)
    unscaled_xy = np.c_[j,i]

    # minor expansion to ensure exact fit to borders
    xy = unscaled_xy * stride * (len(img) / (len(img) - 1))
    xy = xy.round(2)
    try:
        u,v = np.array(list(cKDTree(xy).query_pairs(1.5*stride))).T
    except ValueError:
        return linemerge([])

    # Make sure that no triangles will form at T junctions.
    unscaled_xy_set = set(map(tuple, unscaled_xy))
    unscaled_xy_u = unscaled_xy[u]
    unscaled_xy_v = unscaled_xy[v]
    is_diagonal = np.sum((unscaled_xy_v - unscaled_xy_u)**2, axis=-1) == 2
    keep_mask = ~is_diagonal.copy()
    for k in np.flatnonzero(is_diagonal):
        a = unscaled_xy_u[k]
        b = unscaled_xy_v[k]
        c = (a[0], b[1])
        d = (b[0], a[1])
        if c in unscaled_xy_set or d in unscaled_xy_set:
            keep_mask[k] = False
        else:
            keep_mask[k] = True
    u = u[keep_mask]
    v = v[keep_mask]

    # Convert to shapely simplified shape.
    lines = np.array([xy[u], xy[v]]).swapaxes(0,1)
    shape = linemerge(lines).simplify(tolerance, preserve_topology=preserve_topology)

    # Remove any short deadends created by skeletonization.
    if remove_hair:
        strings = list(asMultiLineString(shape))
        arity = {}
        for strn in strings:
            for point in strn.coords:
                arity.setdefault(point, 0)
                arity[point] += 1

        good_strings = []
        for strn in strings:
            if (arity[strn.coords[0]] != 1 and arity[strn.coords[-1]] != 1) \
               or strn.length >= remove_hair:
                good_strings.append(strn)
        shape = MultiLineString(good_strings)

    return shape
    

def image_metadata(img):
    '''
    :param img: input data
    :return: name, x, y, z, width and height
    '''
    src = rasterio.open(img)
    arr = src.read(1)
    name = src.name.split('.')[0]
    y = int(name.split('-')[0])
    x = int(name.split('-')[1])
    z = int(name.split('-')[2])
    width=int(arr.shape[0])
    height=int(arr.shape[1])

    return name, x, y, z,width,height

# prep image for vectorization
def skeltonize_image(img):
    
    src = rasterio.open(img)
    arr = src.read(1)
    
    # set 5 by 5 convolve 
    ball_5 = np.ones((5,5), dtype=int)
    ball_5[0,[0,-1]] = 0
    ball_5[-1,[0,-1]] = 0
    
    # close gaps at segments
    binary_closure = ndimage.binary_closing \
                (np.pad(arr, 9, mode='reflect'),
                 ball_5)[9:-9,9:-9]
    
    # skeletonize
    skltn = skeletonize(binary_closure)
    
    return skltn


def convert_poly_coords(geom, affine_obj):
    '''
     assigns affine transformation to geometry

    :param geom: shapely geometry input data
    :param affine_obj: affine transformation value
    :return: geometry with correct transformation
    '''

    affine_xform = affine_obj
    g = geom
    
    xformed_geom = affine_transform(g,
                                    [affine_xform.a,
                                     affine_xform.b,
                                     affine_xform.d,
                                     affine_xform.e,
                                     affine_xform.xoff,
                                     affine_xform.yoff])
    return xformed_geom


# default coordinate system
crs = rasterio.crs.CRS({"init": "epsg:4326"})


def assign_transform(img, geom):
    '''
     assigns input image affine transformation to geometry
    :param img: input data sourcing the affine values
    :param geom: shapely geometry to assign the assign
    :return: geometry with correct transformation
    '''

    src = rasterio.open(img)
    affine_xform = src.transform
    
    xformed_geom = affine_transform(geom,
                                 [affine_xform.a,
                                  affine_xform.b,
                                  affine_xform.d,
                                  affine_xform.e,
                                  affine_xform.xoff,
                                  affine_xform.yoff])
    return xformed_geom


shp_crs = from_string("+datum=WGS84 \
                              +ellps=WGS84 \
                              +no_defs \
                              +proj=longlat")

shp_schema = {'geometry': 'MultiLineString',
              'properties': {'id': 'int'}}


def export_to_shp(geom, opt_file_name):
    '''
      saves shapely geometry to shapefile

    :param geom: input shapely vector geometry
    :param opt_file_name: output file name
    :return: shapefile output
    '''

    mp = assign_transform(geom)
    # save
    with fiona.open(opt_file_name+'.shp', 
                    'w', 
                    'ESRI Shapefile', crs=shp_crs, 
                    schema=shp_schema)  as output:
            output.write({'geometry':mapping(mp),'properties': {'id':1}})

            
def export_to_geojson(geom, opt_file_name):
    '''
     saves shapely geometry to geojson
    :param geom: shapely geometry
    :param opt_file_name: geojson output file name
    :return: geojson
    '''
    mp = assign_transform(geom)
    
    with fiona.open(opt_file_name+'.geojson', 
                    'w',
                    'GeoJSON', crs=shp_crs,
                    schema=shp_schema)  as output:
            output.write({'geometry':mapping(mp),'properties': {'id':1}})
    


