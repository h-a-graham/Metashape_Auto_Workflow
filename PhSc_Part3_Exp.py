#######################################################################################################################
# ------ PhotoScan workflow Part 3:  ----------------------------------------------------------------------------------
# ------ Export DPC, Build and Export: Textured Model, Othomosaic, DSM and PhotoScan Report ---------------------------
# ------ Written for PhotoScan 1.4.3 64 bit -------------------------------------------------------------------------
#######################################################################################################################

import PhotoScan as PS
import os
import csv
import inspect
from datetime import datetime

# Clear the Console screen
PS.app.console.clear()  # comment out when using ISCA

startTime = datetime.now()
print ("Script start time: " + str(startTime))

###################################################################################################

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
    #getting directories etc.
    home = var_list[1]
    doc_title = var_list[2]
    datadir = var_list[3]
    coord_sys = var_list[4]
    exportdir = var_list[7]

    # create export directory if it doesn't already exist
    if os.path.exists(exportdir):
        print ("export folder exists")
    else:
        print ("creating export folder...")
        os.makedirs(exportdir)

    #getting processing options
    e_DPC = var_list[12]
    b_mesh = var_list[13]
    mesh_qual = var_list[14]
    b_texture = var_list[15]
    b_ortho = var_list[16]
    b_dsm = var_list[17]
    e_model = var_list[18]
    e_ortho_lr = var_list[19]
    e_ortho_hr = var_list[22]
    e_dsm_lr = var_list[25]
    e_dsm_hr = var_list[28]
    e_report = var_list[31]

    # resolution params
    r_ortho_lr = var_list[20]
    r_ortho_hr = var_list[23]
    r_dsm_lr = var_list[26]
    r_dsm_hr = var_list[29]

    # big tiff options
    bt_ortho_lr = var_list[21]
    bt_ortho_hr = var_list[22]
    bt_dsm_lr = var_list[27]
    bt_dsm_hr = var_list[30]

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


    doc.open(home + name, read_only=False)
    chunk = doc.chunk

    dpc_npoints = chunk.dense_cloud.point_count

    export_DPC(chunk, doc_title, exportdir, e_DPC)

    build_mesh(chunk, doc, home, name, b_mesh, mesh_qual)

    build_texture(chunk, doc, home, name, b_texture, e_model, exportdir, doc_title)

    build_ortho(chunk, exportdir, doc, home, name, doc_title, b_ortho, e_ortho_lr, e_ortho_hr, r_ortho_lr, r_ortho_hr,
                bt_ortho_lr, bt_ortho_hr)

    build_dsm(chunk, exportdir, doc_title, doc, home, name, b_dsm, e_dsm_lr, e_dsm_hr, r_dsm_lr, r_dsm_hr,
              bt_dsm_lr, bt_dsm_hr)

    export_report(chunk, exportdir, doc_title, e_report)

    create_settings_summary(chunk, home, doc_title, exportdir, dpc_npoints)

    if os.path.isfile(home + "/" + doc_title + "_backup.psx"):
        print ("deleting backup")

    doc.save(home + name)


def export_DPC(chunk, doc_title, exportdir, e_DPC):  # export points
    if e_DPC == "TRUE":
        if chunk.dense_cloud is not None:
            print ("Exporting Dense Point Cloud")
            dpc_name = "/" + doc_title + "_dpc_export.laz" # other formats include pts but laz is Andy's fav
            chunk.exportPoints(exportdir + dpc_name, precision=3)
        else:
            print ("you need to build a dense point cloud")
    else:
        print ("Dense Point Cloud Export Not Selected")
        pass


