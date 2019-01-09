#######################################################################################################################
# ------ PhotoScan workflow Part 2: -----------------------------------------------------------------------------------
# ------  bundle adjustment and Dense point cloud creation -----------------------------------------
# ------ Written for PhotoScan 1.4.3 64 bit -------------------------------------------------------------------------
#######################################################################################################################

import PhotoScan as PS
import os
import csv
import inspect
from datetime import datetime
import sys
import time

# Clear the Console screen
PS.app.console.clear()  # deactivate when running on ISCA

# GET TIME

startTime = datetime.now()
print ("Script start time: " + str(startTime))
#####################################################################################################################

def script_setup():
    file_loc = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    input_file_B = (file_loc + "/" + "input_file.csv")
    input_file_B = input_file_B.replace('\\', '/')

    print (input_file_B)

    var_list = []

    with open(input_file_B, 'r') as f:
        mycsv = csv.reader(f)
        for row in mycsv:
            colB = row[1]
            var_list.append(colB)

    home = var_list[1]

    doc_title = var_list[2]

    datadir = var_list[3]

    coord_sys = var_list[4]

    exportdir = var_list[7]

    dpc_quality = var_list[11]

    pair_dm_lim = var_list[33]
    pair_dm_val = var_list[34]

    pair_dpc_lim = var_list[35]
    pair_dpc_val = var_list[36]

    # create export directory if it doesn't already exist
    if os.path.exists(exportdir):
        print ("export folder exists")
    else:
        print ("creating export folder...")
        os.makedirs(exportdir)

    print (home)
    print(doc_title)
    print (datadir)
    print (coord_sys)
    name = "/" + doc_title + ".psx"

    doc = PS.app.document
    PS.app.gpu_mask = 2 ** len(PS.app.enumGPUDevices()) - 1  # activate all available GPUs
    if PS.app.gpu_mask <= 1:
        PS.app.cpu_enable = True  # Enable CPU for GPU accelerated processing (faster with 1 no difference with 0 GPUs)
    elif PS.app.gpu_mask > 1:
        PS.app.cpu_enable = False # Disable CPU for GPU accelerated tasks (faster when multiple GPUs are present)

    if os.path.exists(home + '/' + doc_title + '.files/lock'):
        try:
            print("removing lock file...")
            os.remove(home + '/' + doc_title + '.files/lock')
            print("lock file removed")
        except IOError:
            print ("running interactively... continue")
    doc.open(home + name, read_only=False)
    chunk = doc.chunk

    if not check_markers(chunk):
        print("quiting initiated")
        time.sleep(3)
        # doc.save(home + name)
        PS.app.quit()
        sys.exit()

    count_aligned(chunk)

    Optimise_Bundle_adj(chunk, doc, home, name, doc_title)

    n_cams_enabled_DPC, n_points_final_SPC, n_points_orig_DPC, outside_BB = build_DPC(chunk, dpc_quality, pair_dm_lim, pair_dm_val,
                                                                          pair_dpc_lim, pair_dpc_val)
    doc.save(home + name)

    export_settings(home, doc_title, outside_BB, n_points_final_SPC, n_points_orig_DPC, n_cams_enabled_DPC)

    
    doc.save(home + "/" + doc_title + "_backup2.psx", doc.chunks)
#####################################################################################################################

def check_markers(chunk):
    n_markers = len(chunk.markers)
    quit_yn = None
    if n_markers == 0:
        print ("No markers are present - continue...")
        quit_yn = True


    else:
        enabled_markers = []
        for marker in chunk.markers:
            if marker.reference.enabled == True:
                enabled_markers.append(marker)

        n_enabled_mark = len(enabled_markers)

        if n_markers <= 3:
            if n_enabled_mark < n_markers:
                print ("SCRIPT ABORTED: Only " + str(n_markers) + " Markers present. Enable all markers!!!" + "\n" +
                       "CLOSING PHOTOSCAN........")

                quit_yn = False

            elif n_enabled_mark == n_markers:
                print (str(n_markers) + " Markers present - All enabled" + "\n" +
                       "continue...")
                quit_yn = True

        elif n_markers > 3:
            if n_enabled_mark == n_markers:
                print ("SCRIPT ABORTED: " + str(n_markers) + " present - All enabled" + "\n" +
                       "At least 1 marker must be disabled for use as validation marker - Disable Marker(s)" + "\n" +
                       "CLOSING PHOTOSCAN.........")

                quit_yn = False

            elif n_enabled_mark < n_markers:
                print (str(n_markers) + " markers in total." + "\n" + str(n_enabled_mark) +
                       " enabled Ground Control Points" + "\n" +
                       str(n_markers-n_enabled_mark) + " verification markers" + "\n" + "Continue...")

                quit_yn = True

    return quit_yn



def count_aligned(chunk): # GET NUMBER OF ALIGNED AND NOT-ALIGNED CAMERAS: Check if this belongs here or in script 1
    aligned_list = list()
    for camera in chunk.cameras:
        if camera.transform:
            aligned_list.append(camera)

    not_aligned_list = list()
    for camera in chunk.cameras:
        if not camera.transform:
            not_aligned_list.append(camera)
            camera.enabled = False

    n_aligned = len(aligned_list)

    n_not_aligned = len(not_aligned_list)

    print ("number (%) of aligned cameras is:")
    print (str(n_aligned) + "(" + str(n_aligned / (n_aligned + n_not_aligned) * 100) + "%)")
    print ("number of cameras not aligned is:")
    print (str(n_not_aligned) + "(" + str(n_not_aligned / (n_aligned + n_not_aligned) * 100) + "%)")



