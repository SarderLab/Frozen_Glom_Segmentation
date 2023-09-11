import numpy as np
import cv2
import matplotlib.pyplot as plt
import os
import skimage.io as skio
#import openslide
import lxml.etree as ET
import girder_client
import json
from wsi_annotations_kit import wsi_annotations_kit as wak
from shapely.geometry import Polygon, Point
from tiffslide import TiffSlide
xml_color = [65280, 65535, 255, 16711680, 33023]
NAMES=['non-gs-glomerulus','gs-glomerulus']
levels = []
def convert_wsi(args, level=4):
    # open slide.svs
    #idi = img_dir.split('.')[0]
    slide0 = TiffSlide(args.input_files)
    levels = slide0.level_dimensions
    print(levels)
    slide = []
    if (len(levels) == 1):
        slide = slide0.read_region((0, 0), 0, levels[0])
    else:
        slide = slide0.read_region((0, 0), 2, levels[2])    
    
    # fetch levels[4] size of whole WSI region (40x -> 2.5x)
    #slide = slide0.read_region((0,0), 0, levels[0])
    #print(len(slide.getbands()))
    slide = np.asarray(slide)
    
    # origin slide is in RGBA format, convert it to RGB and save to model data dir
    slide = cv2.cvtColor(slide, cv2.COLOR_RGBA2RGB)
    if (len(levels) == 1):
        scaled_width = slide.shape[1] // 4
        scaled_height = slide.shape[0] // 4
        scaled_slide = cv2.resize(slide, (scaled_width, scaled_height), interpolation=cv2.INTER_LINEAR)
        skio.imsave(os.path.join(args.basedir+'/tmp', 'slide.png'), scaled_slide.astype("uint8"))
    else: 
        skio.imsave(os.path.join(args.basedir+'/tmp', 'slide.png'), slide.astype("uint8")) 



# convert glom contours to geojson format
def to_geojson(contours, label_glom, args):
    # Iterate through each contour
    json_features = []
    spot_annotations = wak.Annotation()
    spot_annotations.add_names([NAMES[label_glom]])
    for row in contours:
        col_coordinates = row
        # Convert to list to remain consistant with JSON format requirements
        col_coordinates = np.squeeze(col_coordinates) 
        # adding the first corrdinate at the end to form a closed polygon
        col_coordinates = np.insert(col_coordinates, len(col_coordinates),col_coordinates[0].tolist() , axis=0) 
        # Scale factor for width and height
        if(len(levels)==1):
            scale_factor_width = 4
            scale_factor_height = 4
        else:
            scale_factor_width = 16
            scale_factor_height = 16

        # Scale the coordinates of the binary mask
        scaled_coordinates = []
        for coord in col_coordinates:
            # Scale x and y coordinates
            scaled_y = int(coord[0] * scale_factor_width)
            scaled_x = int(coord[1] * scale_factor_height)
            # Append scaled coordinates to the list
            scaled_coordinates.append((scaled_x, scaled_y))
       
        spot_poly = Polygon(scaled_coordinates)
        spot_annotations.add_shape(
                poly=spot_poly,
                box_crs=[0, 0],
                structure=NAMES[label_glom],
                name=None,
                properties=None)
    annot = wak.Histomics(spot_annotations)
        
       
        # if label_glom == 0:
        #     # blue for nonGS
        #     features = {'type': 'Feature', 'geometry': {"type": "Polygon", "coordinates": [scaled_coordinates]},
        #                 'properties':{"isLocked": False, "measurements": [], "classification": {"name":"Segmental Sclerosis", "colorRGB": 255}}}
        #     json_features.append(features)
            
            
        # elif label_glom == 1:
        #     # red for GS
        #     features = {'type': 'Feature', 'geometry': {"type": "Polygon", "coordinates": [scaled_coordinates]},
        #                 'properties':{"isLocked": False, "measurements": [], "classification": {"name":"Global Sclerosis", "colorRGB": 16711680}}}
        #     json_features.append(features)
    folder = args.basedir
    girder_folder_id = folder.split('/')[-2]
    _ = os.system("printf 'Using data from girder_client Folder: {}\n'".format(folder))
    file_name = args.input_files.split('/')[-1]
    gc = girder_client.GirderClient(apiUrl=args.girderApiUrl)
    gc.setToken(args.girderToken)
    files = list(gc.listItem(girder_folder_id))
    item_dict = dict()
    for file in files:
        d = {file['name']: file['_id']}
        item_dict.update(d)
    print(item_dict)
    print(item_dict[file_name])
    _ = gc.post(f'annotation/item/{item_dict[file_name]}', data=json.dumps(annot.json), headers={'X-HTTP-Method': 'POST','Content-Type':'application/json'})            
    return json_features

                