def build_mesh(chunk, doc, home, name, b_mesh, mesh_qual):

    if b_mesh == "TRUE":
        print ("building mesh")

        if mesh_qual == "LowFaceCount":
            chunk.buildModel(surface=PS.HeightField, source=PS.DenseCloudData, interpolation= PS.EnabledInterpolation,
                             face_count=PS.LowFaceCount, vertex_colors=True)
        elif mesh_qual == "MediumFaceCount":
            chunk.buildModel(surface=PS.HeightField, source=PS.DenseCloudData, interpolation= PS.EnabledInterpolation,
                             face_count=PS.MediumFaceCount, vertex_colors=True)
        elif mesh_qual == "HighFaceCount":
            chunk.buildModel(surface=PS.HeightField, source=PS.DenseCloudData, interpolation= PS.EnabledInterpolation,
                             face_count=PS.HighFaceCount, vertex_colors=True)
        else:
            print ("---------------------------------------------------------------------------------------------")
            print ("--------------------- WARNING! SET THE CORRECT NAME FOR MESH QUALITY ------------------------")
            print ("------------------------------- DEFAULTING TO HIGH FACE COUNT -------------------------------")
            print ("---------------------------------------------------------------------------------------------")
            chunk.buildModel(surface=PS.HeightField, source=PS.DenseCloudData, interpolation=PS.EnabledInterpolation,
                             face_count=PS.HighFaceCount, vertex_colors=True)
        doc.save(home + name)  # save

    else:
        print("meshing build option not selected")


def build_texture(chunk, doc, home, name, b_texture, e_model, exportdir, doc_title):
    if b_texture == "TRUE":
        print ("building texture")
        chunk.buildUV(mapping=PS.GenericMapping)
        chunk.buildTexture(blending=PS.MosaicBlending, size=2048, fill_holes=True, ghosting_filter=True)

        doc.save(home + name)  # save

    else:
        print("texture build option not selected")

    if e_model == "TRUE":
        if chunk.model is not None:
            print ("exporting textured model")
            model_path = exportdir + "/" + doc_title + "_tex_model.ply"
            chunk.exportModel(model_path, binary=True, precision=3, texture_format=PS.ImageFormatJPEG, texture=True,
                        normals=False, colors=True, udim=False,
                        strip_extensions=False, raster_transform=PS.RasterTransformNone)

        else:
            print (" WARNING: must build mesh and texture before export")
    else:
        print ("textured model export not selected")


