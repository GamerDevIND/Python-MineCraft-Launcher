from configs import USERNAME, DOWNLOAD_DIR, MAX_RAM_GB, MIN_RAM_GB, DESIRED_VERSION
import json 
from downloader import version_data, json_path
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

    client_path = os.path.join(DOWNLOAD_DIR, 'client', 'JAR', 'client.jar')
    
    classpath = os.pathsep.join(libs + [client_path])
    return classpath

def create_profile_json(username, version_id):
    profile_data = {
        "profiles": {
            "CustomProfile": {
                "name": f"Vanilla - {version_id}",
                "gameDir": os.path.abspath(DOWNLOAD_DIR),
                "lastVersionId": version_id,
                "javaArgs": f"-Xmx{MAX_RAM_GB}G -Xms{MIN_RAM_GB}G",
                "type": "custom"   
            }
        },
        "selectedProfile": "CustomProfile",
        "clientToken": str(uuid.uuid4()),
        "authenticationDatabase": {}
    }

    profile_path = os.path.join(DOWNLOAD_DIR, 'launcher_profiles.json')
    with open(profile_path, 'w') as f:
        json.dump(profile_data, f, indent=4)
    print(f"Profile JSON created at: {profile_path}")


if version_data and json_path: 
    with open(json_path, 'r') as f: 
        json_file = json.load(f) 
        
    classpath = build_class_path() 
    main_class = json_file['mainClass'] 
    asset_index = json_file['assetIndex']['id']
    natives_dir = os.path.join(DOWNLOAD_DIR, 'client', 'natives') 
    uuid_offline = str(uuid.uuid4()) 
    ram_args = f'-Xmx{MAX_RAM_GB}G -Xms{MIN_RAM_GB}G'

    create_profile_json(USERNAME, DESIRED_VERSION)

    launch_command = ( 
        f'java {ram_args} '
        f'-Djava.library.path="{natives_dir}" ' 
        f'-cp "{classpath}" ' 
        f'{main_class} ' 
        f'--version {DESIRED_VERSION} ' 
        f'--gameDir "{DOWNLOAD_DIR}" ' 
        f'--assetsDir "{DOWNLOAD_DIR}/assets" ' 
        f'--assetIndex {asset_index} ' 
        f'--uuid {uuid_offline} ' 
        f'--accessToken 0 ' 
        f'--userType legacy ' 
        f'--versionType release ' 
        f'--username {USERNAME} ' 
        f'--launchTarget {main_class}' 
    ) 
    
    with open('launcher.log', 'w') as log_file: 
        print('log file opened')
        print('Launching client...')
        try:
            subprocess.run(launch_command, stderr=subprocess.STDOUT, stdout=log_file, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Game crashed or failed to start. Check launcher.log for details.")
else:
    print("❌ Error: Missing version data or JSON path. Run downloader first.")