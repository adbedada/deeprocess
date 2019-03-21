import os
import glob
import rasterio
from osgeo import gdal
from rasterio import transform
from pygeotile.tile import Tile


def open_tile(filename, outdir, OverLapImageWidth):

    '''
     reads tiles and assigns projection and geo-transform

    :param filename: tile name
    :param outdir: directory path for saving outputs
    :param OverLapImageWidth:
    :return:
    '''

    with rasterio.open(filename, 'r') as src:
        mask = src.read()

        # get the x,y,and z from the file name
        x, y, z = map(int,
                      os.path.splitext
                      (os.path.basename(filename))[0].split('-'))

        x, y = [x-1, y]

        # convert x,y,and z values to tile coordinates in meters
        tile = Tile.from_tms(tms_x=x, tms_y=y, zoom=z)

        minpt = tile.bounds[0].meters
        maxpt = tile.bounds[1].meters
        xmin = minpt[0]
        xmax = maxpt[0]
        ymin = minpt[1] * - 1
        ymax = maxpt[1] * - 1

        aff = transform.from_bounds(west=xmin,
                                    south=ymin,
                                    east=xmax,
                                    north=ymax,
                                    width=256,
                                    height=256)

        newOrigin_dx = int(256 - ((OverLapImageWidth - 256)/2))
        newOrigin_dy = int(256 + ((OverLapImageWidth - 256)/2))

        newOrigin_MapCoords = transform.xy(aff,rows=newOrigin_dy,cols=newOrigin_dx,offset='ul')

        new_aff = transform.from_origin(newOrigin_MapCoords[0],
                                        newOrigin_MapCoords[1],
                                        aff[0], aff[4])

        # match output file names with input
        fout = os.path.join(outdir,
                            os.path.basename(os.path.splitext(os.path.basename(filename))[0]) + '.tif')

        profile = {'driver': 'GTiff',
                   'height': OverLapImageWidth,
                   'width': OverLapImageWidth,
                   'count': mask.shape[0],
                   'dtype': rasterio.uint8,
                   "transform": new_aff}

        # save files
        with rasterio.open(fout, 'w', crs='EPSG:3857', **profile) as dst:
            dst.write(mask.astype(rasterio.uint8))


def build_vrt(input_folder, out_vrt_filename='1_mosaic.vrt', input_image_extension=".tif"):

    '''

     Creates virtual dataset (VRT) from a list of images

    :param input_folder: path to images requring vrt
    :param out_vrt_filename: output file name defaulted to mosaic.vrt
    :param input_image_extension: image file extension type defaulted to geotiff
    :return: virtual dataset (vrt) file
    '''

    # list files inside input folder
    files_list = (glob.glob(os.path.
                            join(input_folder,"*{}".
                                 format(input_image_extension))))

    # build vrt for files listed
    gdal.BuildVRT(os.path.join(input_folder,
                               out_vrt_filename),
                  files_list, separate=False)

    print("Built: ", out_vrt_filename)


def main(input_folder, output_folder, input_image_extension, build_vrt_bool = False):

    files_list = (glob.glob(os.path.join(input_folder,"*{}".format(input_image_extension))))

    for i in files_list:
        open_tile(i, output_folder, 256)
        print("Georeferencing: ", i)

    if build_vrt_bool is True:
        build_vrt(input_folder = output_folder)

    if type(build_vrt_bool) != bool :
        raise Exception("build_vrt_bool parameter only accepts booleans")

