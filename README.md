# PhotoScan_Auto_Workflow
An automated workflow for processing drone imagery in PhotoScan

Simple workflow (will need updating):

1) set up correct settings and directories in the inputfile.csv (make sure the input file is in the same directory as the .py files.
2) run script 2 either in the GUI if working on a desktop or headless if running on an HPC.
3) evaluate sparse point cloud - clean unwanted points and check camera positions and alignment.
4) mark 10 instances of each ground control point.
5) de-select at least 1 (but ideally more) control points to be used as validation markers. SAVE! If this step isn't done then the next script will be killed to prevent run before time consuming dense cloud build.
6) Run Script 2. 
7) review and edit the dense cloud produced in script 2 - deleting erroneous points.
8) save and run script 3. 
review exported files, settings summary and PhotoScan report.
