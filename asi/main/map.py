import pygame

from typing import Any, Tuple
from colorama import Fore, Style
import json
import pickle

from engine.core import EngineSettings

from asi import settings
from .sprites.player.player import PlayerSprite
from .sprites.environment.obstacle import Obstacle
from .sprites.environment.decoration import DecorationSprite
from .sprites.player.storage import Storage
from .sprites.npc.trader import Trader
from .sprites.enemy.kamikaze import Kamikaze
from .sprites.enemy.gunner import Gunner
from .sprites.environment.board import BoardSprite
from .sprites.player.HEAL import Heal
from .sprites.enemy.spike import Spike
from .sprites.enemy.boss import Boss
from .sprites.environment.trigger import Trigger
from .sprites.environment.door import Door


def load_level(filename):  # загрузка уровня
    filename = r"asi/main/resources/map/" + filename

    with open(filename, "r") as mapFile:
        level_map = [line for line in mapFile]

    max_width = max(map(len, level_map))

    return list(map(lambda x: list(x.ljust(max_width, ".")), level_map))  # возвращаем список списков карты


class Map:
    ENTITY_SYMBOL_DECODER = {
        "$": Storage,
        "t": Trader,
        "k": Kamikaze,
        "g": Gunner,
        "h": Heal,
        "s": Spike,
        "B": BoardSprite,
        "b": Boss,
        "*": Trigger,
        "z": Door
    }
    NO_UPDATE_SYMBOL_DECODER = {
        "#": Obstacle,
        "-": Obstacle,
    }
    DECORATION_SYMBOL_DECODER = {
        "G": {
            "image_path": "map/grass-1.png",
            "size": (50, 20)
        },
        "T": {
            "image_path": "map/tree-1.png",
            "size": (200, 200)
        },
    }

    def __init__(self, scene, surface):
        self.__update_sprite_group = pygame.sprite.Group()
        self.__no_update_sprite_group = pygame.sprite.Group()
        self.__player_sprite_group = pygame.sprite.Group()
        self.__scene = scene
        self.__surface = surface
        
        self.__player_render = EngineSettings.get_var("RENDER_DISTANCE")

        self.__background_image = pygame.image.load("asi/main/resources/background.png")

        self.block_size = 50
        self.map: list[list[Any]]
        self.map_symbol: list[list[str]]
        self.map_status: list[list[Any]]
    
    def create_map_2(self, level_map):
        self.start_player_pos = self.__preload_player(level_map)
        
        self.map_size_x = len(max(level_map, key=lambda x: len(x[0])))
        self.map_size_y = len(level_map)
        
        self.__background_size = [
            max(self.map_size_x * self.block_size, settings.HEIGHT),
            max(self.map_size_y * self.block_size, settings.WIDTH)
        ]
        self.__background_pos = [0, 0]
        self.__background_image = pygame.transform.scale(self.__background_image, self.__background_size)
        
        self.map = [[None for x in range(self.map_size_x)] for y in range(self.map_size_y)]
        self.map_status = [[False for x in range(self.map_size_x)] for y in range(self.map_size_y)]
        self.map_symbol = [[" " for x in range(self.map_size_x)] for y in range(self.map_size_y)]
        
        f = False
        
        for y in range(len(level_map)):
            for x in range(len(level_map[y])):
                symbol = level_map[y][x]
                
                if symbol in Map.NO_UPDATE_SYMBOL_DECODER:
                    sprite = self.__scene.load_sprite(
                        Map.NO_UPDATE_SYMBOL_DECODER[symbol],
                        coords=[
                            self.block_size * x,
                            self.block_size * y
                        ]
                    )
                    self.map[y][x] = sprite
                    
                    self.map_symbol[y][x] = symbol
                    
                    if not f:
                        self.t = sprite
                        f = True
                
                if symbol in Map.ENTITY_SYMBOL_DECODER:
                    sprite = self.__scene.load_sprite(
                        Map.ENTITY_SYMBOL_DECODER[symbol],
                        coords=[
                            self.block_size * x,
                            self.block_size * y
                        ]
                    )
                    self.map[y][x] = sprite

                    self.map_symbol[y][x] = symbol
                
                if symbol in Map.DECORATION_SYMBOL_DECODER:
                    sprite = self.__scene.load_sprite(
                        DecorationSprite,
                        coords=[
                            self.block_size * x + self.block_size - Map.DECORATION_SYMBOL_DECODER[symbol]["size"][0],
                            self.block_size * y + self.block_size - Map.DECORATION_SYMBOL_DECODER[symbol]["size"][1]
                        ],
                        **Map.DECORATION_SYMBOL_DECODER[symbol]
                    )
                    self.map[y][x] = sprite
                    
                    self.map_symbol[y][x] = symbol
                    

        self.player = self.__scene.load_sprite(
            PlayerSprite,
            coords=[
                self.block_size * self.start_player_pos[0],
                self.block_size * self.start_player_pos[1]
            ]
        )
        self.__scene.player = self.player
        self.start_player_pos = [0, 0]
        self.__last_player_pos = self.get_payer_map_pos()
        # self.__update_sprite_group.add(self.player)
        
        self.__player_sprite_group.add(self.player)
        
        self.__scene._game_stack.sprite_group.update()
        
        player_pos = self.get_payer_map_pos()
        
        for y in range(
            max(player_pos[1] - self.__player_render[1], 0),
            min(player_pos[1] + self.__player_render[1], self.map_size_y)
        ):
            for x in range(
                max(player_pos[0] - self.__player_render[0], 0),
                min(player_pos[0] + self.__player_render[0], self.map_size_x)
            ):
                self.map_status[y][x] = True

                if self.map[y][x] and self.map_symbol[y][x] not in Map.NO_UPDATE_SYMBOL_DECODER:
                    self.__update_sprite_group.add(
                        self.map[y][x]
                    )

                if self.map[y][x] and self.map_symbol[y][x] in Map.NO_UPDATE_SYMBOL_DECODER:
                    self.__no_update_sprite_group.add(
                        self.map[y][x]
                    )
                    
    def get_payer_map_pos(self):
        return [
            int(self.start_player_pos[0] + self.player.rect.center[0] // self.block_size),
            int(self.start_player_pos[1] + self.player.rect.center[1] // self.block_size)
        ]
    
    def in_render_zone(self, player_pos, coords: Tuple[int, int]):
        return (
            player_pos[0] - self.__player_render[0] <= coords[0] <= player_pos[0] + self.__player_render[0] and
            player_pos[1] - self.__player_render[1] <= coords[1] <= player_pos[1] + self.__player_render[1]
        )
    
    def draw_debug_map(self):
        for y in range(self.map_size_y):
                for x in range(self.map_size_x):
                    if self.map_status[y][x]:
                        color = Fore.GREEN
                    else:
                        color = Fore.RED
                        
                    print(self.map_symbol[y][x] + color, end=" ")
                print()
            
        print(Style.RESET_ALL)

    def draw_background(self):
        self.__background_image = pygame.transform.scale(self.__background_image, (
            max(self.map_size_x * self.block_size, settings.HEIGHT),
            max(self.map_size_y * self.block_size, settings.WIDTH))
        )

        self.__surface.blit(self.__background_image, (min(self.t.rect.x, 0), min(self.t.rect.y, 0)))

    def update(self):
        player_pos = self.get_payer_map_pos()


        if self.__player_render != EngineSettings.get_var("RENDER_DISTANCE"):
            self.__player_render = EngineSettings.get_var("RENDER_DISTANCE")

            self.__update_sprite_group.empty()
            self.__no_update_sprite_group.empty()
            
            self.__player_sprite_group.add(self.player)
            
            for y in range(len(self.map_status)):
                for x in range(len(self.map_status[y])):
                    self.map_status[y][x] = False

            for y in range(
                max(player_pos[1] - self.__player_render[1], 0),
                min(player_pos[1] + self.__player_render[1], self.map_size_y)
            ):
                for x in range(
                    max(player_pos[0] - self.__player_render[0], 0),
                    min(player_pos[0] + self.__player_render[0], self.map_size_x)
                ):
                    self.map_status[y][x] = True

                    if self.in_render_zone(player_pos, (x, y)) and self.map_symbol[y][x] not in Map.NO_UPDATE_SYMBOL_DECODER:
                        if self.map[y][x] and self.map[y][x] in self.__scene.sprite_group:
                            self.__update_sprite_group.add(
                                self.map[y][x]
                            )
                    
                    if self.in_render_zone(player_pos, (x, y)) and self.map_symbol[y][x] in Map.NO_UPDATE_SYMBOL_DECODER:
                        if self.map[y][x] and self.map[y][x] in self.__scene.sprite_group:
                            self.__no_update_sprite_group.add(
                                self.map[y][x]
                            )
            
            self.__surface.fill(pygame.Color("#3C2A21"))
            self.__no_update_sprite_group.draw(self.__surface)
            self.__update_sprite_group.draw(self.__surface)


        if self.__last_player_pos != player_pos:
            player_shift = [
                player_pos[0] - self.__last_player_pos[0],
                player_pos[1] - self.__last_player_pos[1]
            ]

            
            old_left_x_render = self.__last_player_pos[0] + self.__player_render[0]
            old_right_x_render = self.__last_player_pos[0] - self.__player_render[0]
            
            new_left_x_render = self.__last_player_pos[0] + player_shift[0] + self.__player_render[0]
            new_right_x_render = self.__last_player_pos[0] + player_shift[0] - self.__player_render[0]
            
            min_left_x_render, max_left_x_render = min(old_left_x_render, new_left_x_render), max(old_left_x_render, new_left_x_render)
            min_right_x_render, max_right_x_render = min(old_right_x_render, new_right_x_render), max(old_right_x_render, new_right_x_render)
    
            for y in range(
                max(min(
                        player_pos[1],
                        self.__last_player_pos[1]
                    ) - self.__player_render[1], 0),
                min(max(
                    player_pos[1],
                    self.__last_player_pos[1]
                    )+ self.__player_render[1] + 1, self.map_size_y)
                ):
                for x in (*range(max(min_left_x_render, 0), min(max_left_x_render + 1, self.map_size_x)), *range(max(min_right_x_render, 0), min(max_right_x_render + 1, self.map_size_x))):
                    if self.in_render_zone(player_pos, (x, y)) and not self.map_status[y][x] and self.map_symbol[y][x] not in Map.NO_UPDATE_SYMBOL_DECODER:
                        if self.map[y][x] and self.map[y][x] in self.__scene.sprite_group:
                            self.__update_sprite_group.add(
                                self.map[y][x]
                            )

                        self.map_status[y][x] = True
                    
                    if self.in_render_zone(player_pos, (x, y)) and not self.map_status[y][x] and self.map_symbol[y][x] in Map.NO_UPDATE_SYMBOL_DECODER:
                        if self.map[y][x] and self.map[y][x] in self.__scene.sprite_group:
                            self.__no_update_sprite_group.add(
                                self.map[y][x]
                            )

                        self.map_status[y][x] = True

                    if not self.in_render_zone(player_pos, (x, y)) and self.map_status[y][x]:
                        if self.map_symbol[y][x] in Map.NO_UPDATE_SYMBOL_DECODER:
                            self.__no_update_sprite_group.remove(
                                self.map[y][x]
                            )
                        else:
                            self.__update_sprite_group.remove(
                                self.map[y][x]
                            )
                            
                        self.map_status[y][x] = False


            old_top_y_render = self.__last_player_pos[1] + self.__player_render[1]
            old_bottom_y_render = self.__last_player_pos[1] - self.__player_render[1]
            
            new_top_y_render = self.__last_player_pos[1] + player_shift[1] + self.__player_render[1]
            new_bottom_y_render = self.__last_player_pos[1] + player_shift[1] - self.__player_render[1]
            
            min_top_y_render, max_top_y_render = min(old_top_y_render, new_top_y_render), max(old_top_y_render, new_top_y_render)
            min_bottom_y_render, max_bottom_y_render = min(old_bottom_y_render, new_bottom_y_render), max(old_bottom_y_render, new_bottom_y_render)
            
            for x in range(
                max(min(
                        player_pos[0],
                        self.__last_player_pos[0]
                    ) - self.__player_render[0], 0),
                min(max(
                        player_pos[0],
                        self.__last_player_pos[0]
                    ) + self.__player_render[0] + 1, self.map_size_x)
                ):
                for y in (*range(max(min_top_y_render, 0), min(max_top_y_render + 1, self.map_size_y)), *range(max(min_bottom_y_render, 0), min(max_bottom_y_render + 1, self.map_size_y))):
                    if self.in_render_zone(player_pos, (x, y)) and not self.map_status[y][x] and self.map_symbol[y][x] not in Map.NO_UPDATE_SYMBOL_DECODER:
                        if self.map[y][x] and self.map[y][x] in self.__scene.sprite_group:
                            self.__update_sprite_group.add(
                                self.map[y][x]
                            )

                        self.map_status[y][x] = True

                    if self.in_render_zone(player_pos, (x, y)) and not self.map_status[y][x] and self.map_symbol[y][x] in Map.NO_UPDATE_SYMBOL_DECODER:
                        if self.map[y][x] and self.map[y][x] in self.__scene.sprite_group:
                            self.__no_update_sprite_group.add(
                                self.map[y][x]
                            )

                        self.map_status[y][x] = True

                    if not self.in_render_zone(player_pos, (x, y))  and self.map_status[y][x]:
                        if self.map_symbol[y][x] in Map.NO_UPDATE_SYMBOL_DECODER:
                            self.__no_update_sprite_group.remove(
                                self.map[y][x]
                            )
                        else:
                            self.__update_sprite_group.remove(
                                self.map[y][x]
                            )
                        
                        self.map_status[y][x] = False
                
            self.__last_player_pos = player_pos
                    
        for sprite in self.__update_sprite_group.sprites():
            sprite._update(True)
            
        self.__surface.fill(pygame.Color(EngineSettings.get_var("GAME_BACKGROUND_COLOR")))
        
        if EngineSettings.get_var("DRAW_BACKGROUND"):
            self.draw_background()

        self.__no_update_sprite_group.draw(self.__surface)
        self.__update_sprite_group.draw(self.__surface)
        
        for sprite in self.__player_sprite_group.sprites():
            sprite._update(True)
        
        self.__player_sprite_group.draw(self.__surface)
        
        self.render(self.player.rect.center)

    def __preload_player(self, level_map):
        for y in range(len(level_map)):
            for x in range(len(level_map[y])):
                if level_map[y][x] == "p":
                    return [x, y]

        raise ValueError("Игрок не обнаружен на карте")

    def add_decorataion_sprite(self, coords, data):
        sprite = DecorationSprite(self.__scene, coords=coords, **data)
        self.__env_sprite_group.add(sprite)
        self.__scene._game_stack.sprite_group.add(sprite)
        
        return sprite

    def render(self, player_coords):
        self.__move_map_for_player(player_coords)

    def __move_map_for_player(self, player_coords):
        move_percent = 30
        
        WIDTH, HEIGHT = EngineSettings.get_var("SIZE")

        if (
                WIDTH * move_percent / 100 >= player_coords[0] or
                player_coords[0] >= WIDTH * (100 - move_percent) / 100 or
                HEIGHT * move_percent / 100 >= player_coords[1] or
                player_coords[1] >= HEIGHT * (100 - move_percent) / 100
        ):

            x, y = 0, 0

            if WIDTH * move_percent / 100 >= player_coords[0]:
                x = WIDTH * move_percent / 100 - player_coords[0]
            elif player_coords[0] >= WIDTH * (100 - move_percent) / 100:
                x = WIDTH * (100 - move_percent) / 100 - player_coords[0]

            if HEIGHT * move_percent / 100 >= player_coords[1]:
                y = HEIGHT * move_percent / 100 - player_coords[1]
            elif player_coords[1] >= HEIGHT * (100 - move_percent) / 100:
                y = HEIGHT * (100 - move_percent) / 100 - player_coords[1]

            self.move_map((int(x), int(y)))

    def move_map(self, coords):
        x, y = coords
        self.start_player_pos[0] -= x / self.block_size
        self.start_player_pos[1] -= y / self.block_size

        self.__scene.move_all_sprites((x, y))
        self.__background_pos[0] += x * self.block_size / 10
        self.__background_pos[0] += x * self.block_size

    def save_map_dump(self):
        from .sprites.player.player import PlayerСharacteristics

        data = {
            "map_data": [[None for x in range(len(self.map_symbol[y]))] for y in range(len(self.map_symbol))],
            "player": {},
            "player_characteristics": {key: PlayerСharacteristics.__dict__[key] for key in filter(lambda x: "__" not in x, PlayerСharacteristics.__dict__)},
            "map_variables": {
                "start_player_pos": list(self.start_player_pos)
            }
        }
        
        
        for y in range(len(self.map_symbol)):
            for x in range(len(self.map_symbol[y])):
                if self.map[y][x] not in self.__scene.sprite_group:
                    continue
                
                rect = self.map[y][x].rect
                pre_data = {
                    "rect": {
                        "left": rect.x,
                        "top": rect.y,
                        "width": rect.width,
                        "height": rect.height
                    }
                }

                for key, value in self.map[y][x].__dict__.items():
                    if key in NEED_VARS:
                        pre_data[key] = value
                
                data["map_data"][y][x] = pre_data
                

        rect = self.player.rect

        pre_data = {
            "rect": {
                "left": rect.x,
                "top": rect.y,
                "width": rect.width,
                "height": rect.height
            },
        }

        for key, value in self.player.__dict__.items():
            if key in NEED_VARS:
                pre_data[key] = value
        
        data["player"] = pre_data

        with open("dump.json", "w") as dump_file:
            dump_file.write(json.dumps(data))
    
    def load_map_dump(self, dump_path):
        if "map_symbol" in self.__dict__:
            for y in range(len(self.map_symbol)):
                for x in range(len(self.map_symbol[y])):
                    if self.map[y][x]:
                        self.map[y][x].kill()
            
            self.player.kill()
            
            self.__player_sprite_group.empty()
            self.__update_sprite_group.empty()
            self.__no_update_sprite_group.empty()
            self.__scene.sprite_group.empty()

        self.create_map_2(load_level(EngineSettings.get_var("MAP_NAME")))        
        
        with open(dump_path, "r") as dump_file:
            data = json.loads(dump_file.read())
    
        for y in range(len(self.map_symbol)):
            for x in range(len(self.map_symbol[y])):
                if self.map[y][x] not in self.__scene.sprite_group:
                    continue

                if self.map[y][x] and not data["map_data"][y][x]:
                    self.map[y][x].kill()
                    continue
    
                rect = data["map_data"][y][x]["rect"]
                del data["map_data"][y][x]["rect"]
                
                self.map[y][x].__dict__.update(data["map_data"][y][x])
                
                self.map[y][x].rect.x = rect["left"]
                self.map[y][x].rect.y = rect["top"]


        rect = data["player"]["rect"]
        del data["player"]["rect"]
        
        self.player.__dict__.update(data["player"])

        self.player.rect.x = rect["left"]
        self.player.rect.y = rect["top"]
        
        
        from .sprites.player.player import PlayerСharacteristics
        
        
        for key, value in data["player_characteristics"].items():
            setattr(PlayerСharacteristics, key, value)
            
        for key, value in data["map_variables"].items():
            setattr(self, key, value)
        
        self.player.update_ui()


NEED_VARS = ('width', 'height', "_PlayerSprite__count_heal", "_PlayerSprite__count_big_heal", "health")
