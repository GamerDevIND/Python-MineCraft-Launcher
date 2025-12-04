from configs import USERNAME, DOWNLOAD_DIR, MAX_RAM_GB, MIN_RAM_GB
import json 
from downloader import version_data, json_path, release_version, latest_release
import uuid 
import subprocess 
import os 
def build_class_path():
    base_lib_dir = os.path.join(DOWNLOAD_DIR, 'client', 'JAR', 'libraries')
    libs = []
    for root, _, files in os.walk(base_lib_dir):
        for file in files:
            if file.endswith('.jar'):
                libs.append(os.path.join(root, file))

    client_path = os.path.join(DOWNLOAD_DIR,'client', 'JAR', 'client.jar')

    classpath = os.pathsep.join(libs + [client_path])
    return classpath

RAM_ARGS = f'-Xmx{MAX_RAM_GB}G -Xms{MIN_RAM_GB}G'   

if version_data and json_path: 
    with open(file=json_path) as f: 
        json_file = json.load(f) 
        classpath = build_class_path() 
        main_class = json_file['mainClass'] 
        asset_index = json_file['assetIndex']['id']
        NATIVES_DIR = os.path.join(DOWNLOAD_DIR, 'client', 'natives') 
        main_class = json_file['mainClass'] 
        uuid_offline = str(uuid.uuid4()) 
        asset_index = json_file['assetIndex']['id'] 
        version_id = latest_release
        print('Success. Launching') 
        launch_command = ( 
            f'java {RAM_ARGS} '
	    f'-Djava.library.path="{NATIVES_DIR}" ' 
            f'-cp "{classpath}" ' f'{main_class} ' f'--version {version_id} ' 
            f'--gameDir "{DOWNLOAD_DIR}" ' f'--assetsDir "{DOWNLOAD_DIR}/assets" ' 
            f'--assetIndex {asset_index} ' f'--uuid {uuid_offline} ' f'--accessToken 0 ' 
            f'--userType legacy ' f'--versionType release ' f'--username {USERNAME} ' 
            f'--launchTarget {main_class}' 
	) 
        
        with open('launcher.log' ,'w') as f: 
            print("log file opened")
            subprocess.run(launch_command, stderr=subprocess.STDOUT, stdout=f, check=True)