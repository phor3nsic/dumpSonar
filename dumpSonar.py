import requests
import os
import sys
import argparse
import hashlib
import urllib3

# ------------------------------- Colors -------------------------------

class C:
	R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"; B = "\033[94m"
	CY = "\033[96m"; GR = "\033[90m"; BOLD = "\033[1m"; RST = "\033[0m"

	@classmethod
	def disable(cls):
		for k in ("R", "G", "Y", "B", "CY", "GR", "BOLD", "RST"):
			setattr(cls, k, "")

if not sys.stdout.isatty():
	C.disable()

# ------------------------------- Helpers ------------------------------

stats = {"downloaded": 0, "skipped": 0, "failed": 0, "verified": 0, "mismatch": 0, "bytes": 0}
session = requests.Session()

def banner():
	return f"""{C.CY}
     _                       __
  __| |_   _ _ __ ___  _ __ / _\\ ___  _ __   __ _ _ __
 / _` | | | | '_ ` _ \\| '_ \\\\ \\ / _ \\| '_ \\ / _` | '__|
| (_| | |_| | | | | | | |_) |\\ \\ (_) | | | | (_| | |
 \\__,_|\\__,_|_| |_| |_| .__/\\__/\\___/|_| |_|\\__,_|_|
                      |_|{C.RST}

\t\t\t\t{C.GR}by @ph0r3nsic{C.RST}
"""

def human(n):
	n = float(n)
	for unit in ("B", "KB", "MB", "GB", "TB"):
		if n < 1024:
			return f"{n:.1f}{unit}"
		n /= 1024
	return f"{n:.1f}PB"

def info(msg):    print(f"{C.B}[i]{C.RST} {msg}")
def ok(msg):      print(f"{C.G}[+]{C.RST} {msg}")
def warn(msg):    print(f"{C.Y}[!]{C.RST} {msg}")
def err(msg):     print(f"{C.R}[-]{C.RST} {msg}")

def progress(current, total, prefix=""):
	width = 28
	frac = current / total if total else 1.0
	filled = int(width * frac)
	bar = "█" * filled + "░" * (width - filled)
	label = (prefix[:28] + "…") if len(prefix) > 29 else prefix.ljust(29)
	sys.stdout.write(f"\r  {C.GR}{label}{C.RST} {C.CY}{bar}{C.RST} {int(frac * 100):3d}% ({current}/{total})")
	sys.stdout.flush()
	if current >= total:
		sys.stdout.write("\n")

def get(url_, **kwargs):
	kwargs.setdefault("timeout", timeout)
	kwargs.setdefault("verify", verify_tls)
	return session.get(url_, **kwargs)

def checksum_ok(content, checksum):
	"""Returns True/False if a known checksum matched, or None if none available."""
	if not checksum:
		return None
	for algo in ("sha1", "md5", "sha256"):
		if algo in checksum and checksum[algo]:
			digest = hashlib.new(algo, content).hexdigest()
			return digest.lower() == checksum[algo].lower()
	return None

def save(path, content, checksum=None):
	"""Writes content to path, accounting for skip/verify/mismatch stats. Returns status string."""
	# Resume: skip if a file with a matching checksum already exists.
	if os.path.exists(path) and checksum:
		with open(path, "rb") as f:
			if checksum_ok(f.read(), checksum):
				stats["skipped"] += 1
				return "skip"
	with open(path, "wb") as f:
		f.write(content)
	stats["downloaded"] += 1
	stats["bytes"] += len(content)
	result = checksum_ok(content, checksum)
	if result is True:
		stats["verified"] += 1
	elif result is False:
		stats["mismatch"] += 1
		return "mismatch"
	return "ok"

# ----------------------------- SonarQube ------------------------------

def sq_list_projects():
	req = get(url + "components/search_projects?ps=300")
	return req.json() if req.status_code == 200 else None

def sq_list_files(project):
	req = get(url + "components/tree?component=" + project + "&ps=500")
	return req.json() if req.status_code == 200 else None

def sq_download_file(project, file):
	req = get(url + "sources/raw?key=" + file)
	if req.status_code != 200 or req.text.lstrip().startswith('{"errors"'):
		stats["failed"] += 1
		return
	filename = file.replace("/", "_")
	# SonarQube returns source text; checksum validation is not available here.
	content = req.content
	with open(f"{output}/{project}/{filename}", "wb") as f:
		f.write(content)
	stats["downloaded"] += 1
	stats["bytes"] += len(content)

def run_sonarqube():
	resp = sq_list_projects()
	if not resp or "components" not in resp:
		err("No projects returned. Check the URL (must end with /api/) and access.")
		return

	projects = [c["key"] for c in resp["components"]]
	info(f"Total of projects: {C.BOLD}{len(projects)}{C.RST}")

	if input(f"{C.Y}[?]{C.RST} Proceed download projects? (y/n): ") != "y":
		warn("terminated by user...")
		return

	for project in projects:
		ok(f"Project {C.BOLD}{project}{C.RST}")
		os.makedirs(f"{output}/{project}", exist_ok=True)
		resp = sq_list_files(project)
		files = [c["key"] for c in resp["components"]] if resp and "components" in resp else []

		if not files:
			progress(1, 1, project)
			continue

		for i, file in enumerate(files, 1):
			sq_download_file(project, file)
			progress(i, len(files), project)

# ------------------------------- Nexus --------------------------------

def nx_list_repositories():
	req = get(url + "repositories")
	return req.json() if req.status_code == 200 else []

def nx_list_components(repository):
	items, token = [], None
	while True:
		endpoint = "components?repository=" + repository
		if token:
			endpoint += "&continuationToken=" + token
		req = get(url + endpoint)
		if req.status_code != 200:
			break
		data = req.json()
		items.extend(data.get("items", []))
		token = data.get("continuationToken")
		if not token:
			break
	return items

def nx_download_asset(repository, asset):
	download_url = asset.get("downloadUrl")
	if not download_url:
		stats["failed"] += 1
		return
	path = asset.get("path", "")
	checksum = asset.get("checksum", {})
	filename = path.replace("/", "_") if path else download_url.rsplit("/", 1)[-1]
	filepath = f"{output}/{repository}/{filename}"

	# Resume before hitting the network.
	if os.path.exists(filepath) and checksum:
		with open(filepath, "rb") as f:
			if checksum_ok(f.read(), checksum):
				stats["skipped"] += 1
				return
	try:
		req = get(download_url)
	except requests.RequestException:
		stats["failed"] += 1
		return
	if req.status_code != 200:
		stats["failed"] += 1
		return
	save(filepath, req.content, checksum)

def run_nexus():
	repos = nx_list_repositories()
	if not repos:
		err("No repositories returned. Check the URL (must end with /service/rest/v1/) and access.")
		return

	repositories = [r["name"] for r in repos]
	info(f"Total of repositories: {C.BOLD}{len(repositories)}{C.RST}")
	for r in repos:
		print(f"    {C.GR}- {r['name']} ({r.get('format', '?')}/{r.get('type', '?')}){C.RST}")

	if input(f"{C.Y}[?]{C.RST} Proceed download repositories? (y/n): ") != "y":
		warn("terminated by user...")
		return

	for repository in repositories:
		ok(f"Repository {C.BOLD}{repository}{C.RST}")
		os.makedirs(f"{output}/{repository}", exist_ok=True)
		components = nx_list_components(repository)
		assets = [a for c in components for a in c.get("assets", [])]

		if not assets:
			progress(1, 1, repository)
			continue

		for i, asset in enumerate(assets, 1):
			nx_download_asset(repository, asset)
			progress(i, len(assets), repository)

# ------------------------------- Summary ------------------------------

def summary():
	print(f"\n{C.BOLD}{'─' * 44}{C.RST}")
	print(f"{C.BOLD}  Summary{C.RST}")
	print(f"{C.BOLD}{'─' * 44}{C.RST}")
	print(f"  {C.G}Downloaded{C.RST} : {stats['downloaded']}")
	print(f"  {C.B}Skipped{C.RST}    : {stats['skipped']} {C.GR}(already present & valid){C.RST}")
	print(f"  {C.G}Verified{C.RST}   : {stats['verified']} {C.GR}(checksum matched){C.RST}")
	if stats["mismatch"]:
		print(f"  {C.R}Mismatch{C.RST}   : {stats['mismatch']} {C.GR}(checksum FAILED){C.RST}")
	if stats["failed"]:
		print(f"  {C.R}Failed{C.RST}     : {stats['failed']}")
	print(f"  {C.CY}Total size{C.RST} : {human(stats['bytes'])}")
	print(f"  {C.CY}Output{C.RST}     : {os.path.abspath(output)}")
	print(f"{C.BOLD}{'─' * 44}{C.RST}")

# -------------------------------- Main --------------------------------

def main():
	if mode == "sonarqube":
		run_sonarqube()
	elif mode == "nexus":
		run_nexus()
	summary()

if __name__ == "__main__":
	print(banner())
	parser = argparse.ArgumentParser(add_help=True)
	parser.add_argument("--mode", help="Target type", choices=["sonarqube", "nexus"], default="sonarqube")
	parser.add_argument("--url", help="Base URL. SonarQube ends with /api/ , Nexus ends with /service/rest/v1/ . Ex: https://target/api/", required=True)
	parser.add_argument("--output", help="Output folder to save data. Ex: /tmp/dump", default="output")
	parser.add_argument("--timeout", help="Request timeout in seconds (default: 30)", type=int, default=30)
	parser.add_argument("--insecure", help="Disable TLS certificate verification", action="store_true")
	args = parser.parse_args()

	mode = args.mode
	url = args.url if args.url.endswith("/") else args.url + "/"
	output = args.output
	timeout = args.timeout
	verify_tls = not args.insecure

	if args.insecure:
		urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
		warn("TLS verification disabled")

	try:
		main()
	except KeyboardInterrupt:
		print()
		warn("interrupted by user")
		summary()
