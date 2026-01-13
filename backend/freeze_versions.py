from importlib.metadata import version, PackageNotFoundError
import re


def pin_requirements(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    with open(file_path, 'w') as f:
        for line in lines:
            line_stripped = line.strip()

            # 1. Preserve comments and empty lines exactly as is
            if not line_stripped or line_stripped.startswith('#'):
                f.write(line)
                continue

            # 2. Extract the base package name to query the version
            # Regex handles: "pkg", "pkg[extra]", "pkg==1.0", "pkg>=1.0"
            # We split on strict version operators or brackets to get the name
            # NOTE: This is a simple parser for your specific requirements.txt style
            parts = re.split(r'[\[<=>]', line_stripped)
            package_name = parts[0].strip()

            try:
                # 3. Get the installed version using the modern library
                installed_ver = version(package_name)

                # 4. Reconstruct the line
                # If the user wrote "uvicorn[standard]", keep the "[standard]" part
                # but append/replace the version.

                # Check if there were extras in the original line
                if '[' in line_stripped:
                    # extract "uvicorn[standard]" part, ignore old version info if present
                    base_with_extra = line_stripped.split(']')[0] + ']'
                    f.write(f"{base_with_extra}=={installed_ver}\n")
                else:
                    f.write(f"{package_name}=={installed_ver}\n")

            except PackageNotFoundError:
                print(f"Warning: Package '{package_name}' not found in environment. Skipping.")
                f.write(line)


if __name__ == "__main__":
    pin_requirements('requirements.txt')
    print("requirements.txt successfully updated using importlib.metadata.")
