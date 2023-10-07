import yaml
import json


def load_yaml(name):
    """ Load .YAML file and return a dictionary """
    with open(name) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return data


# Write JSON
def write_json(name, data):
    """ Write .JSON file """
    with open(name, 'w') as f:
        json.dump(data, f, indent=4)