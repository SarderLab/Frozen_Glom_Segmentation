import argparse
import os

import skimage.io as skio
import json
from skimage.morphology import remove_small_objects
from tqdm import tqdm
import time
import sys
sys.path.append('..')
from glom_code.src.makedata import *
from glom_code.src.makemodel import *
from glom_code.src.reconst import *
from glom_code.src.utils import *

start_time = time.time()

parser = argparse.ArgumentParser()
parser.add_argument('--basedir')
parser.add_argument('--non_gs_model')
parser.add_argument('--gs_model')
parser.add_argument('--input_files')
parser.add_argument('--girderApiUrl')
parser.add_argument('--girderToken')
args = parser.parse_args()

#preprocess WSIs
#inds = os.listdir("./data/WSI")
os.makedirs(args.basedir + '/tmp')
convert_wsi( args, level=2)

print('Finish converting WSIs')

NAMES=['non-gs-glomerulus','gs-glomerulus']
# model parameters
isTrain = False  # set model in testing mode
isContinue = False
#savedir = "./log/"
loadpaths = [args.non_gs_model, args.gs_model]
#loadpaths = ["dk8_UNet_norm_25x_pre249_.pth"]  # load model weights

# iter through Non-GS and GS models
for label_glom, loadpath in enumerate(loadpaths):

    glomtype = "NonGS" if label_glom == 0 else "GS"
    print("label glom")
    print(label_glom)
    print("NonGS Glomerular segmentation model" if label_glom == 0 else "GS Glomerular segmentation model")
    model = GlomNet(isTrain, isContinue, None, loadpath, "UNet")
    # window-slide and centor crop setting  
    patchsize = 256 # center area size
    padding = 64 # boundary that need to be excluded when stitch together

    # for reconstruction, input is a whole slide image
    inds = os.listdir(args.basedir+'/tmp')
    for name in tqdm(inds[:]):
        idi = name.split('.')[0]
        print(idi)

        # read slide image for reconstruction
        img = np.array(Image.open(args.basedir+'/tmp/slide.png'))
        print("slide size", img.shape)

        # pad to a suitable size for window-slide patch extraction
        img,rr,cc = pad_img(img,patchsize)
        # extract all patches from the whole slide with calculated rows and columns
        io_arr_out = np.array(ext(img,rr,cc,patchsize,padding))
        io_arr_out = io_arr_out.reshape(-1,patchsize+padding,patchsize+padding,3)
        print("collected patches size",io_arr_out.shape)
        
        # convert patches into tensor format and add skip flag to 
        # patches on white backgrounds for computation saving
        inputs, skip = to_tensor(io_arr_out)
        results = get_results(model, inputs, skip)
        
        # reconstruct whole slide prediction by stitching output results
        newmask = np.zeros((img.shape[0], img.shape[1]), dtype=bool)
        new_mask = reconst_mask(newmask,results,rr,cc,patchsize,padding)
        # save new mask
        skio.imsave(args.basedir + '/tmp/mask.png', (new_mask*255).astype('uint8'), check_contrast=False)
        
        #Exporting results to a GeoJSON file
        new_mask = skio.imread(args.basedir + '/tmp/mask.png')/255
        new_mask = new_mask.astype(bool)
        # Remove small objects from the mask
        new_mask = remove_small_objects(new_mask, min_size=200)
        #xml_suey(new_mask,[],[],2,1,NAMES[label_glom])
        print("Exporting results to a GeoJSON file")
        # find contour from new mask
        contours = measure.find_contours(new_mask, 0.5)
        # convert contours to geojson format
        json_features = to_geojson(contours, label_glom,args)
        # Create file path by joining directory, filename, and extension
        #geoJSON_file_path = os.path.join('output/json', os.path.basename(idi + '_' + glomtype + '.json'))

        #with open(geoJSON_file_path, 'w') as file:
                #json.dump(json_features, file)
        
    # reprot time cost
    print("--- %.2f seconds ---" % (time.time() - start_time))
 