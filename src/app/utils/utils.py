import os.path

@staticmethod
def get_script_path():
    # Get script path
    script_dir = os.path.dirname(os.path.abspath("main.py"))
    return script_dir


@staticmethod
def resolve_sys_path(name):
    path = os.path.join(get_script_path(), name)
    
    return path