Columbia Bar Channel Analysis Project Readme and Instructions

Contents:
Python Module Scripts:
1. download_new_surveys_v4.py
2. preprocess_surveys_v2.py
3. analyze_surveys_v13.py
4. generate_report_v5.py

ArcGIS Pro Project file:
Columbia_Bar_Analysis.aprx

Python Workflow Execution Script:
Columbia_Bar_Channel_Analysis_v4.py

Windows Batch Script for Task Automating the Analysis:
Run_Columbia_Bar_Channel_Analysis.bat

Documentation:
Columbia_Bar_Channel_Analysis_Implementation_v4.pdf
Columbia_Bar_Channel_Analysis_Scripts_Descriptions_v4.pdf


How to Run:
1. In the batch file (Run_Columbia_Bar_Channel_Analysis.bat) set the location of this project directory for the CD line.
1.a. i.e. "cd C:\Users\gao42\PSU\GEOG485\Columbia_Bar_Project\Columbia_Bar_Channel_Analysis_Project_gao42"
1.b. Execution will fail if this path is incorect.
2. Set the location and name of the your cloned ArcGis python environment python.exe.
2.a. i.e. "C:\Users\gao42\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone-gao42\python.exe" .\Columbia_Bar_Channel_Analysis_v4.py
2.b. Execution will fail if this path is incorect.  
3. Verifiy the running computer has ArcGIS Pro installed and is connected to the Internet (needed to download survey data).
4. Run the batch script Run_Columbia_Bar_Channel_Analysis.bat and allow time for the script to execute the workflow (download, preprocess, analysis and report generation).
4.a. There can be up to 20 sec before any activity is seen.
4.b. I can take up to 5 min to complete the downloads to report generation.
5. The final three reports will be stored in the relative "analysis_reports" directory.

If there are issues downloading the survey data from the Internet:
1. Download the project work flow that has already been run at: https://pennstateoffice365-my.sharepoint.com/:u:/g/personal/gao42_psu_edu/IQBJFl0hMLgRQIKWUGdzb607AW5pHJLb3EXpUOIlCjVwOds?e=gQN3Bb
2. Copy the "downloaded _surveys" directory in this Columbia_Bar_Channel_Analysis_Project_gao42 directory.
3. Comment out "downloaded = check_and_download_surveys(...)" in the python workflow script Columbia_Bar_Channel_Analysis_v4.py and rerun the analysis.