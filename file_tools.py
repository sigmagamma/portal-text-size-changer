import os
import sys
import winreg
from shutil import rmtree
from os import path,remove

import json
import shlex
import re
import vpk

##Steam logic
def steam_path_windows():
    try:
        hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\WOW6432Node\Valve\Steam")
    except:
        hkey = None
        print(sys.exc_info())
    try:
        steam_path = winreg.QueryValueEx(hkey, "InstallPath")
    except:
        steam_path = None
        print(sys.exc_info())
    return steam_path[0] + "\steamapps\common"


def steam_path_linux():
    return "~/.steam/steam/steamapps/common"



class FileTools:
    def __init__(self, game,game_service_path):

        if (game is not None):
            with open(self.get_patch_gamedata(),'r') as game_data_file:
                data = json.load(game_data_file).get(game)
                if data is not None:
                    # text and filenames logic
                    self.game = game
                    self.basegame = data['basegame']
                    self.basegame_path = "\\" + self.game + "\\" + self.basegame
                    self.game_parent_path = game_service_path
                    full_basegame_path = self.get_full_basegame_path()
                    if not os.path.exists(full_basegame_path):
                        raise Exception("folder "+full_basegame_path + " doesn't exist. Please install the game. ")

                    # mod folder logic
                    self.mod_folder = self.get_custom_folder()
                    self.os = data.get('os')

                    # scheme file logic
                    self.scheme_file_name = data.get("scheme_file_name")
                    self.format_replacements = data.get("format_replacements")
                    self.vpk_file_name = data.get("vpk_file_name")
                    self.save_scheme_file_from_vpk()
                    self.source_scheme_path =  self.get_patch_scheme_path()
                else:
                    return None
        else:
            return None

    ## general folder logic
    # patch are the local files of the patch.
    # basegame is the content folder for the original game (usually something like portal/portal)
    # mod is where the mod gets placed (for instance portal/custom/sizepatch)

    def get_patch_gamedata(self):
        filename = "game_data.json"
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            filename = path.abspath(path.join(path.dirname(__file__), filename))
        return filename

    def get_full_game_path(self):
        return self.game_parent_path + "\\"+self.game

    def get_full_basegame_path(self):
        return self.game_parent_path + self.basegame_path

    def get_basegame_resource_folder(self):
        return self.get_full_basegame_path() + "\\resource"

    def get_custom_parent_folder(self):
        return self.get_full_basegame_path() + "\custom"

    def get_custom_folder(self):
        return self.get_custom_parent_folder()+"\sizepatch"

    def get_mod_resource_folder(self):
        return self.mod_folder+"\\resource"

    def create_mod_folders(self):
        mod_resource_folder = self.get_mod_resource_folder()
        if not os.path.exists(mod_resource_folder):
            os.makedirs(mod_resource_folder)
    def remove_mod_folder(self):
        rmtree(self.mod_folder)
        remove(self.source_scheme_path)
    def remove_mod(self):
        self.remove_mod_folder()

    ## scheme files logic
    def check_compatibility(self,platform_string):
        lexer = shlex.shlex(platform_string)
        state = True
        negate = False
        parantheses = False
        in_paran = ""
        for token in lexer:
            if token == ")":
                state = self.check_compatibility(in_paran) != negate
                negate = False
                in_paran = ""
            elif parantheses:
                in_paran += token
            elif token == "!":
                negate = True
            elif token == "||" and state:
                break
            elif token == "&&" and not state:
                break
            elif token == "$":
                continue
            elif token == "(":
                parantheses = True
            else:
                compatability = (token == self.os) or (token == "GAMECONSOLE" and self.os in ["X360","PS3"])
                state = compatability != negate
                negate = False
        return state


    def write_scheme_file(self,source_scheme_path, dest_scheme_path,format_replacements):
        with open(source_scheme_path, 'r') as f_in, \
                open(dest_scheme_path, 'w') as f_out:
            while True:
                line = f_in.readline()
                if not line:
                    break
                matched = False
                for key in format_replacements.keys():
                    compare_key = "\""+key+"\""
                    potential_key = line.strip()
                    if potential_key.startswith(compare_key) or potential_key.startswith(key):
                        f_out.write(line)
                        f_out.write(f_in.readline())
                        replacement = format_replacements.get(key)
                        next = f_in.readline()
                        while True:
                            next_stripped =  next.strip("\"\t\n")
                            if not next_stripped.isnumeric():
                                f_out.write(next)
                                break
                            f_out.write(next)
                            format = replacement.get(next_stripped)
                            if format is not None:
                                f_out.write(f_in.readline())
                                while True:
                                    field_value = f_in.readline()
                                    if field_value.strip("\"\t\n") == "}":
                                        f_out.write(field_value)
                                        next = f_in.readline()
                                        break
                                    fv_array = [ a for a in re.split('\"\s{1,}\"|\s{1,}\"|]\s{1,}|\"\s{1,}\[|\"\n',field_value) if a != '']
                                    if len(fv_array) > 2 and not self.check_compatibility(fv_array[2]):
                                        f_out.write(field_value)
                                        continue
                                    fv_key = fv_array[0]
                                    value = format.get(fv_key)
                                    if value is not None:
                                        field_value = field_value.replace(fv_array[1],value)
                                    f_out.write(field_value)
                        matched = True
                        break
                if not matched:
                    f_out.write(line)

    def get_basegame_scheme_path(self):
        return self.get_basegame_resource_folder()+"\\"+self.scheme_file_name

    def get_mod_scheme_path(self):
        return self.get_mod_resource_folder() + "\\" + self.scheme_file_name

    def get_patch_scheme_path(self):
        return self.scheme_file_name

    def get_basegame_vpk_path(self):
        return self.get_full_basegame_path() + "\\" + self.vpk_file_name

    def save_scheme_file_from_vpk(self):
        pak = vpk.open(self.get_basegame_vpk_path())
        pakfile = pak.get_file("resource/" + self.scheme_file_name)
        pakfile.save(self.get_patch_scheme_path())
    ## main write function
    def write_files(self):
        self.create_mod_folders()
        if self.scheme_file_name is not None:
            self.write_scheme_file(self.source_scheme_path,self.get_mod_scheme_path(),self.format_replacements)
            os.remove(self.source_scheme_path)