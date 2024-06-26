import requests
import os
import argparse

def banner():
	return """
     _                       __                        
  __| |_   _ _ __ ___  _ __ / _\ ___  _ __   __ _ _ __ 
 / _` | | | | '_ ` _ \| '_ \\\ \\ / _ \| '_ \ / _` | '__|
| (_| | |_| | | | | | | |_) |\ \ (_) | | | | (_| | |   
 \__,_|\__,_|_| |_| |_| .__/\__/\___/|_| |_|\__,_|_|   
                      |_|                              

\t\t\t\tby @ph0r3nsic
"""

def list_projects():
	endpoint = "components/search_projects?ps=300"
	req = requests.get(url + endpoint)
	if req.status_code == 200:
		return req.json()

def list_files(project):
	endpoint = "components/tree?component="+project
	req = requests.get(url + endpoint)
	if req.status_code == 200:
		return req.json()

def download_file(project, file):
	endpoint = "sources/raw?key="+file
	req = requests.get(url + endpoint)
	filename = file.replace("/","_")
	with open(f"output/{project}/{filename}","w") as f:
		f.write(req.text)

def main():
	projects = []
	components = list_projects()["components"]

	for component in components:
		projects.append(component["key"])

	print(f"[i] Total of projects: {str(len(projects))}")
	
	if input("Proced download projects? (y/n): ") == "y":

		for project in projects:
			print(f"==> Downloading {project}")
			os.system(f"mkdir -p {output}/{project}")
			files = []
			resp = list_files(project)
			
			if "components" in resp:
				components = resp["components"]
				if len(components) > 0: 

					for component in components:
						files.append(component["key"])

					for file in files:
						download_file(project, file)
	else:
		print("[!] terminated by user...")

if __name__=="__main__":
	print(banner())
	parser = argparse.ArgumentParser(add_help=True)
	parser.add_argument("--url", help="Url of sonarqube api. Ex: https://sonarqube/api/", required=True)
	parser.add_argument("--output", help="Output folder to save projects. Ex: /tmp/dump", default="output")
	args = parser.parse_args()
	
	url = args.url
	output = args.output

	main()