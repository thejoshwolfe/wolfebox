
import os

def read_settings(settings_dir_name, default_settings_str):
    settings_dir = os.path.join(os.path.expanduser("~"), ".config", settings_dir_name)
    if not os.path.isdir(settings_dir):
        # let any exceptions bubble
        os.makedirs(settings_dir)
    settings_path = os.path.join(settings_dir, "config.py")
    # try to read settings
    try:
        # eval chokes on CRLF sometimes, so use 'U'
        with open(settings_path, "rU") as settings_file:
            settings = eval(settings_file.read())
        if type(settings) != dict:
            raise TypeError()
    except:
        # swallow all exceptions from mysterious user code and use default settings
        # TODO: this is bad
        with open(settings_path, "w") as settings_file:
            settings_file.write(default_settings_str)
        settings = eval(default_settings_str)
    return (settings_dir, settings_path, settings)
