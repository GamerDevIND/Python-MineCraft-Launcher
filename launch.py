import json
import uuid
import subprocess
import os

from configs import (
    USERNAME,
    DOWNLOAD_DIR,
    MAX_RAM_GB,
    MIN_RAM_GB,
    DESIRED_VERSION,
    vanilla_version_dir,
    vanilla_json_path,
    fabric_json_path,
    client_jar,
    natives_dir,
    fabric_version_dir,
    USE_FABRIC
)

from pprint import pp

injector_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, "authlib-injector-1.2.7.jar"))

if not os.path.exists(vanilla_json_path):
    print(f"❌ Error: Vanilla metadata not found at {vanilla_json_path}")
    exit(1)

with open(vanilla_json_path, "r") as f:
    vanilla_data = json.load(f)

if USE_FABRIC:

    if not os.path.exists(fabric_json_path):
        print(f"❌ Error: Fabric metadata not found at {fabric_json_path}")
        exit(1)

    with open(fabric_json_path, "r") as f:
        fabric_data = json.load(f)

else:
    fabric_data = {}

def build_class_path(*json_files):
    # Search both potential library root locations
    candidate_bases = [
        os.path.join(DOWNLOAD_DIR, "libraries"),
        os.path.join(vanilla_version_dir, "client", "libraries")
    ]

    libs_to_load = []
    seen = set()

    for json_file in json_files:
        for lib in json_file.get("libraries", []):
            downloads = lib.get("downloads", {})
            artifact = downloads.get("artifact")

            if artifact:
                rel_path = artifact["path"]
            else:
                name = lib.get("name")
                if not name:
                    continue
                parts = name.split(":")
                if len(parts) < 3:
                    print(f"⚠️ Invalid library name: {name}")
                    continue
                
                group_path = os.path.join(*parts[0].split("."))
                artifact_name = parts[1]
                version = parts[2]
                classifier = f"-{parts[3]}" if len(parts) > 3 else ""
                
                rel_path = os.path.join(
                    group_path,
                    artifact_name,
                    version,
                    f"{artifact_name}-{version}{classifier}.jar"
                )

            lib_path = None
            for base in candidate_bases:
                check_path = os.path.join(base, rel_path)
                if os.path.exists(check_path):
                    lib_path = check_path
                    break

            if lib_path:
                normalized = os.path.normcase(os.path.abspath(lib_path))
                if normalized not in seen:
                    libs_to_load.append(lib_path)
                    seen.add(normalized)
            else:
                print("MISSING:", rel_path)

    libs_to_load.append(client_jar)
    return os.pathsep.join(libs_to_load)

def read_profile_json():

    profile_path = os.path.join(
        DOWNLOAD_DIR,
        "launcher_profiles.json"
    )

    if os.path.exists(profile_path):

        with open(profile_path, "r") as f:
            return json.load(f)

    return None

def create_profile_json(version_id, uuid__=None):

    existing_data = read_profile_json()

    uuid_ = uuid__ or str(uuid.uuid4())

    if existing_data:
        uuid_ = existing_data.get(
            "clientToken",
            uuid__ or str(uuid.uuid4())
        )

    profile_key = f"Profile-{version_id}"

    profile_content = {
        "name": f"Vanilla - {version_id}",
        "gameDir": os.path.abspath(DOWNLOAD_DIR),
        "lastVersionId": version_id,
        "javaArgs": (
            f"-Xmx{MAX_RAM_GB}G "
            f"-Xms{MIN_RAM_GB}G"
        ),
        "type": "custom",
        "created": uuid_[:8]
    }

    if existing_data:

        if existing_data.get("profiles", {}).get(profile_key) == profile_content:
            return uuid_

        data_to_save = existing_data
    else:

        data_to_save = {
            "profiles": {},
            "selectedProfile": "",
            "clientToken": uuid_,
            "authenticationDatabase": {}
        }

    data_to_save["profiles"][profile_key] = profile_content
    data_to_save["selectedProfile"] = profile_key

    profile_path = os.path.join(DOWNLOAD_DIR, "launcher_profiles.json")
    with open(profile_path, "w") as f:
        json.dump(data_to_save,f, indent=4
        )

    print(f"✅ Profile for {version_id} updated in: {profile_path}")

    return uuid_

uuid_offline = create_profile_json(DESIRED_VERSION,)


if USE_FABRIC:
    classpath = build_class_path(vanilla_data, fabric_data)
    raw_jvm_args = fabric_data.get("arguments", {}).get("jvm", [])
    fabric_jvm_args = [arg.strip() for arg in raw_jvm_args if isinstance(arg, str)]
    main_class = "net.fabricmc.loader.impl.launch.knot.KnotClient"
    asset_index = vanilla_data["assetIndex"]["id"]
else:
    classpath = build_class_path(vanilla_data)
    fabric_jvm_args = []
    main_class = vanilla_data["mainClass"]
    asset_index = vanilla_data["assetIndex"]["id"]

cmd = [
    "java",
    f"-Xmx{MAX_RAM_GB}G",
    f"-Xms{MIN_RAM_GB}G",
    f"-Djava.library.path={natives_dir}",
    f"-javaagent:{injector_path}=ely.by",
    *fabric_jvm_args,
    "-cp",
    classpath,
    main_class,
    "--version",
    DESIRED_VERSION,
    "--gameDir", os.path.abspath(DOWNLOAD_DIR),
    "--assetsDir",os.path.abspath(os.path.join(DOWNLOAD_DIR, "assets")),
    "--assetIndex",
    asset_index,
    "--uuid",
    uuid_offline,
    "--accessToken",
    "0",
    "--userType",
    "legacy",
    "--versionType",
    "release",
    "--username",
    USERNAME
]


pp(cmd)

with open("launcher.log", "w") as log_file:

    print("Log file opened at launcher.log")

    try:

        print(
            f"Launching Minecraft {DESIRED_VERSION} "
            f"(Fabric : {USE_FABRIC})..."
        )

        subprocess.run(cmd, stderr=subprocess.STDOUT, stdout=log_file, check=True)

    except subprocess.CalledProcessError:

        print(
            "❌ Game crashed. "
            "Check launcher.log for details."
        )