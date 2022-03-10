from file_tools import FileTools,steam_path_windows
import os
ft = FileTools("Portal",steam_path_windows())
base_text = "By proceeding you acknowledge you are responsible for running this."
if os.path.exists(ft.mod_folder):
    answer = input(base_text + " Press y to reinstall, u to uninstall")
    if answer == "y":
        ft.write_files()
    elif answer == 'u':
        ft.remove_mod()
else:
    answer = input(base_text + " Press y to install. Rerun to uninstall when the official fix is released.")
    if answer == "y":
        ft.write_files()


