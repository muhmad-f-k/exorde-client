import logging
from importlib import metadata
from importlib import import_module, metadata
import re
import aiohttp
import subprocess
from types import ModuleType


from importlib.metadata import PackageNotFoundError


import os


async def is_up_to_date(repository_path) -> bool:
    def is_older_version(version1, version2):
        # Remove the "v" prefix if present
        if version1.startswith("v"):
            version1 = version1[1:]
        if version2.startswith("v"):
            version2 = version2[1:]

        # Split the versions into major, middle, and minor components
        major1, middle1, minor1 = version1.split(".")
        major2, middle2, minor2 = version2.split(".")

        # Compare the major components
        if int(major1) < int(major2):
            return True
        elif int(major1) > int(major2):
            return False

        # If major components are equal, compare the middle components
        if int(middle1) < int(middle2):
            return True
        elif int(middle1) > int(middle2):
            return False

        # If major and middle components are equal, compare the minor components
        if int(minor1) < int(minor2):
            return True
        elif int(minor1) > int(minor2):
            return False

        # The versions are equal
        return False

    async def fetch_version_from_setup_file(setup_file_url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(setup_file_url) as response:
                # Error handling for non-successful HTTP status codes
                if response.status != 200:
                    raise ValueError(
                        "An error occurred while fetching the setup file at the specified endpoint"
                    )

                # Asynchronously read response data
                response_text = await response.text()

                # Use regular expressions to parse setup version
                version_match = re.search(r'version="(.+?)"', response_text)
                if version_match:
                    return version_match.group(1)
                else:
                    raise ValueError(
                        "No versions were found in the specified setup file"
                    )

    try:
        module_name = os.path.basename(repository_path.rstrip("/"))
    except:
        raise TypeError(
            f"is_up_to_date(repository_path), '{repository_path}' is not a valid repository"
        )
    try:
        local_version = metadata.version(module_name)
    except Exception as e:
        logging.info(
            "[MODULE LOADER ERROR] COULD NOT LOAD local_version"
        )
        return False

    setup_path = repository_path.replace(
        "https://github.com/", "https://raw.githubusercontent.com/"
    )
    try:
        online_version = await fetch_version_from_setup_file(
            f"{setup_path}/main/setup.py"
        )
    except Exception as e:
        logging.info(
            "[MODULE LOADER ERROR] COULD NOT LOAD online_version"
        )
        return False

    logging.info(
        f"version -> local: '{local_version}' | remote: '{online_version}'"
    )
    if is_older_version(local_version, online_version):
        logging.info(
            "[is_older_version] the online version is newer!"
        )
        return False
    logging.info(
        "[is_older_version] the online version is not newer, no update needed."
    )
    return True


async def get_scraping_module(repository_path) -> ModuleType:
    module_name = os.path.basename(repository_path.rstrip("/"))
    try:
        if not await is_up_to_date(repository_path):
            subprocess.check_call(["pip", "install", f"git+{repository_path}.git"])
    except (subprocess.CalledProcessError, PackageNotFoundError):
        raise RuntimeError("Failed to install or import the module.")

    try:
        loaded_module = import_module(module_name)
    except ImportError:
        logging.info(
            f"[MODULE LOADER Scraping module] - Could not import or land the module from {repository_path}"
        )
    except Exception as e:
        logging.info(
            f"[MODULE LOADER Scraping module] Error: {e}"
        )

    return loaded_module