def build_ortho(chunk, exportdir, doc, home, name, doc_title, b_ortho, e_ortho_lr, e_ortho_hr, r_ortho_lr, r_ortho_hr,
                bt_ortho_lr, bt_ortho_hr):  # Currently no option to add "description metadata to exports add when available!!!
    if b_ortho == "TRUE":
        print ("building Orthomosaic")
        chunk.buildOrthomosaic(surface=PS.ModelData, blending=PS.MosaicBlending, fill_holes=True)
        doc.save(home + name)  # save
    else:
        print("build orthomosaic option not selected")

    o_mm_lr = int(round(float(r_ortho_lr) * 1000))
    o_mm_hr = int(round(float(r_ortho_hr) * 1000))

    if bt_ortho_lr == "TRUE":  # if low res ortho big tiff option true
        if e_ortho_lr == "TRUE":
            if chunk.orthomosaic is not None:
                print("exporting low resolution orthomosaic")
                ortho_res_lr = float(r_ortho_lr)  # set the desired resolution

                ortho_path_lr = exportdir + "/" + doc_title + "_Ortho_LR_"+ str(o_mm_lr) + "mm.tiff"
                chunk.exportOrthomosaic(ortho_path_lr, raster_transform=PS.RasterTransformNone, dx=ortho_res_lr,
                                        dy=ortho_res_lr, tiff_big=True, tiff_compression=PS.TiffCompressionNone,
                                        write_alpha=True)
            else:
                print ("must build Orthomosaic before export")
        else:
            print("low resolution Orthomosaic export option not selected")
    else:  # big tiff false here...
        if e_ortho_lr == "TRUE":
            if chunk.orthomosaic is not None:
                print("exporting low resolution orthomosaic")
                ortho_res_lr = float(r_ortho_lr)  # set the desired resolution

                ortho_path_lr = exportdir + "/" + doc_title + "_Ortho_LR_" + str(o_mm_lr) + "mm.tiff"
                chunk.exportOrthomosaic(ortho_path_lr, raster_transform=PS.RasterTransformNone, dx=ortho_res_lr,
                                        dy=ortho_res_lr, tiff_big=False, tiff_compression=PS.TiffCompressionNone,
                                        write_alpha=True)
            else:
                print ("must build Orthomosaic before export")
        else:
            print("low resolution Orthomosaic export option not selected")

    if bt_ortho_hr == "TRUE": # high res big tiff option true
        if e_ortho_hr == "TRUE":
            if chunk.orthomosaic is not None:
                print("exporting high resolution orthomosaic")

                ortho_res_hr = float(r_ortho_hr)  # set the desired resolution

                ortho_path_hr = exportdir + "/" + doc_title + "_Ortho_HR_" + str(o_mm_hr) + "mm.tiff"
                chunk.exportOrthomosaic(ortho_path_hr, raster_transform=PS.RasterTransformNone, dx=ortho_res_hr,
                                        dy=ortho_res_hr, tiff_big=True, tiff_compression=PS.TiffCompressionNone,
                                        write_alpha=True)
            else:
                print ("must build Orthomosaic before export")
        else:
            print("high resolution Orthomosaic export option not selected")

    else:  # big tiff option False
        if e_ortho_hr == "TRUE":
            if chunk.orthomosaic is not None:
                print("exporting high resolution orthomosaic")

                ortho_res_hr = float(r_ortho_hr)  # set the desired resolution

                ortho_path_hr = exportdir + "/" + doc_title + "_Ortho_HR_" + str(o_mm_hr) + "mm.tiff"
                chunk.exportOrthomosaic(ortho_path_hr, raster_transform=PS.RasterTransformNone, dx=ortho_res_hr,
                                        dy=ortho_res_hr, tiff_big=False, tiff_compression=PS.TiffCompressionNone,
                                        write_alpha=True)
            else:
                print ("must build Orthomosaic before export")
        else:
            print("high resolution Orthomosaic export option not selected")


def build_dsm(chunk, exportdir, doc_title, doc, home, name, b_dsm, e_dsm_lr, e_dsm_hr, r_dsm_lr, r_dsm_hr,
              bt_dsm_lr, bt_dsm_hr):
    # build DSMs
    if b_dsm == "TRUE":
        print ("building DSM...")
        chunk.buildDem(source=PS.DenseCloudData, interpolation=PS.EnabledInterpolation)
        doc.save(home + name)
    else:
        print (" build dsm option not selected")

    #export DSMs

    mm_lr = int(round(float(r_dsm_lr) * 1000))
    mm_hr = int(round(float(r_dsm_hr) * 1000))

    if bt_dsm_lr == "TRUE":
        if e_dsm_lr == "TRUE":
            if chunk.elevation is not None:
                print ("exporting low resolution DSM")
                dsm_res_lr = float(r_dsm_lr)
                dsm_path_lr = exportdir + "/" + doc_title + "_DSM_LR_" + str(mm_lr) +"mm.tiff"
                chunk.exportDem(dsm_path_lr, raster_transform=PS.RasterTransformNone, dx=dsm_res_lr,
                                dy=dsm_res_lr, tiff_big=True)
            else:
                print ("build DSM before trying to export")
        else:
            print("low resolution DSM export option not selected")
    else:
        if e_dsm_lr == "TRUE":
            if chunk.elevation is not None:
                print ("exporting low resolution DSM")
                dsm_res_lr = float(r_dsm_lr)
                dsm_path_lr = exportdir + "/" + doc_title + "_DSM_LR_" + str(mm_lr) +"mm.tiff"
                chunk.exportDem(dsm_path_lr, raster_transform=PS.RasterTransformNone, dx=dsm_res_lr, dy=dsm_res_lr,
                                tiff_big=False)
            else:
                print ("build DSM before trying to export")
        else:
            print("low resolution DSM export option not selected")
    if bt_dsm_hr == "TRUE":
        if e_dsm_hr == "TRUE":
            if chunk.elevation is not None:
                print ("exporting high resolution DSM")
                dsm_res_hr = float(r_dsm_hr)
                dsm_path_hr = exportdir + "/" + doc_title + "_DSM_HR_" + str(mm_hr) +"mm.tiff"
                chunk.exportDem(dsm_path_hr, raster_transform=PS.RasterTransformNone, dx=dsm_res_hr,
                                dy=dsm_res_hr, tiff_big=True)
            else:
                print ("build DSM before trying to export")
        else:
            print("high resolution DSM export option not selected")
    else:
        if e_dsm_hr == "TRUE":
            if chunk.elevation is not None:
                print ("exporting high resolution DSM")
                dsm_res_hr = float(r_dsm_hr)
                dsm_path_hr = exportdir + "/" + doc_title + "_DSM_HR_" + str(mm_hr) +"mm.tiff"
                chunk.exportDem(dsm_path_hr, raster_transform=PS.RasterTransformNone, dx=dsm_res_hr, dy=dsm_res_hr,
                                tiff_big=False)
            else:
                print ("build DSM before trying to export")
        else:
            print("high resolution DSM export option not selected")


