import json 
import uuid 
import subprocess 
import os 
from configs import USERNAME, DOWNLOAD_DIR, MAX_RAM_GB, MIN_RAM_GB, DESIRED_VERSION, GAME_DIR, VERSION_DIR

json_path = os.path.join(VERSION_DIR, f"{DESIRED_VERSION}.json")
client_jar = os.path.join(VERSION_DIR, 'client', 'JAR', f'{DESIRED_VERSION}.jar')
natives_dir = os.path.join(VERSION_DIR, 'client', 'natives')

if not os.path.exists(json_path):
    print(f"❌ Error: Metadata for {DESIRED_VERSION} not found at {json_path}")
    exit(1)

with open(json_path, 'r') as f:
    version_data = json.load(f)

def build_class_path(json_file):
    lib_base = os.path.join(VERSION_DIR, 'client', 'JAR', 'libraries')
    libs_to_load = []

    for lib in json_file['libraries']:
        if 'downloads' in lib and 'artifact' in lib['downloads']:
            lib_path = os.path.join(lib_base, lib['downloads']['artifact']['path'])
            if os.path.exists(lib_path):
                libs_to_load.append(lib_path)
    
    return os.pathsep.join(libs_to_load + [client_jar])

def read_profile_json():

    profile_path = os.path.join(DOWNLOAD_DIR, 'launcher_profiles.json')

    if os.path.exists(profile_path):

        with open(profile_path, 'r') as f:
            return json.load(f)
        
    return None

def create_profile_json(version_id):
    existing_data = read_profile_json()
    profile_key = f"Profile-{version_id}"
    
    profile_content = {
        "name": f"Vanilla - {version_id}",
        "gameDir": os.path.abspath(os.path.join(GAME_DIR)),
        "lastVersionId": version_id,
        "javaArgs": f"-Xmx{MAX_RAM_GB}G -Xms{MIN_RAM_GB}G",
        "type": "custom",
        "created": str(uuid.uuid4())[:8]
    }

    if existing_data:
        if existing_data.get("profiles", {}).get(profile_key) == profile_content:
            return
        data_to_save = existing_data
    else:
        data_to_save = {
            "profiles": {},
            "selectedProfile": "",
            "clientToken": str(uuid.uuid4()),
            "authenticationDatabase": {}
        }

    data_to_save["profiles"][profile_key] = profile_content
    data_to_save["selectedProfile"] = profile_key

    profile_path = os.path.join(DOWNLOAD_DIR, 'launcher_profiles.json')
    with open(profile_path, 'w') as f:
        json.dump(data_to_save, f, indent=4)
    print(f"✅ Profile for {version_id} updated in: {profile_path}")

if version_data: 
    classpath = build_class_path(version_data) 
    main_class = version_data['mainClass'] 
    asset_index = version_data['assetIndex']['id']
    uuid_offline = str(uuid.uuid4()) 

    create_profile_json(DESIRED_VERSION)
    cmd = [
    "java",
    f"-Xmx{MAX_RAM_GB}G",
    f"-Xms{MIN_RAM_GB}G",
    f"-Djava.library.path={os.path.join(VERSION_DIR, 'client', 'natives')}",
    "-cp", classpath,
    main_class,
    "--version", DESIRED_VERSION,
    "--gameDir", os.path.abspath(GAME_DIR),
    "--assetsDir", os.path.abspath(os.path.join(VERSION_DIR, "assets")),
    "--assetIndex", asset_index,
    "--uuid", uuid_offline,
    "--accessToken", "0",
    "--userType", "legacy",
    "--versionType", "release",
    "--username", USERNAME
]


    with open('launcher.log', 'w') as log_file: 
        print('Log file opened at launcher.log')
        try:
            print(f"Launching Minecraft {DESIRED_VERSION}...")
            subprocess.run(cmd, stderr=subprocess.STDOUT, stdout=log_file, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Game crashed. Check launcher.log for details.")