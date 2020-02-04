import json

class Settings:

    def __init__(self,freq=1,servers=[],listeners=[]):
        self.freq = freq
        self.servers = servers
        self.listeners = listeners

    def __repr__(self):
        return "Settings:\n"+json.dumps(self.export(), indent=2, sort_keys=False)

    def export(self):
        sts = {"settings":{}}
        sts["settings"]["freq"] = self.freq
        sts["servers"] = []
        for server in self.servers:
            sts["servers"].append(server.as_json)
        for listener in self.listeners:
            sts["listeners"].append(listener.as_json)
        return sts

    def save(self,filename="current"):
        with open("./lib/settings/"+filename+".json","w") as f:
            f.write(json.dumps(self.export(), indent=2, sort_keys=True))

    def load(self,filename="current"):
        with open("./lib/settings/"+filename+".json","r") as f:
            try:
                data = json.load(f)
            except:
                return "JSON file parse error"

            try:
                for unit, attrs in data.items():
                    obj = {"settings":self,"ship":self.ship,"target":self.target,"rotator":self.rotator}[unit]
                    if not obj:
                        obj = eval(unit.title())()

                    for key, value in attrs.items():
                        obj.__dict__[key] = value

                    self.__dict__[unit] = obj

            except:
                return "Settings file corrupt"