def export_report(chunk, exportdir, doc_title, e_report):

    if e_report == "TRUE":
        print ("generating and exporting photoscan report")
        report_path = exportdir + "/" + doc_title + "_process_report.pdf"
        chunk.exportReport(path=report_path, description=doc_title)
    else:
        print ("export report option not selected")


def create_settings_summary(chunk, home, doc_title, exportdir, dpc_npoints):
    print ("producing final settings summary")

    # determine project reference settings
    ps_cam_locsa = (str(chunk.camera_location_accuracy))
    ps_cam_locs = ps_cam_locsa.replace("Vector", "")

    list_a = []
    for marker in chunk.markers:
        list_a.append(marker.reference.accuracy)

    if (list_a[1:] ==  list_a[:-1]) == True:
        ps_mark_locsa = (str(chunk.maker_location_accuracy))
        ps_mark_locs = ps_mark_locsa.replace("Vector", "")
    else:

        x_list = [item[0] for item in list_a]
        y_list = [item[1] for item in list_a]
        z_list = [item[2] for item in list_a]

        ps_mark_locs = str([[min(x_list), max(x_list)], [min(y_list), max(y_list)], [min(z_list), max(z_list)]])

    ps_markproj = chunk.marker_projection_accuracy
    ps_tp_acc = chunk.tiepoint_accuracy

    #import settings output files from script 1 and 2
    s1_out_sett = home + '/' + doc_title + '.files/PhSc1_settings_TEMP.csv'
    s2_out_sett = home + '/' + doc_title + '.files/PhSc2_settings_TEMP.csv'
    # if script1 settings file exists load in otherwise vars = NA
    if os.path.isfile(s1_out_sett) and os.path.isfile(s2_out_sett):
        print("settings files for scripts 1 and 2 present - creating settings file output...")
        sett_s1s = []

        with open(s1_out_sett, 'r') as f:
            mycsv = csv.reader(f)
            for row in mycsv:
                colB = row[1]
                sett_s1s.append(colB)

        sett_s2s = []

        with open(s2_out_sett, 'r') as f:
            mycsv = csv.reader(f)
            for row in mycsv:
                colB = row[1]
                sett_s2s.append(colB)

        sett_s1 = [float(i) for i in sett_s1s]
        sett_s2 = [float(i) for i in sett_s2s]

        # create variables:
        blank = ""  # line break for csv file

        n_cams_loaded = sett_s1[0]
        n_cams_rem_QF = sett_s1[1]
        perc_cams_rem_QF = round(sett_s1[2], 3)
        min_qual_val = round(sett_s1[3], 3)
        n_cams_not_align = sett_s1[4] - sett_s1[1]
        perc_cams_not_align = round(((sett_s1[4] - sett_s1[1])/sett_s1[0])*100, 3)
        n_cams_man_disab = sett_s1[0] - sett_s1[1] - sett_s2[3] - (sett_s1[4] - sett_s1[1])
        perc_cams_man_disab = round(((sett_s1[0] - sett_s1[1] - sett_s2[3] - (sett_s1[4] - sett_s1[1]))/sett_s1[0])*100, 3)
        n_cams_enabled = sett_s2[3]
        perc_cams_enabled = round((sett_s2[3]/sett_s1[0])*100, 3)


        n_pnts_orig_spc = sett_s1[5]
        n_pnts_rem_REF = sett_s1[6]
        perc_pnts_rem_REF = round((sett_s1[6]/sett_s1[5]) * 100, 3)
        n_pnts_rem_manual = (sett_s1[5] - sett_s1[6]) - (sett_s2[1] + sett_s2[0])
        perc_pnts_rem_manual = round((((sett_s1[5] - sett_s1[6]) - (sett_s2[1] + sett_s2[0]))/sett_s1[5]) * 100, 3)
        n_pnts_rem_BB = sett_s2[0]
        perc_pnts_rem_BB = round((sett_s2[0]/sett_s1[5]) * 100, 3)
        n_pnts_SPC_final = sett_s2[1]

        n_pnts_orig_DPC = sett_s2[2]
        n_pnts_man_rem_DPC = sett_s2[2] - dpc_npoints
        perc_pnts_man_rem_DPC = round(((sett_s2[2] - dpc_npoints)/sett_s2[2]) * 100, 4)
        n_pnts_final_DPC = dpc_npoints

        # create and export final settings csv
        opt_list = ["camera_location_accuracy_(m)", "marker_location_accuracy_(m)", "marker_projection_accuracy_(pix)",
                    "tiepoint_accuracy_(pix)", "",
                    "n cameras loaded", "n cameras removed by Quality filter", "% cameras removed by Quality filter",
                    "minimum image quality", "n enabled cameras not aligned", "% enabled cameras not aligned",
                    "n cameras manually disabled", "% cameras manually disabled", "n cameras enabled",
                    "% cameras enabled", "",
                    "n points in original SPC", "n SPC points removed in reproj. err. filter",
                    "% SPC points removed in reproj. err. filter", "n SPC points removed manually",
                    "% SPC points removed manually", "n points removed by Bounding Box",
                    "% points removed by Bounding Box", "n points in final SPC", "",
                    "n points in original DPC", "n points removed manually DPC", "% points removed manually DPC",
                    "n points final DPC"]
        params_list = [ps_cam_locs, ps_mark_locs, ps_markproj, ps_tp_acc, blank,
                       n_cams_loaded, n_cams_rem_QF, perc_cams_rem_QF,
                       min_qual_val, n_cams_not_align, perc_cams_not_align, n_cams_man_disab, perc_cams_man_disab,
                       n_cams_enabled, perc_cams_enabled, blank,
                       n_pnts_orig_spc, n_pnts_rem_REF, perc_pnts_rem_REF, n_pnts_rem_manual, perc_pnts_rem_manual,
                       n_pnts_rem_BB, perc_pnts_rem_BB, n_pnts_SPC_final, blank,
                       n_pnts_orig_DPC, n_pnts_man_rem_DPC, perc_pnts_man_rem_DPC, n_pnts_final_DPC]

        with open(exportdir + "/" + doc_title + "_project_settings.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(zip(opt_list, params_list))

    else:
        print("script 1 settings and/or script2 settings do not exist")
        print("producing reference settings file only")
        opt_list = ["camera_location_accuracy_(m)", "marker_location_accuracy_(m)", "marker_projection_accuracy_(pix)",
                    "tiepoint_accuracy_(pix)"]
        params_list = [ps_cam_locs, ps_mark_locs, ps_markproj, ps_tp_acc]

        with open(exportdir + "/" + doc_title + "_reference_settings.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(zip(opt_list, params_list))



if __name__ == '__main__':
    script_setup()
    print ("Total Time: " + str(datetime.now() - startTime))  # GET TOTAL TIME