import os, json

class Settings:

    def __init__(self,app=None,period=0,talkers=[],listeners=[]):
        self.app = app
        self.period = period
        self.talkers = talkers
        self.listeners = listeners

    def __repr__(self):
        return "Settings:\n"+json.dumps(self.export(), indent=2, sort_keys=False)

    def export(self):
        sts = {"settings":{}}
        sts["settings"]["period"] = self.period
        sts["talkers"] = self.talkers
        sts["listeners"] = self.listeners
        return sts

    def save(self,talkers,listeners,filename="_current"):
        self.talkers = list(map(lambda talker: talker.as_json(), talkers))
        self.listeners = list(map(lambda listener: listener.as_json(), listeners))
        with open("./lib/settings/"+filename+".json","w") as f:
            f.write(json.dumps(self.export(), indent=2, sort_keys=True))

    def load(self,filename="_current"):
        path = os.path.join(self.app.root_path, "lib", "settings", (filename+".json"))
        if not os.path.isfile(path):
            return [False,"File not found"]
        with open(path,"r") as f:
            try:
                data = json.load(f)
            except:
                return [False,"JSON file parse error"]

            for unit in data:
                if unit == 'settings':
                    for key, value in data[unit].items():
                        self.__dict__[key] = value
                else:
                    self.__dict__[unit] = data[unit]

            return [True]




