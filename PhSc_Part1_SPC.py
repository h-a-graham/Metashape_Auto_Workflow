#######################################################################################################################
# ------ PhotoScan workflow Part 1: -----------------------------------------------------------------------------------
# ------ Image Quality analysis, Camera Alignment analysis, Reprojection Error Analysis, Sparse Point Cloud Creation --
# ------ and Reference settings ---------------------------------------------------------------------------------------
# ------ Written for PhotoScan 1.4.3 64 bit ---------------------------------------------------------------------------
#######################################################################################################################
# IMPORTS #
import PhotoScan as PS
import math
import os
import csv
import inspect
from datetime import datetime

PS.app.console.clear() # comment out when using ISCA

startTime = datetime.now()
print ("Script start time: " + str(startTime))

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

    marker_coords = var_list[5]
    marker_crs = var_list[6]

    Est_img_qual = var_list[8]

    img_qual_thresh = var_list[9]

    spc_quality = var_list[10]

    reproj_err_limit = var_list[32]

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

    doc.save(home+name)

    # Locate and add photos
    photos = os.listdir(datadir)  # Get the photos filenames
    photos = [os.path.join(datadir, p) for p in photos]  # convert to full paths

    chunk = PS.app.document.addChunk()  # create a chunk

    chunk.addPhotos([photos])  # add photos to chunk

    new_crs = PS.CoordinateSystem(coord_sys)  # define desired Coordinate System

    try:
        for camera in chunk.cameras:  # set the coordinates for cameras
            camera.reference.location = new_crs.project(chunk.crs.unproject(camera.reference.location))
    except Exception:
        print ("Images do not have projection data... No Worries! continue without!")

    # Optional import of markers if desired...
    if marker_coords == "NONE":  # if no markers are given then pass
        pass
    else:
        chunk.loadReference(marker_coords, columns="nxyzXYZ", delimiter=",", group_delimiters=False,  # if a path is given markers are added
                            skip_rows=1, ignore_labels=False, create_markers=True, threshold=0.1)

        if marker_crs == coord_sys:  # if marker and project crs match then pass otherwise convert marker crs
            pass
        else:
            for marker in chunk.markers:  # This needs testing  but should theoretically work...
                marker.reference.location = new_crs.project(chunk.crs.unproject(marker.reference.location))

    chunk.crs = new_crs  # set project coordinate system

    doc.save(home + name)

    orig_n_cams, n_filter_removed, perc_filter_removed, real_qual_thresh = preprocess(Est_img_qual, img_qual_thresh, chunk)

    doc.save(home + name)
    points, projections = build_SPC(chunk, spc_quality)

    total_points, perc_ab_thresh, nselected = filter_reproj_err(chunk, reproj_err_limit)

    n_not_aligned = ref_setting_setup(doc, points, projections, home, name)

    export_settings(orig_n_cams, n_filter_removed, perc_filter_removed, real_qual_thresh, n_not_aligned,
                    total_points, nselected, home, doc_title)

    # SAVE DOCUMENT
    doc.save(home + name)
    if perc_ab_thresh > 20:
        print ("-------------------------------------------------------------")
        print ("WARNING >20% OF POINTS ABOVE REPROJECTION ERROR THRESHOLD!!!!")
        print ("-------------------------------------------------------------")

        # Get Execution Time...
    print ("Total Time: " + str(datetime.now() - startTime))  # GET TOTAL TIME


