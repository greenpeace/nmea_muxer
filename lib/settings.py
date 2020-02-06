import json

class Settings:

    def __init__(self,period=0,servers=[],listeners=[]):
        self.period = period
        self.servers = servers
        self.listeners = listeners

    def __repr__(self):
        return "Settings:\n"+json.dumps(self.export(), indent=2, sort_keys=False)

    def export(self):
        sts = {"settings":{}}
        sts["settings"]["period"] = self.period
        sts["servers"] = self.servers
        sts["listeners"] = self.listeners
        return sts

    def save(self,servers,listeners,filename="current"):
        self.servers = list(map(lambda server: server.as_json(), servers))
        self.listeners = list(map(lambda listener: listener.as_json(), listeners))
        with open("./lib/settings/"+filename+".json","w") as f:
            f.write(json.dumps(self.export(), indent=2, sort_keys=True))

    def load(self,filename="current"):
        with open("./lib/settings/"+filename+".json","r") as f:
            try:
                data = json.load(f)
            except:
                return "JSON file parse error"

            for unit in data:
                if unit == 'settings':
                    for key, value in data[unit].items():
                        self.__dict__[key] = value
                else:
                    self.__dict__[unit] = data[unit]




