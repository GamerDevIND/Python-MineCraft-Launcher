import requests
import json
import os
import hashlib
import zipfile
from configs import DOWNLOAD_DIR, DESIRED_VERSION, OS_TYPE

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_version_manifest():
    try:
        response = requests.get(MANIFEST_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching manifest: {e}")
        return None

def download_version_data(version_id, version_manifest):
    for version in version_manifest['versions']:
        if version['id'] == version_id:
            version_url = version['url']
            print(f"Downloading data for version {version_id} from {version_url}")
            
            response = requests.get(version_url)
            response.raise_for_status()
            version_data = response.json()

            file_path = os.path.join(DOWNLOAD_DIR, f"{version_id}.json")
            with open(file_path, 'w') as f:
                json.dump(version_data, f, indent=4)
            
            print(f"Saved version data to {file_path}")
            return version_data, file_path
    
    print(f"Version {version_id} not found.")
    return None, None

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

    hasher = hashlib.sha1()
    try:
        print(f'Downloading {name} from {url}')
        response = requests.get(url, stream=True)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {name}: {e}")
        return False

    os.makedirs(os.path.dirname(download_path), exist_ok=True)

    try:
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

def download_files(full_data, only_client=True, only_server=False, download_mappings=False):
    success = True
    download_data = full_data['downloads']
    if only_client or (not only_client and not only_server):
        url_jar = download_data['client']['url']
        hash_jar = download_data['client']['sha1']
        path_jar = os.path.join(DOWNLOAD_DIR,'client', 'JAR', 'client.jar')
        if not download_and_verify(url_jar, hash_jar, path_jar, 'Client JAR'):
            success = False

        if download_mappings and 'client_mappings' in download_data:
            url_map = download_data['client_mappings']['url']
            hash_map = download_data['client_mappings']['sha1']
            path_map = os.path.join(DOWNLOAD_DIR, 'client', 'mappings', 'client.txt')
            if not download_and_verify(url_map, hash_map, path_map, 'Client Mappings'):
                success = False

    if only_server or (not only_client and not only_server):
        if not 'server' in download_data:
            print('Server data not found in the json')
            success = False
        else:
            url_jar = download_data['server']['url']
            hash_jar = download_data['server']['sha1']
            path_jar = os.path.join(DOWNLOAD_DIR, 'server', 'JAR', 'server.jar')
            if not download_and_verify(url_jar, hash_jar, path_jar, 'Server JAR'):
                success = False
            
            if download_mappings and 'server_mappings' in download_data:
                url_map = download_data['server_mappings']['url']
                hash_map = download_data['server_mappings']['sha1']
                path_map = os.path.join(DOWNLOAD_DIR, 'server', 'mappings', 'server.txt')
                if not download_and_verify(url_map, hash_map, path_map, 'Server Mappings'):
                    success = False
    print('main JAR downlaoded, downloading libraries...')

    libs = full_data['libraries']

    base_path = os.path.join(DOWNLOAD_DIR, 'client', 'JAR', 'libraries')

    os.makedirs(base_path, exist_ok=True)

    for i ,lib in enumerate(libs, 1):
        data = lib['downloads']['artifact']

        if not data:
            continue

        url = data['url']
        sha1 = data['sha1']
        path = data['path']

        save_path = os.path.join(base_path, path)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        download_and_verify(url, sha1, save_path, f'Library: {i} / {len(libs)}')

    return success

def download_asset_index(full_data):
    asset_info = full_data['assetIndex']
    asset_id = asset_info['id']

    index_dir = os.path.join(DOWNLOAD_DIR, 'assets', 'indexes')
    os.makedirs(index_dir, exist_ok=True)
    
    index_path = os.path.join(index_dir, f'{asset_id}.json')
    
    success = download_and_verify(
        asset_info['url'], 
        asset_info['sha1'], 
        index_path, 
        f'Asset Index: {asset_id}'
    )
    
    if success:
        with open(index_path, 'r') as f:
            return json.load(f)
    return None

def download_assets(asset_index_data):
    assets_base_url = "https://resources.download.minecraft.net/"
    objects_dir = os.path.join(DOWNLOAD_DIR, 'assets', 'objects')
    os.makedirs(objects_dir, exist_ok=True)
    total_assets = len(asset_index_data['objects'])
    for i, (name, obj) in enumerate(asset_index_data['objects'].items(), 1):
        hash_val = obj['hash']
        hash_prefix = hash_val[:2]
        
        url = f'{assets_base_url}{hash_prefix}/{hash_val}'
        save_path = os.path.join(objects_dir, hash_prefix, hash_val)
        
        download_and_verify(url, hash_val, save_path, f'Asset Object: {i} / {total_assets}')

def unzip_file(full_data):
    natives_path = os.path.join(DOWNLOAD_DIR, 'client', 'natives')
    libs = full_data['libraries']

    for lib in libs:
        if OS_TYPE in lib['downloads']['artifact']['path']:
            jar_path = os.path.join(DOWNLOAD_DIR, 'client', 'JAR', 'libraries', lib['downloads']['artifact']['path'])
            print(f"Extracting natives from: {os.path.basename(jar_path)}...")
            with zipfile.ZipFile(jar_path, 'r') as zf:
                zf.extractall(natives_path)

manifest = get_version_manifest()

if manifest:
    latest_release = manifest['latest']['release']

    avaliable_versions = []

    for v in manifest['versions']:
        if v['id']:
            avaliable_versions.append(v['id'])
            if v['id'] == DESIRED_VERSION:
                version_data, json_path = download_version_data(DESIRED_VERSION, manifest)

def downlaod(json_path):
    if json_path:
        os.makedirs(f'{DOWNLOAD_DIR}/client', exist_ok=True)
        os.makedirs(f'{DOWNLOAD_DIR}/client/JAR', exist_ok=True)
        os.makedirs(f'{DOWNLOAD_DIR}/client/mappings', exist_ok=True)
        os.makedirs(f'{DOWNLOAD_DIR}/server', exist_ok=True)
        os.makedirs(f'{DOWNLOAD_DIR}/server/JAR', exist_ok=True)
        os.makedirs(f'{DOWNLOAD_DIR}/server/mappings', exist_ok=True)
        with open(file=json_path) as f:
                json_file = json.load(f)
        download_files(json_file)

        index_data = download_asset_index(json_file)

        download_assets(index_data)

        unzip_file(json_file)

    else:
        print('Error: no json path.')

if __name__ == '__main__':
    if json_path:
        downlaod(json_path=json_path)