def preprocess(Est_img_qual, img_qual_thresh, chunk):

    # Estimating Image Quality and excluding poor images
    if Est_img_qual == "TRUE":
        print ("running image quality filter...")
        chunk.estimateImageQuality()

        qual = float(img_qual_thresh)

        kept_img_quals = []
        dumped_img_quals = []

        for camera in chunk.cameras:
            IQ = float(camera.meta["Image/Quality"])
            if IQ < qual:
                camera.enabled = False
                dumped_img_quals.append(IQ)
            else:
                kept_img_quals.append(IQ)

        print ("number of cameras disabled = " + str(len(dumped_img_quals)))
        print ("percent of cameras disabled = " + str(round((len(dumped_img_quals)/(len(kept_img_quals)+len(dumped_img_quals))*100), 1)) + "%")
        print ("number of cameras enabled = " + str(len(kept_img_quals)))

        p09 = [i for i in kept_img_quals if i >= 0.9]
        p08 = [i for i in kept_img_quals if i >= 0.8]
        p07 = [i for i in kept_img_quals if i >= 0.7]
        p06 = [i for i in kept_img_quals if i >= 0.6]
        p05 = [i for i in kept_img_quals if i >= 0.5]

        print ("number of photos with image quality >= 0.9: " + str(len(p09)))
        print ("percent of cameras with image quality >= 0.9: " + str(round((len(p09)/(len(kept_img_quals)+len(dumped_img_quals))*100), 1)) + "%")

        print ("number of photos with image quality >= 0.8: " + str(len(p08)))
        print ("percent of cameras with image quality >= 0.8: " + str(round((len(p08)/(len(kept_img_quals)+len(dumped_img_quals))*100), 1)) + "%")

        print ("number of photos with image quality >= 0.7: " + str(len(p07)))
        print ("percent of cameras with image quality >= 0.7: " + str(round((len(p07)/(len(kept_img_quals)+len(dumped_img_quals))*100), 1)) + "%")

        print ("number of photos with image quality >= 0.6: " + str(len(p06)))
        print ("percent of cameras with image quality >= 0.6: " + str(round((len(p06)/(len(kept_img_quals)+len(dumped_img_quals))*100), 1)) + "%")

        print ("number of photos with image quality >= 0.5: " + str(len(p05)))
        print ("percent of cameras with image quality >= 0.5: " + str(round((len(p05)/(len(kept_img_quals)+len(dumped_img_quals))*100), 1)) + "%")

        orig_n_cams = len(dumped_img_quals) + len(kept_img_quals)
        n_filter_removed = len(dumped_img_quals)
        perc_filter_removed = round(((n_filter_removed/orig_n_cams)*100), 1)
        real_qual_thresh = min(kept_img_quals)
    else:
        print ("image quality filtering skipped...")
        chunk.estimateImageQuality()
        all_imgs_qual = []
        for camera in chunk.cameras:
            IQ = float(camera.meta["Image/Quality"])
            all_imgs_qual.append(IQ)

        orig_n_cams = len(chunk.cameras)
        n_filter_removed = "no_filter_applied"
        perc_filter_removed = "no_filter_applied"
        real_qual_thresh = min(all_imgs_qual)

    return orig_n_cams, n_filter_removed, perc_filter_removed, real_qual_thresh

def build_SPC(chunk, spc_quality):
    print ("building sparse point cloud...")
    # Match and Align Photos and Cameras
    if spc_quality == "LowestAccuracy":
        chunk.matchPhotos(accuracy=PS.LowestAccuracy, preselection=PS.GenericPreselection,
                          generic_preselection=True, reference_preselection=True, filter_mask=False, keypoint_limit=40000,
                          tiepoint_limit=8000)  # LowestAccuracy
    elif spc_quality == "LowAccuracy":
        chunk.matchPhotos(accuracy=PS.LowAccuracy, preselection=PS.GenericPreselection,
                          generic_preselection=True, reference_preselection=True, filter_mask=False, keypoint_limit=40000,
                          tiepoint_limit=8000)
    elif spc_quality == "MediumAccuracy":
        chunk.matchPhotos(accuracy=PS.MediumAccuracy, preselection=PS.GenericPreselection,
                          generic_preselection=True, reference_preselection=True, filter_mask=False, keypoint_limit=40000,
                          tiepoint_limit=8000)
    elif spc_quality == "HighAccuracy":
        chunk.matchPhotos(accuracy=PS.HighAccuracy, preselection=PS.GenericPreselection,
                          generic_preselection=True, reference_preselection=True, filter_mask=False, keypoint_limit=40000,
                          tiepoint_limit=8000)
    elif spc_quality == "HighestAccuracy":
        chunk.matchPhotos(accuracy=PS.HighestAccuracy, preselection=PS.GenericPreselection,
                          generic_preselection=True, reference_preselection=True, filter_mask=False, keypoint_limit=40000,
                          tiepoint_limit=8000)
    else:
        print ("---------------------------------------------------------------------------------------------")
        print ("--------------------- WARNING! SET THE CORRECT NAME FOR SPC ACCURACY ------------------------")
        print ("----------------------------- DEFAULTING TO HIGHEST ACCURACY --------------------------------")
        print ("---------------------------------------------------------------------------------------------")
        chunk.matchPhotos(accuracy=PS.HighestAccuracy, preselection=PS.GenericPreselection,
                          generic_preselection=True, reference_preselection=True, filter_mask=False,
                          keypoint_limit=40000,
                          tiepoint_limit=8000)

    chunk.alignCameras(adaptive_fitting=False)

    point_cloud = chunk.point_cloud
    points = point_cloud.points
    projections = chunk.point_cloud.projections

    return points, projections


def count_aligned(chunk): # GET NUMBER OF ALIGNED AND NON-ALIGNED CAMERAS
    aligned_list = list()
    for camera in chunk.cameras:
        if camera.transform:
            aligned_list.append(camera)

    not_aligned_list = list()
    for camera in chunk.cameras:
        if not camera.transform:
            not_aligned_list.append(camera)

    n_aligned = len(aligned_list)

    n_not_aligned = len(not_aligned_list)

    return (n_aligned, n_not_aligned)

