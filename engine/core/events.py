from dataclasses import dataclass


@dataclass
class EventTypes:
    INFO = "info"


class EngineEvent:
    def __init__(self, type_: EventTypes, name: str, data={}) -> None:
        self.__type = type_
        self.__name = name
        self.__data = data
    
    def __get_as_dict(self):
        return {
            "type": self.__type,
            "name": self.__name,
            "data": self.__data
        }
        
    def get_as_object(self):
        return type("EventObject", (), self.__get_as_dict())
    
    @property
    def get(self):
        return self.__get_as_dict()

    def __str__(self) -> str:
        return f"type: {self.__type}, name: {self.__name}"


class EngineEvents:
    def __init__(self) -> None:
        self.events: set[EngineEvent] = set()

    def get_events(self):
        for event in self.events:
            yield event.get

    def add_event(self, event):
        self.events.add(event)
        

if __name__ == "__main__":
    event = EngineEvent("Тип", "Название", {"data": "some data"})
    print(event.get["name"])
