import os
import sys

site_packages = [p for p in sys.path if 'site-packages' in p][0]
broken_packages = []

for item in os.listdir(site_packages):
    if item.endswith('.dist-info'):
        record_path = os.path.join(site_packages, item, 'RECORD')
        if os.path.exists(record_path):
            with open(record_path, 'r') as f:
                records = f.read().splitlines()
            files_to_check = [r.split(',')[0] for r in records if '.dist-info' not in r and r.endswith('.py')]
            if files_to_check:
                broken = True
                for f in files_to_check[:5]:
                    if os.path.exists(os.path.join(site_packages, f)):
                        broken = False
                        break
                if broken:
                    pkg_name = item.split('-')[0]
                    broken_packages.append(pkg_name)

print("BROKEN_PACKAGES=" + " ".join(set(broken_packages)))
