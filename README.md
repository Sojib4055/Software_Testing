Steps to Install Packages from requirements.txt

1. Open a Terminal or Command Prompt
Launch Command Prompt (Windows) or Terminal (Mac/Linux).

2. Navigate to the Project Directory
Use the following command to navigate to your project folder:
cd /path/to/your/project

3. Create a Virtual Environment (Optional but Recommended)
Create a virtual environment using the following command:
python -m venv venv

4. Activate the Virtual Environment
Windows (Command Prompt):
venv\Scripts\activate
Windows (PowerShell):
.\venv\Scripts\Activate.ps1
Mac/Linux:
source venv/bin/activate

5. Install Packages
Use the following command to install the packages listed in requirements.txt:
pip install -r requirements.txt

6. Verify Installation
Ensure the packages were installed correctly by listing installed packages:
pip list

Troubleshooting Tips
Script Execution Policy Error (PowerShell): If you encounter a security error in PowerShell about script execution policies, run this command in Administrator PowerShell:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
Package Installation Errors:
oDouble-check your requirements.txt file for typos or incorrect package names.
oEnsure you are connected to the internet.
oRun pip install --upgrade pip if you face outdated pip issues.

7. Download Google chrome driver.