def calc_reprojection_error(chunk, points, projections):

    npoints = len(points)

    photo_avg = []

    for camera in chunk.cameras:
        if not camera.transform:
            continue
        point_index = 0
        photo_num = 0
        photo_err = 0
        for proj in projections[camera]:
            track_id = proj.track_id
            while point_index < npoints and points[point_index].track_id < track_id:
                point_index += 1
            if point_index < npoints and points[point_index].track_id == track_id:
                if not points[point_index].valid:
                    continue

                dist = camera.error(points[point_index].coord, proj.coord).norm() ** 2  # get the square error for each point in camera

                photo_num += 1 # counts number of points per camera
                photo_err += dist # creates list of square point errors

        photo_avg.append(math.sqrt(photo_err / photo_num))  # get root mean square error for each camera

    return photo_avg  # returns list of rmse values for each camera

def ref_setting_setup(doc, points, projections,
                      home, name):

    #save first
    # doc.save(home + name)
    chunk = doc.chunk
    # get number of aligned cameras
    n_aligned, n_not_aligned = count_aligned(chunk)
    print ("number (%) of aligned cameras is:")
    print (str(n_aligned) + "(" + str(n_aligned/(n_aligned+n_not_aligned)*100)+ "%)")
    print ("number of cameras not aligned is:")
    print (str(n_not_aligned) + "(" + str(n_not_aligned/(n_aligned+n_not_aligned)*100)+ "%)")

    # Set up Reference Settings:
    cam_loc_acc = [20, 20, 50]    # xyz metres
    mark_loc_acc = [0.02, 0.02, 0.05]  # xyz metres
    mark_proj_acc = 2  # pixels
    chunk.camera_location_accuracy = cam_loc_acc  # units in m
    chunk.marker_location_accuracy = mark_loc_acc  # SINGLE VALUE USED WHEN MARKER-SPECIFIC ERRORS ARE UNAVAILABLE
    chunk.marker_projection_accuracy = mark_proj_acc  # FOR MANUALLY PLACED MARKERS

    total_error = calc_reprojection_error(chunk, points, projections) # calculate reprojection error

    reproj_error = sum(total_error)/len(total_error) # get average rmse for all cameras

    print ("mean reprojection error for point cloud:")
    print (round(reproj_error, 3))
    print ("max reprojection error is: " + str(max(total_error)))

    if reproj_error < 1:
        reproj_error = 1
    else:
        pass

    tiepoint_acc = (round(reproj_error, 2))
    chunk.tiepoint_accuracy = tiepoint_acc

    doc.save(home + name)

    return n_not_aligned

def filter_reproj_err (chunk, reproj_err_limit):
    # Filter points by their reprojection error and remove those with values > 0.45 (or the limit set in the input file)

    print ("filtering tiepoints by reprojection error (threshold = " + str(reproj_err_limit) + ")")
    Reproj_Err_Limit = float(reproj_err_limit)

    f = PS.PointCloud.Filter()
    f.init(chunk, PS.PointCloud.Filter.ReprojectionError)
    f.selectPoints(Reproj_Err_Limit)
    nselected = len([p for p in chunk.point_cloud.points if p.selected])
    total_points = len(chunk.point_cloud.points)
    perc_ab_thresh = round((nselected/total_points*100), 1)

    if perc_ab_thresh > 20:
        print ("---------------------------------------------------------")
        print ("WARNING >20% OF POINTS ABOVE REPROJECTION ERROR THRESHOLD")
        print ("---------------------------------------------------------")

    print("number of points below " + str(Reproj_Err_Limit) +
          " Reprojection Error Limit: " + str(nselected) + "/" +
          str(total_points) + "(" + str(perc_ab_thresh) +
          "%)")

    print ("Removing points above error threshold...")
    f.removePoints(Reproj_Err_Limit)

    return total_points, perc_ab_thresh, nselected


def export_settings(orig_n_cams, n_filter_removed, perc_filter_removed, real_qual_thresh, n_not_aligned,
                    total_points, nselected, home, doc_title):
    print("exporting settings to temp_folder")

    opt_list = ["n_cameras_loaded", "n_cams_removed_qual_filter", "%_cams_removed_qual_filter", "img_qual_min_val",
                "n_cameras_not_aligned", "n_points_orig_SPC", "n_points_removed_reproj_filter"]
    params_list = [orig_n_cams, n_filter_removed, perc_filter_removed, real_qual_thresh, n_not_aligned,
                   total_points, nselected]

    if os.path.exists(home + '/' + doc_title + '.files'):

        with open(home + '/' + doc_title + '.files/PhSc1_settings_TEMP.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(zip(opt_list, params_list))



if __name__ == '__main__':
    script_setup()

#######################################################################################################################
# Now it's time to do some manual cleaning as per the protocol:

