#!/usr/bin/env python3
import sys
import re
import glob
import os
import time
import json
import tempfile
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Single-letter shorthand for global flags. Letters may be bundled behind one
# dash (e.g. -lv expands to --list --verbose) — every letter in a bundle
# must be recognized or the whole token is rejected as an unrecognized flag.
SHORT_FLAG_MAP = {
    "l": "--list",
    "v": "--verbose",
}


def expand_short_flags(argv):
    """Expand single-dash shorthand (bundled or not) into canonical --long flags.

    "-l" -> ["--list"], "-lv" -> ["--list", "--verbose"].
    Tokens that aren't a pure letters-only single-dash flag (e.g. "--long",
    plain filenames, "-") pass through unchanged. A bundle containing any
    unrecognized letter errors out immediately rather than guessing.
    """
    expanded = []
    for token in argv:
        is_short_bundle = (
            len(token) > 1
            and token[0] == '-'
            and token[1] != '-'
            and token[1:].isalpha()
        )
        if not is_short_bundle:
            expanded.append(token)
            continue

        letters = token[1:].lower()
        unknown = [c for c in letters if c not in SHORT_FLAG_MAP]
        if unknown:
            print(f"Error: Unrecognized flag '{token}' (unknown shorthand: {', '.join('-' + c for c in unknown)})")
            sys.exit(1)

        expanded.extend(SHORT_FLAG_MAP[c] for c in letters)
    return expanded


sys.argv = [sys.argv[0]] + expand_short_flags(sys.argv[1:])

# --verbose / -v enables the noisy Resolve path-validation diagnostics; quiet by default.
VERBOSE_FLAGS = {"--verbose", "-v"}
VERBOSE = bool(VERBOSE_FLAGS & {a.lower() for a in sys.argv})
if not VERBOSE:
    logging.getLogger().setLevel(logging.WARNING)


def vprint(*args, **kwargs):
    """print() gated behind --verbose, for setup diagnostics that are noise on a working install."""
    if VERBOSE:
        print(*args, **kwargs)


# --------------------------------------------------------------------------
# DaVinci Resolve API connection (only used by Resolve-backed flags, e.g.
# --list). Adapted from generate_srt.py's connection logic, trimmed to what
# these features need. Not imported or touched by the plain SRT-file path.
# --------------------------------------------------------------------------

RESOLVE_PATHS_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resolve_paths.json")


def find_module_locations(base_path):
    """Find possible locations of DaVinciResolveScript.py based on a base path.
    Only checks the standard location and directly in the specified path."""
    locations = []
    module_paths = []

    standard_location = os.path.join(base_path, "Modules", "DaVinciResolveScript.py")
    if os.path.isfile(standard_location):
        locations.append(os.path.dirname(standard_location))
        module_paths.append(standard_location)

    direct_location = os.path.join(base_path, "DaVinciResolveScript.py")
    if os.path.isfile(direct_location):
        locations.append(base_path)
        module_paths.append(direct_location)

    return {
        "locations": locations,
        "module_paths": module_paths
    }


def validate_resolve_paths():
    """Validate Resolve paths and prompt for custom paths if needed."""
    config_file = RESOLVE_PATHS_CONFIG_FILE
    config = {}
    modified = False

    vprint("\n=== Starting path validation ===")
    vprint("Checking for required files...")

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                vprint(f"Loaded config from: {config_file}")
                if "RESOLVE_SCRIPT_API" in config:
                    vprint(f"  Config API path: {config['RESOLVE_SCRIPT_API']}")
                if "RESOLVE_SCRIPT_LIB" in config:
                    vprint(f"  Config LIB path: {config['RESOLVE_SCRIPT_LIB']}")
        except Exception as e:
            logging.warning(f"Failed to load config file: {str(e)}")

    if sys.platform.startswith("win"):
        default_api_path = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
    elif sys.platform == "darwin":
        default_api_path = r"/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
    elif sys.platform.startswith("linux"):
        default_api_path = r"/opt/resolve/Developer/Scripting"
    else:
        default_api_path = ""

    if sys.platform.startswith("win"):
        default_lib_path = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
    elif sys.platform == "darwin":
        default_lib_path = r"/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
    elif sys.platform.startswith("linux"):
        default_lib_path = r"/opt/resolve/libs/Fusion/fusionscript.so"
    else:
        default_lib_path = ""

    vprint(f"Default API path: {default_api_path}")
    vprint(f"Default LIB path: {default_lib_path}")

    default_module_paths = find_module_locations(default_api_path)
    default_api_valid = len(default_module_paths["module_paths"]) > 0
    default_lib_valid = os.path.isfile(default_lib_path)

    vprint(f"Default module file exists: {default_api_valid}")
    vprint(f"Default library file exists: {default_lib_valid}")

    api_path = None
    if "RESOLVE_SCRIPT_API" in config:
        api_path = config["RESOLVE_SCRIPT_API"]
        os.environ["RESOLVE_SCRIPT_API"] = api_path
        vprint(f"Using API path from config: {api_path}")
    elif os.getenv("RESOLVE_SCRIPT_API"):
        api_path = os.getenv("RESOLVE_SCRIPT_API")
        vprint(f"Using existing API path from env: {api_path}")
    else:
        api_path = default_api_path
        os.environ["RESOLVE_SCRIPT_API"] = api_path
        vprint(f"Using default API path: {api_path}")

    lib_path = None
    if "RESOLVE_SCRIPT_LIB" in config:
        lib_path = config["RESOLVE_SCRIPT_LIB"]
        os.environ["RESOLVE_SCRIPT_LIB"] = lib_path
        vprint(f"Using LIB path from config: {lib_path}")
    elif os.getenv("RESOLVE_SCRIPT_LIB"):
        lib_path = os.getenv("RESOLVE_SCRIPT_LIB")
        vprint(f"Using existing LIB path from env: {lib_path}")
    else:
        lib_path = default_lib_path
        os.environ["RESOLVE_SCRIPT_LIB"] = lib_path
        vprint(f"Using default LIB path: {lib_path}")

    module_info = find_module_locations(api_path)
    module_exists = len(module_info["module_paths"]) > 0

    vprint("Checking possible module locations:")
    for path in module_info["module_paths"]:
        vprint(f"  - {path}: Found")

    if not module_exists:
        print("\n==================================================")
        print(f"DaVinciResolveScript.py not found at standard location:")
        print(f"{os.path.join(api_path, 'Modules', 'DaVinciResolveScript.py')}")
        print("==================================================")

        if default_api_valid:
            print(f"Default module file exists at one of these locations:")
            for path in default_module_paths["module_paths"]:
                print(f"  - {path}")

            use_default = input("Press Enter to use default path, or type a custom path: ")

            if not use_default.strip():
                os.environ["RESOLVE_SCRIPT_API"] = default_api_path
                api_path = default_api_path
                if "RESOLVE_SCRIPT_API" in config:
                    del config["RESOLVE_SCRIPT_API"]
                    modified = True
                print(f"Using default path: {default_api_path}")
            else:
                custom_path = use_default
                if os.path.isfile(custom_path):
                    module_dir = os.path.dirname(custom_path)
                    if os.path.basename(custom_path) == "DaVinciResolveScript.py":
                        api_parent = os.path.dirname(module_dir) if os.path.basename(module_dir) == "Modules" else module_dir
                        os.environ["RESOLVE_SCRIPT_API"] = api_parent
                        api_path = api_parent
                        config["RESOLVE_SCRIPT_API"] = api_parent
                        modified = True
                        print(f"Set API path to: {api_parent} (based on file: {custom_path})")
                    else:
                        print(f"Warning: The specified file does not appear to be DaVinciResolveScript.py")
                        print(f"Using path anyway: {custom_path}")
                        os.environ["RESOLVE_SCRIPT_API"] = module_dir
                        api_path = module_dir
                        config["RESOLVE_SCRIPT_API"] = module_dir
                        modified = True
                elif os.path.isdir(custom_path):
                    custom_module_info = find_module_locations(custom_path)
                    if custom_module_info["module_paths"]:
                        os.environ["RESOLVE_SCRIPT_API"] = custom_path
                        api_path = custom_path
                        config["RESOLVE_SCRIPT_API"] = custom_path
                        modified = True
                        print(f"Found module at: {custom_module_info['module_paths'][0]}")
                        print(f"Set API path to: {custom_path}")
                    else:
                        print(f"Warning: DaVinciResolveScript.py not found at or under: {custom_path}")
                        print(f"Using path anyway: {custom_path}")
                        os.environ["RESOLVE_SCRIPT_API"] = custom_path
                        api_path = custom_path
                        config["RESOLVE_SCRIPT_API"] = custom_path
                        modified = True
                else:
                    print(f"Warning: Path not found: {custom_path}")
                    print(f"Using default path: {default_api_path}")
                    os.environ["RESOLVE_SCRIPT_API"] = default_api_path
                    api_path = default_api_path
                    if "RESOLVE_SCRIPT_API" in config:
                        del config["RESOLVE_SCRIPT_API"]
                        modified = True
        else:
            print(f"Default module file not found at standard locations")
            print("Please provide a valid path to DaVinciResolveScript.py or its parent directory")

            while True:
                custom_path = input("Enter path to DaVinciResolveScript.py or its parent directory: ")
                if not custom_path.strip():
                    print("Error: A path must be provided.")
                    continue

                if os.path.isfile(custom_path):
                    module_dir = os.path.dirname(custom_path)
                    if os.path.basename(custom_path) == "DaVinciResolveScript.py":
                        api_parent = os.path.dirname(module_dir) if os.path.basename(module_dir) == "Modules" else module_dir
                        os.environ["RESOLVE_SCRIPT_API"] = api_parent
                        api_path = api_parent
                        config["RESOLVE_SCRIPT_API"] = api_parent
                        modified = True
                        print(f"Set API path to: {api_parent} (based on file: {custom_path})")
                        break
                    else:
                        print(f"Warning: The specified file does not appear to be DaVinciResolveScript.py")
                        retry = input("Use this path anyway? (y/n): ")
                        if retry.lower() == 'y':
                            os.environ["RESOLVE_SCRIPT_API"] = module_dir
                            api_path = module_dir
                            config["RESOLVE_SCRIPT_API"] = module_dir
                            modified = True
                            break
                elif os.path.isdir(custom_path):
                    custom_module_info = find_module_locations(custom_path)
                    if custom_module_info["module_paths"]:
                        os.environ["RESOLVE_SCRIPT_API"] = custom_path
                        api_path = custom_path
                        config["RESOLVE_SCRIPT_API"] = custom_path
                        modified = True
                        print(f"Found module at: {custom_module_info['module_paths'][0]}")
                        print(f"Set API path to: {custom_path}")
                        break
                    else:
                        print(f"Warning: DaVinciResolveScript.py not found at or under: {custom_path}")
                        retry = input("Use this path anyway? (y/n): ")
                        if retry.lower() == 'y':
                            os.environ["RESOLVE_SCRIPT_API"] = custom_path
                            api_path = custom_path
                            config["RESOLVE_SCRIPT_API"] = custom_path
                            modified = True
                            break
                else:
                    print(f"Error: Path not found: {custom_path}")

    lib_file_exists = os.path.isfile(lib_path)
    vprint(f"Library exists at {lib_path}: {lib_file_exists}")

    if not lib_file_exists:
        print("\n==================================================")
        print(f"ERROR: DaVinci Resolve library not found!")
        print(f"Expected at: {lib_path}")
        print("==================================================")

        if default_lib_valid:
            print(f"Default library exists at: {default_lib_path}")
            use_default = input("Press Enter to use default path, or type a custom path: ")
            if not use_default.strip():
                os.environ["RESOLVE_SCRIPT_LIB"] = default_lib_path
                lib_path = default_lib_path
                if "RESOLVE_SCRIPT_LIB" in config:
                    del config["RESOLVE_SCRIPT_LIB"]
                    modified = True
                print(f"Using default path: {default_lib_path}")
            else:
                custom_path = use_default
                if os.path.isfile(custom_path):
                    os.environ["RESOLVE_SCRIPT_LIB"] = custom_path
                    lib_path = custom_path
                    config["RESOLVE_SCRIPT_LIB"] = custom_path
                    modified = True
                    print(f"Using custom path: {custom_path}")
                else:
                    print(f"Warning: File not found at '{custom_path}'")
                    print(f"Using default path: {default_lib_path}")
                    os.environ["RESOLVE_SCRIPT_LIB"] = default_lib_path
                    lib_path = default_lib_path
                    if "RESOLVE_SCRIPT_LIB" in config:
                        del config["RESOLVE_SCRIPT_LIB"]
                        modified = True
        else:
            print(f"Default library also not found at: {default_lib_path}")

            while True:
                custom_path = input("Enter path to DaVinci Resolve library file: ")
                if not custom_path.strip():
                    print("Error: A path must be provided.")
                    continue

                if os.path.isfile(custom_path):
                    os.environ["RESOLVE_SCRIPT_LIB"] = custom_path
                    lib_path = custom_path
                    config["RESOLVE_SCRIPT_LIB"] = custom_path
                    modified = True
                    print(f"Using custom path: {custom_path}")
                    break
                else:
                    print(f"Error: File not found at '{custom_path}'. Please try again.")

    if modified:
        try:
            if not config:
                if os.path.exists(config_file):
                    os.remove(config_file)
                    print(f"Removed empty config file: {config_file}")
            else:
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                print(f"Saved custom paths to {config_file}")
        except Exception as e:
            logging.warning(f"Failed to save config file: {str(e)}")

    logging.info("========== FINAL PATH CONFIGURATION ==========")
    logging.info(f"Using RESOLVE_SCRIPT_API: {api_path}")
    logging.info(f"Using RESOLVE_SCRIPT_LIB: {lib_path}")

    module_info = find_module_locations(api_path)
    for path in module_info["locations"]:
        if path not in sys.path:
            sys.path.append(path)
            logging.info(f"Added to Python path: {path}")

    if api_path and api_path not in sys.path and os.path.exists(api_path):
        sys.path.append(api_path)
        logging.info(f"Added API path to Python path: {api_path}")

    logging.info("=============================================")

    success = test_resolve_import_in_subprocess()
    if not success:
        print("\nWARNING: DaVinci Resolve API import test failed in a separate process.")
        print("This may indicate compatibility issues with your Python environment and DaVinci Resolve.")
        print("The script will still attempt to continue, but may fail or crash.")

        should_continue = input("\nDo you want to continue anyway? (y/n): ")
        if should_continue.lower() != 'y':
            print("Exiting as requested.")
            sys.exit(1)

    return success


def test_resolve_import_in_subprocess():
    """Test importing DaVinciResolveScript in a separate process for safety"""
    logging.info("Testing DaVinci Resolve import in a separate process...")

    api_path = os.environ.get("RESOLVE_SCRIPT_API", "")
    lib_path = os.environ.get("RESOLVE_SCRIPT_LIB", "")

    module_info = find_module_locations(api_path)
    module_locations = module_info["locations"]
    module_files = module_info["module_paths"]

    vprint("Found module locations:")
    for path in module_files:
        vprint(f"  - {path}")

    search_paths = []
    if os.path.exists(api_path):
        search_paths.append(api_path)
    if os.path.exists(os.path.dirname(api_path)):
        search_paths.append(os.path.dirname(api_path))

    for loc in module_locations:
        if loc not in search_paths and os.path.exists(loc):
            search_paths.append(loc)

    vprint(f"Search paths to be used: {search_paths}")

    with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
        test_script = f.name

        f.write(f'''
import os
import sys

os.environ["RESOLVE_SCRIPT_API"] = r"{api_path}"
os.environ["RESOLVE_SCRIPT_LIB"] = r"{lib_path}"

search_paths = {search_paths!r}
for path in search_paths:
    if path and path not in sys.path:
        sys.path.append(path)
        print(f"Added {{path}} to Python path")

module_files = {module_files!r}
for module_file in module_files:
    print(f"Known module file: {{module_file}}")

print(f"Python sys.path: {{sys.path}}")

try:
    import DaVinciResolveScript
    print("Successfully imported DaVinciResolveScript in test process")
    sys.exit(0)
except ImportError as e:
    print(f"Standard import failed: {{e}}")

for module_file in module_files:
    module_dir = os.path.dirname(module_file)

    try:
        if module_dir not in sys.path:
            sys.path.append(module_dir)
            print(f"Added module directory {{module_dir}} directly to path")

        import DaVinciResolveScript
        print(f"Successfully imported DaVinciResolveScript after adding {{module_dir}}")
        sys.exit(0)
    except ImportError as e:
        print(f"Import still failed with {{module_dir}} in path: {{e}}")

print("Trying direct module loading with importlib...")
try:
    import importlib.util

    for module_file in module_files:
        try:
            print(f"Trying to load {{module_file}} with importlib...")
            spec = importlib.util.spec_from_file_location("DaVinciResolveScript", module_file)
            if spec:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print(f"Successfully loaded {{module_file}} with importlib")
                sys.path.insert(0, os.path.dirname(module_file))
                sys.exit(0)
        except Exception as e:
            print(f"Importlib loading failed for {{module_file}}: {{e}}")
except Exception as e:
    print(f"Importlib approach failed: {{e}}")

print("All import attempts failed")
sys.exit(1)
''')

    try:
        logging.info(f"Running import test script: {test_script}")
        result = subprocess.run(
            [sys.executable, test_script],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            logging.info("Import test succeeded in subprocess")
            logging.info(f"Subprocess stdout: {result.stdout}")
            return True
        else:
            logging.error(f"Import test failed in subprocess with exit code {result.returncode}")
            logging.error(f"Subprocess stderr: {result.stderr}")
            logging.error(f"Subprocess stdout: {result.stdout}")
            return False

    except subprocess.TimeoutExpired:
        logging.error("Import test timed out - this suggests the import would hang or crash")
        return False
    except Exception as e:
        logging.error(f"Error running import test: {e}")
        return False
    finally:
        try:
            os.unlink(test_script)
        except:
            pass


def get_resolve():
    """Connect to a running DaVinci Resolve instance via its scripting API.

    Validates/discovers the Resolve script paths on first use, imports
    DaVinciResolveScript, and returns the live Resolve object.
    """
    validate_resolve_paths()

    try:
        import DaVinciResolveScript as dvr_script
    except ImportError as e:
        logging.error(f"Failed to import DaVinciResolveScript: {str(e)}")
        print("\nError importing DaVinci Resolve script libraries. Please check:")
        print("1. DaVinci Resolve is properly installed")
        print("2. You have the correct version of Python (64-bit)")
        print("3. The paths to DaVinci Resolve libraries are correct")
        print("\nPaths checked:")
        print(f"API path: {os.environ.get('RESOLVE_SCRIPT_API', 'Not set')}")
        print(f"Library path: {os.environ.get('RESOLVE_SCRIPT_LIB', 'Not set')}")
        sys.exit(1)

    logging.info("Getting Resolve object...")
    try:
        resolve = dvr_script.scriptapp("Resolve")
        if not resolve:
            raise Exception("Failed to get Resolve object")

        project_manager = resolve.GetProjectManager()
        if not project_manager:
            raise Exception("Failed to get project manager - Resolve may not be ready")

        current_page = resolve.GetCurrentPage()
        if current_page != "edit":
            resolve.OpenPage("edit")
            time.sleep(1)

        return resolve
    except Exception as e:
        logging.error(f"Error getting Resolve object: {str(e)}")
        raise


def get_current_project():
    """Get the current project in Resolve."""
    try:
        resolve = get_resolve()
        if not resolve:
            logging.error("Failed to get Resolve object")
            return None

        project_manager = resolve.GetProjectManager()
        if not project_manager:
            logging.error("Failed to get project manager")
            return None

        current_project = project_manager.GetCurrentProject()
        if not current_project:
            logging.error("No project is currently open")
            return None

        logging.info(f"Using current project: {current_project.GetName()}")
        return current_project
    except Exception as e:
        logging.error(f"Error getting current project: {str(e)}")
        return None


def list_timelines(project):
    """Return the names of all timelines in the given project, in timeline index order."""
    count = project.GetTimelineCount()
    names = []
    for i in range(1, count + 1):
        timeline = project.GetTimelineByIndex(i)
        if timeline:
            names.append(timeline.GetName())
    return names


def handle_list_flag():
    """Print the timelines in the current project and exit."""
    resolve = get_resolve()
    if not resolve:
        print("Error: Could not connect to DaVinci Resolve. Is it running?")
        sys.exit(1)

    project = get_current_project()
    if not project:
        print("Error: No project is currently open in Resolve.")
        sys.exit(1)

    names = list_timelines(project)
    if not names:
        print(f"No timelines found in project '{project.GetName()}'.")
        sys.exit(0)

    print(f"Timelines in project '{project.GetName()}':")
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name}")
    sys.exit(0)


def require_standalone(argv, flag):
    """Exit with an error if any argument besides `flag` (and --verbose/-v) is present.

    Used for flags like --list that don't compose with files or other
    flags — they do one specific thing and exit.
    """
    allowed = {flag} | VERBOSE_FLAGS
    extra = [a for a in argv if a.lower() not in allowed]
    if extra:
        print(f"Error: {flag} must be used standalone (only --verbose/-v may accompany it).")
        print(f"  Unexpected argument(s): {' '.join(extra)}")
        sys.exit(1)


def parse_time(time_str):
    """Convert SRT time format to milliseconds."""
    parts = time_str.split(',')
    time_parts = parts[0].split(':')
    milliseconds = parts[1]
    hours, minutes, seconds = map(int, time_parts)
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + int(milliseconds)

def format_time(milliseconds):
    """Convert milliseconds to SRT time format."""
    hours = milliseconds // 3600000
    milliseconds %= 3600000
    minutes = milliseconds // 60000
    milliseconds %= 60000
    seconds = milliseconds // 1000
    milliseconds %= 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def process_srt_file(file_path, gap_mode="after"):
    """Process an SRT file to remove gaps between subtitles."""
    print(f"Processing {file_path} with gap mode: {gap_mode}", flush=True)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        print(f"UTF-8 decoding failed, trying with latin-1", flush=True)
        # Try with a different encoding if utf-8 fails
        with open(file_path, 'r', encoding='latin-1') as file:
            content = file.read()
    
    # Parse the SRT file into subtitle blocks
    subtitles = []
    
    # Split the content by empty lines to get subtitle blocks
    blocks = re.split(r'\r?\n\r?\n', content.strip())
    
    for i, block in enumerate(blocks):
        lines = block.split('\n')
        if len(lines) >= 3:  # Ensure we have index, timing, and text
            index = lines[0]
            timing = lines[1]
            text = '\n'.join(lines[2:])
            
            # Parse timing
            match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', timing)
            if match:
                start_time, end_time = match.groups()
                start_ms = parse_time(start_time)
                end_ms = parse_time(end_time)
                
                subtitle = {
                    'index': index,
                    'start': start_ms,
                    'end': end_ms,
                    'text': text
                }
                subtitles.append(subtitle)
            else:
                print(f"Warning: Failed to parse timing in block {i}: {timing}", flush=True)
        else:
            print(f"Warning: Block {i} has fewer than 3 lines: {lines}", flush=True)
    
    # Apply gap removal
    changes_made = 0
    if len(subtitles) > 1:
        for i in range(len(subtitles) - 1):
            current = subtitles[i]
            next_subtitle = subtitles[i + 1]
            
            if gap_mode == "after":
                # Make the end time of current subtitle match the start time of next subtitle
                if current['end'] != next_subtitle['start']:
                    current['end'] = next_subtitle['start']
                    changes_made += 1
            else:  # gap_mode == "before"
                # Make the start time of next subtitle match the end time of current subtitle
                if next_subtitle['start'] != current['end']:
                    next_subtitle['start'] = current['end']
                    changes_made += 1
    
    print(f"Made {changes_made} timing changes", flush=True)
    
    # Reconstruct the SRT content
    output_content = ''
    for i, subtitle in enumerate(subtitles):
        output_content += f"{subtitle['index']}\n"
        output_content += f"{format_time(subtitle['start'])} --> {format_time(subtitle['end'])}\n"
        output_content += f"{subtitle['text']}\n"
        
        # Add blank line between subtitles except for the last one
        if i < len(subtitles) - 1:
            output_content += "\n"
    
    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(output_content)
    
    print(f"Successfully processed {file_path}", flush=True)

def main():
    """Main function to handle command line arguments and process files."""
    argv = sys.argv[1:]
    argv_lower = [a.lower() for a in argv]

    if "--list" in argv_lower:
        require_standalone(argv, "--list")
        handle_list_flag()

    if len(sys.argv) < 2:
        print("Usage: python subtitle_gap_remover.py <file_path(s)> [before|after]", flush=True)
        print("  file_path(s): Path(s) to SRT file(s), wildcards accepted", flush=True)
        print("  before|after: Optional gap mode, defaults to 'after'", flush=True)
        print("  -l, --list: List timelines in the currently open Resolve project, then exit", flush=True)
        return

    # Check if the last argument is a gap mode
    gap_mode = "after"  # Default
    files_to_process = []

    if sys.argv[-1].lower() in ["before", "after"]:
        gap_mode = sys.argv[-1].lower()
        file_args = sys.argv[1:-1]
    else:
        file_args = sys.argv[1:]
    
    # Process all file arguments, expanding wildcards
    for arg in file_args:
        expanded_files = glob.glob(arg)
        if expanded_files:
            files_to_process.extend(expanded_files)
        else:
            print(f"Warning: No files found matching '{arg}'", flush=True)
    
    if not files_to_process:
        print("No files to process.", flush=True)
        return
    
    # Process each file
    for file_path in files_to_process:
        if os.path.isfile(file_path):
            process_srt_file(file_path, gap_mode)
        else:
            print(f"Warning: '{file_path}' is not a file.", flush=True)

if __name__ == "__main__":
    main() 