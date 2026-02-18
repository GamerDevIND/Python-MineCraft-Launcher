import requests
import json
import os
import hashlib
import zipfile
from configs import DOWNLOAD_DIR, DESIRED_VERSION, OS_TYPE, arch_suffix, VERSION_DIR, FABRIC_PREFIX

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
FABRIC_META = "https://meta.fabricmc.net/v2/versions/loader"

def read_profile_json():

    profile_path = os.path.join(DOWNLOAD_DIR, 'launcher_profiles.json')

    if os.path.exists(profile_path):

        with open(profile_path, 'r') as f:
            return json.load(f)
        
    return None

def get_version_manifest():
    try:
        response = requests.get(MANIFEST_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching manifest: {e}")
        return None

def download_version_data(version_id, version_manifest):
    if version_id.startswith(FABRIC_PREFIX):
        parts = version_id.split('-')
        if len(parts) >= 3:
            minecraft_version = '-'.join(parts[2:])
            print(f"Detected fabric-loader version for Minecraft {minecraft_version}")
            
            for version in version_manifest['versions']:
                if version['id'] == minecraft_version:
                    version_url = version['url']
                    print(f"Downloading base Minecraft data for {minecraft_version} from {version_url}")
                    
                    response = requests.get(version_url)
                    response.raise_for_status()
                    base_version_data = response.json()
                    
                    fabric_version_data = {
                        "inheritsFrom": minecraft_version,
                        "id": version_id,
                        "type": "release",
                        "mainClass": "net.fabricmc.loader.impl.launch.knot.KnotClient",
                        "libraries": [
                            {
                                "name": f"net.fabricmc:fabric-loader:{get_latest_fabric_loader(DESIRED_VERSION)}",
                                "url": "https://maven.fabricmc.net/"
                            }
                        ],
                        "downloads": base_version_data.get('downloads', {}),
                        "arguments": base_version_data.get('arguments', {}),
                        "assetIndex": base_version_data.get('assetIndex', {}),
                        "releaseTime": base_version_data.get('releaseTime', ''),
                        "time": base_version_data.get('time', '')
                    }
                    
                    file_path = os.path.join(VERSION_DIR, f"{version_id}.json")
                    with open(file_path, 'w') as f:
                        json.dump(fabric_version_data, f, indent=4)
                    
                    print(f"Created fabric-loader version data at {file_path}")
                    return fabric_version_data, file_path
    
    for version in version_manifest['versions']:
        if version['id'] == version_id:
            version_url = version['url']
            print(f"Downloading data for version {version_id} from {version_url}")
            
            response = requests.get(version_url)
            response.raise_for_status()
            version_data = response.json()

            file_path = os.path.join(VERSION_DIR, f"{version_id}.json")
            with open(file_path, 'w') as f:
                json.dump(version_data, f, indent=4)
            
            print(f"Saved version data to {file_path}")
            return version_data, file_path
    
    print(f"Version {version_id} not found.")
    return None, None

def get_latest_fabric_loader(mc_version):
    try:
        resp = requests.get(f"{FABRIC_META}/{mc_version}")
        data = resp.json()
        for entry in data:
            if entry.get("stable", False):
                return entry["version"] 
        return data[0]["version"] 
    except:
        return "0.16.5"

def download_and_verify(url, expected_hash, download_path, name):
    if os.path.exists(download_path) and expected_hash:
        try:
            hasher = hashlib.sha1()
            with open(download_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            
            if hasher.hexdigest().lower() == expected_hash.lower():
                print(f"Skipping {name}: already exists and verified.")
                return True
        except Exception:
            pass

    try:
        print(f'Downloading {name} from {url}')
        response = requests.get(url, stream=True)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {name}: {e}")
        return False

    os.makedirs(os.path.dirname(download_path), exist_ok=True)

    try:
        hasher = hashlib.sha1()
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=(1024 * 8)):
                f.write(chunk)
                if expected_hash:
                    hasher.update(chunk)

        if expected_hash:
            hashed = hasher.hexdigest()
            if expected_hash.lower() == hashed.lower():
                print(f'Hashing success for {name}.')
                return True
            else:
                print(f'Hashing FAILED for {name}. Expected: {expected_hash}, Got: {hashed}')
                if os.path.exists(download_path):
                    os.remove(download_path)
                return False
        else:
            print(f'No hash to verify for {name}. File saved.')
            return True
            
    except IOError as e:
        print(f"Error writing file {download_path}: {e}")
        return False

def should_download(lib_entry):
    rules = lib_entry.get('rules')
    if not rules:
        return True

    allow = False
    for rule in rules:
        action = rule.get('action') 
        os_rule = rule.get('os', {})
        os_name = os_rule.get('name')

        target_os = 'osx' if OS_TYPE == 'macos' else OS_TYPE

        if os_name is None:
            allow = (action == 'allow')
        elif os_name == target_os:
            allow = (action == 'allow')
            
    return allow

def download_files(full_data):
    download_data = full_data['downloads']
    if DESIRED_VERSION.startswith(FABRIC_PREFIX):
        print("Downloading fabric-loader version...")
        
        fabric_loader_url = f"https://maven.fabricmc.net/net/fabricmc/fabric-loader/{get_latest_fabric_loader(DESIRED_VERSION)}/fabric-loader-{get_latest_fabric_loader(DESIRED_VERSION)}.jar"
        fabric_loader_path = os.path.join(VERSION_DIR, 'client', 'JAR', f'fabric-loader-{get_latest_fabric_loader(DESIRED_VERSION)}.jar')
        download_and_verify(fabric_loader_url, None, fabric_loader_path, 'Fabric Loader')
        
        base_version = full_data.get('inheritsFrom')
        if base_version:
            base_manifest = get_version_manifest()
            base_data, _ = download_version_data(base_version, base_manifest)
            if base_data:
                download_data = base_data['downloads']
                client_jar_url = download_data['client']['url']
                client_jar_hash = download_data['client']['sha1']
                client_jar_path = os.path.join(VERSION_DIR, 'client', 'JAR', f'{base_version}.jar')
                download_and_verify(client_jar_url, client_jar_hash, client_jar_path, f'Base Minecraft {base_version} JAR')
        
        libs = full_data['libraries']
        lib_base = os.path.join(VERSION_DIR, 'client', 'JAR', 'libraries')

        for i, lib in enumerate(libs, 1):
            if not should_download(lib):
                continue 

            downloads = lib.get('downloads', {})

            artifact = downloads.get('artifact')
            if artifact:
                save_path = os.path.join(lib_base, artifact['path'])
                download_and_verify(artifact['url'], artifact['sha1'], save_path, f"Lib {i} / {len(libs)}")

            classifiers = downloads.get('classifiers', {})
            native_key = f"natives-{OS_TYPE}{arch_suffix}"

            if OS_TYPE == 'macos' and f"natives-osx{arch_suffix}" in classifiers:
                native_key = f"natives-osx{arch_suffix}"

            if native_key in classifiers:
                native = classifiers[native_key]
                save_path = os.path.join(lib_base, native['path'])
                download_and_verify(native['url'], native['sha1'], save_path, f"Native {i} / {len(classifiers)}")
    else:
        download_data = full_data['downloads']
        
        client_jar_url = download_data['client']['url']
        client_jar_hash = download_data['client']['sha1']
        client_jar_path = os.path.join(VERSION_DIR, 'client', 'JAR', f'{DESIRED_VERSION}.jar')
        download_and_verify(client_jar_url, client_jar_hash, client_jar_path, 'Client JAR')

        print('main JAR download, downloading libraries...')
        libs = full_data['libraries']
        lib_base = os.path.join(VERSION_DIR, 'client', 'JAR', 'libraries')

        for i, lib in enumerate(libs, 1):
            if not should_download(lib):
                continue 

            downloads = lib.get('downloads', {})

            artifact = downloads.get('artifact')
            if artifact:
                save_path = os.path.join(lib_base, artifact['path'])
                download_and_verify(artifact['url'], artifact['sha1'], save_path, f"Lib {i} / {len(libs)}")

            classifiers = downloads.get('classifiers', {})
            native_key = f"natives-{OS_TYPE}{arch_suffix}"

            if OS_TYPE == 'macos' and f"natives-osx{arch_suffix}" in classifiers:
                native_key = f"natives-osx{arch_suffix}"

            if native_key in classifiers:
                native = classifiers[native_key]
                save_path = os.path.join(lib_base, native['path'])
    
def download_assets(full_data):
    if DESIRED_VERSION.startswith(FABRIC_PREFIX):
        base_version = full_data.get('inheritsFrom')
        if base_version:
            base_manifest = get_version_manifest()
            base_data, _ = download_version_data(base_version, base_manifest)
            if base_data:
                asset_info = base_data['assetIndex']
                asset_id = asset_info['id']
                index_path = os.path.join(VERSION_DIR, 'assets', 'indexes', f"{asset_id}.json")
                
                if download_and_verify(asset_info['url'], asset_info['sha1'], index_path, f'Asset Index: {asset_id}'):
                    with open(index_path, 'r') as f:
                        index_data = json.load(f)

                    assets_base_url = "https://resources.download.minecraft.net/"
                    objects_dir = os.path.join(VERSION_DIR, 'assets', 'objects')
                    
                    objects = index_data['objects']
                    total_assets = len(objects)
                    print(f"Found {total_assets} assets. Checking files...")
                    
                    for i, (name, obj) in enumerate(objects.items(), 1):
                        hash_val = obj['hash']
                        url = f"{assets_base_url}{hash_val[:2]}/{hash_val}"
                        save_path = os.path.join(objects_dir, hash_val[:2], hash_val)
                        download_and_verify(url, hash_val, save_path, f'Asset Object: {i} / {total_assets}')
    else:
        asset_info = full_data['assetIndex']
        asset_id = asset_info['id']
        index_path = os.path.join(VERSION_DIR, 'assets', 'indexes', f"{asset_id}.json")
        
        if download_and_verify(asset_info['url'], asset_info['sha1'], index_path, f'Asset Index: {asset_id}'):
            with open(index_path, 'r') as f:
                index_data = json.load(f)

            assets_base_url = "https://resources.download.minecraft.net/"
            objects_dir = os.path.join(VERSION_DIR, 'assets', 'objects')
            
            objects = index_data['objects']
            total_assets = len(objects)
            print(f"Found {total_assets} assets. Checking files...")
            
            for i, (name, obj) in enumerate(objects.items(), 1):
                hash_val = obj['hash']
                url = f"{assets_base_url}{hash_val[:2]}/{hash_val}"
                save_path = os.path.join(objects_dir, hash_val[:2], hash_val)
                download_and_verify(url, hash_val, save_path, f'Asset Object: {i} / {total_assets}')

def is_fabric_version(version_id):
    return version_id.startswith(FABRIC_PREFIX)

def parse_fabric_version(version_id):
    if not is_fabric_version(version_id):
        return None, None
    parts = version_id[len(FABRIC_PREFIX):].split('-', 1)
    if len(parts) != 2:
        return None, None
    loader_ver, mc_ver = parts
    return loader_ver, mc_ver

def extract_natives(full_data):
    print("Extracting native binaries...")
    natives_path = os.path.join(VERSION_DIR, 'client', 'natives')
    lib_base = os.path.join(VERSION_DIR, 'client', 'JAR', 'libraries')
    os.makedirs(natives_path, exist_ok=True)

    if DESIRED_VERSION.startswith(FABRIC_PREFIX):
        base_version = full_data.get('inheritsFrom')
        if base_version:
            base_manifest = get_version_manifest()
            base_data, _ = download_version_data(base_version, base_manifest)
            if base_data:
                for lib in base_data['libraries']:
                    if not should_download(lib):
                        continue

                    classifiers = lib.get('downloads', {}).get('classifiers', {})
                    native_key = f"natives-{OS_TYPE}{arch_suffix}"
                    if OS_TYPE == 'macos' and f"natives-osx{arch_suffix}" in classifiers:
                        native_key = f"natives-osx{arch_suffix}"

                    if native_key in classifiers:
                        jar_path = os.path.join(lib_base, classifiers[native_key]['path'])
                        if os.path.exists(jar_path):
                            with zipfile.ZipFile(jar_path, 'r') as zf:
                                for member in zf.namelist():
                                    if not member.startswith('META-INF/'):
                                        zf.extract(member, natives_path)
    else:
        for lib in full_data['libraries']:
            if not should_download(lib):
                continue

            classifiers = lib.get('downloads', {}).get('classifiers', {})
            native_key = f"natives-{OS_TYPE}{arch_suffix}"
            if OS_TYPE == 'macos' and f"natives-osx{arch_suffix}" in classifiers:
                native_key = f"natives-osx{arch_suffix}"

            if native_key in classifiers:
                jar_path = os.path.join(lib_base, classifiers[native_key]['path'])
                if os.path.exists(jar_path):
                    with zipfile.ZipFile(jar_path, 'r') as zf:
                        for member in zf.namelist():
                            if not member.startswith('META-INF/'):
                                zf.extract(member, natives_path)

if __name__ == '__main__':
    manifest = get_version_manifest()
    if not manifest:
        print("❌ Error: Could not fetch version manifest.")
        exit(1)

    profiles_data = read_profile_json()
    version_exists_in_profiles = False

    if profiles_data:
        profiles = profiles_data.get("profiles", {})
        for profile_id, profile_info in profiles.items():
            if profile_info.get("lastVersionId") == DESIRED_VERSION:
                version_exists_in_profiles = True
                break
    
    if DESIRED_VERSION.startswith(FABRIC_PREFIX):
        base_version = DESIRED_VERSION.split('-')[-1]
        client_jar_path = os.path.join(VERSION_DIR, 'client', 'JAR', f'{base_version}.jar')
        fabric_loader_path = os.path.join(VERSION_DIR, 'client', 'JAR', f'fabric-loader{get_latest_fabric_loader(DESIRED_VERSION)}.jar')
        metadata_exists = os.path.exists(os.path.join(VERSION_DIR, f"{DESIRED_VERSION}.json"))
        has_files = os.path.exists(client_jar_path) and os.path.exists(fabric_loader_path)
    else:
        client_jar_path = os.path.join(VERSION_DIR, 'client', 'JAR', f'{DESIRED_VERSION}.jar')
        metadata_exists = os.path.exists(os.path.join(VERSION_DIR, f"{DESIRED_VERSION}.json"))
        has_files = os.path.exists(client_jar_path)

    if not (version_exists_in_profiles and has_files and metadata_exists):
        print(f"📥 Version {DESIRED_VERSION} not found or incomplete. Starting download...")
        
        version_data, json_path = download_version_data(DESIRED_VERSION, manifest)
        
        if version_data:
            download_files(version_data)
            download_assets(version_data)
            extract_natives(version_data)
            print(f"\n✅ Minecraft {DESIRED_VERSION} successfully installed!")
        else:
            print(f"❌ Error: Could not retrieve data for version {DESIRED_VERSION}")
    else:
        print(f"✅ Version {DESIRED_VERSION} is already present in your profiles. Skipping download.")