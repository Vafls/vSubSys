import os

config_path = r'C:\vLaunch\kernel\config\global.cfg'
kernel_path = r'C:\vLaunch\kernel\kernel.py'

def check_and_create_config():
    if not os.path.exists(config_path):
        with open(config_path, 'w') as config_file:
            config_file.write('profile_1_name=\n')
            config_file.write('profile_1_pass=\n')
        print("File global.cfg has been created.")
    with open(config_path, 'r') as config_file:
        lines = config_file.readlines()
    
    profile_name = None
    profile_pass = None
    for line in lines:
        if line.startswith('profile_1_name='):
            profile_name = line.split('=')[1].strip()
        elif line.startswith('profile_1_pass='):
            profile_pass = line.split('=')[1].strip()
    
    if not profile_name:
        print("--------------------")
        profile_name = input("Enter profile name: ")
    if not profile_pass:
        print("--------------------")
        profile_pass = input("Enter profile password: ")
    
    with open(config_path, 'w') as config_file:
        config_file.write(f'profile_1_name={profile_name}\n')
        config_file.write(f'profile_1_pass={profile_pass}\n')

def run_kernel():
    os.system(f'python {kernel_path}')

if __name__ == "__main__":
    check_and_create_config()
    run_kernel()