def Optimise_Bundle_adj(chunk, doc, home, name, doc_title):
    chunk.optimizeCameras(fit_f=True, fit_cx=True, fit_cy=True, fit_b1=True,
                          fit_b2=True, fit_k1=True, fit_k2=True, fit_k3=False,
                          fit_k4=False, fit_p1=True, fit_p2=True, fit_p3=False,
                          fit_p4=False)  # As suggested in James, et al. (2017)
    print ("Optimization Parameters:")
    print (PS.app.document.chunk.meta['optimize/fit_flags'])

    print("save")
    doc.save(home + name)
    doc.save(home + "/" + doc_title + "_backup.psx", doc.chunks) # enable after testing!!!!!!



def build_DPC(chunk, dpc_quality, pair_dm_lim, pair_dm_val, pair_dpc_lim, pair_dpc_val):


    chunk.resetRegion()  # reset bounding region following the manual point cleaning
    region = chunk.region
    region.size = 1.5 * region.size  # increase bounding region 2 times
    chunk.region = region  # set new region

    #####  Check number of enabled cameras ###
    camlist = []
    for camera in chunk.cameras:
        if camera.enabled:
            camlist.append(camera)

    n_cams_enabled_DPC = len(camlist)

    ## check number of points in final sparse cloud ###
    # first check n points outside bounding box: ###
    R = chunk.region.rot
    C = chunk.region.center
    size = chunk.region.size
    for point in chunk.point_cloud.points:
        if point.valid:
            v = point.coord
            v.size = 3
            v_c = v - C
            v_r = R.t() * v_c
            if abs(v_r.x) > abs(size.x / 2.):
                point.selected = True
            elif abs(v_r.z) > abs(size.z / 2.):
                point.selected = True
            elif abs(v_r.y) > abs(size.y / 2.):
                point.selected = True
            else:
                continue

    outside_BB = len([p for p in chunk.point_cloud.points if p.selected])
    print ("number of points outside BB is:" + str(outside_BB))

    n_points_final_SPC = len(chunk.point_cloud.points) - outside_BB

    if pair_dm_lim == "TRUE":  # This part determines if a pair limit is required for depth map filtering
        print ("Depth map pair filtering enabled: limit = " + str(pair_dm_val))
        PS.app.settings.setValue('main/depth_filtering_limit', float(pair_dm_val))  # sets value based on input file
    else:
        PS.app.settings.setValue('main/depth_filtering_limit', -1)  # restores default

    if pair_dpc_lim == "TRUE":  # This part determines if a pair limit is required for depth map filtering
        print ("Dense cloud pair filtering enabled: limit = " + str(pair_dpc_val))
        PS.app.settings.setValue('main/dense_cloud_max_neighbors', float(pair_dpc_val))  # sets value based on input file
    else:
        PS.app.settings.setValue('main/dense_cloud_max_neighbors', -1)


    print ("building Dense Point Cloud...")
    if dpc_quality == "LowestQuality":
        chunk.buildDepthMaps(quality=PS.LowestQuality, filter=PS.MildFiltering, reuse_depth=True)
    elif dpc_quality == "LowQuality":
        chunk.buildDepthMaps(quality=PS.LowQuality, filter=PS.MildFiltering, reuse_depth=True)
    elif dpc_quality == "MediumQuality":
        chunk.buildDepthMaps(quality=PS.MediumQuality, filter=PS.MildFiltering, reuse_depth=True)
    elif dpc_quality == "HighQuality":
        chunk.buildDepthMaps(quality=PS.HighQuality, filter=PS.MildFiltering, reuse_depth=True)
    elif dpc_quality == "UltraQuality":
        chunk.buildDepthMaps(quality=PS.UltraQuality, filter=PS.MildFiltering, reuse_depth=True)
    else:
        print ("---------------------------------------------------------------------------------------------")
        print ("--------------------- WARNING! SET A CORRECT NAME FOR DPC QUALITY -------------------------")
        print ("------------------------------- DEFAULTING TO HIGH QUALITY ----------------------------------")
        print ("---------------------------------------------------------------------------------------------")
        chunk.buildDepthMaps(quality=PS.HighQuality, filter=PS.MildFiltering, reuse_depth=True)

    chunk.buildDenseCloud(point_colors=True)

    # count number of points in dense cloud
    n_points_orig_DPC = chunk.dense_cloud.point_count

    return n_cams_enabled_DPC, n_points_final_SPC, n_points_orig_DPC, outside_BB

def export_settings(home, doc_title, outside_BB, n_points_final_SPC, n_points_orig_DPC, n_cams_enabled_DPC):
    print("exporting settings to temp_folder")

    opt_list = ["n_points_outside_BB","n_points_final_SPC", "n_points_orig_DPC", "n_cams_enabled_DPC"]
    params_list = [outside_BB, n_points_final_SPC, n_points_orig_DPC, n_cams_enabled_DPC]
    if os.path.exists(home + '/' + doc_title + '.files'):

        with open(home + '/' + doc_title + '.files/PhSc2_settings_TEMP.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(zip(opt_list, params_list))





    #############  MANUAL SCREENING OF DENSE POINT CLOUD NOW REQUIRED ##########################


if __name__ == '__main__':
    script_setup()
    print ("Total Time: " + str(datetime.now() - startTime))  # GET TOTAL TIME
