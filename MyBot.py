#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from hlt.positionals import Direction
import random
import logging

game = hlt.Game()

#object used for deciding what ships get to move. Makes up the nodes of a graph
class Node(object):

    def __init__(self, ship, move):
        self.ship = ship
        self.move = move
        self.dest = game_map.normalize(ship.position.directional_offset(move))
        self.dependent_on = None
        self.dependants = [] #list of nodes that are dependent on this node moving
        self.anti_dependants = [] # list of nodes that are dependent on this node NOT moving, ie. they have the same dest
        self.moved = False
    
    def __hash__(self):
        return hash((self.ship.id, self.move))

    def make_depenendent_on(self, other):
        self.dependent_on = other
        other.dependants.append(self)

    def make_anti_dependant(self, other):
        self.anti_dependants.append(other)
        other.anti_dependants.append(self)

    # returns the length of the largest chain of ships dependent on this node moving
    def dependant_chain_length(self):
        if len(self.dependants) == 0:
            return 0
        return max(elem.dependant_chain_length() for elem in self.dependants) + 1 # recursion

# dict that returns infinity when a key that does not exist is accessed
class Score_Dict(dict):

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return float('inf')

# dict that returns None when a key that does not exist is accessed
class Came_From_Dict(dict):
    
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return None

# dict that won't throw an error on popping a key that doesn't exist
class Better_Dict(dict):
    
    def pop(self, key):
        try:
            dict.pop(self, key)
        except KeyError:
            pass


# thot stands for "total halite on tiles". It helps me determine max_ships
thot = 0
for x in range(game.game_map.width):
    for y in range(game.game_map.height):
        cell = game.game_map[hlt.Position(x, y)]
        thot += cell.halite_amount

avg_hal = thot/(game.game_map.width*game.game_map.height)

game.ready("yeet_bot")
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))


ship_status = Better_Dict()
ship_dest = Better_Dict()
paths = Better_Dict()
search_count = {}

stop_collection = constants.MAX_HALITE / 20 # ships stop collecting when tile.halite_amouont gets below this
dont_consider = constants.MAX_HALITE / 15 # ships don't consider a cell as a worth destination if it doesnt have this much halite
endgame_point = game.game_map.width * 0.8 # start heading home when there are this many moves remaining
#radius_cap = 65 # don't look at tiles farther away than this
expand_factor = 0.5 # ratio of the map width that a ship will search for a dest
not_done = 0.68 # percent full a ship has to be in order to go to the shipyard
end_game_not_done = 0.9 # percent full a ship has to be in order to go to the shipyard in the late game
second_search_radius = 12 # distance a ship will look for a new destination if its not at the shipyard
stop_spawn_point = -1.5625*game.game_map.width + 290 # don't spawn any more ships with this many turns remaining
max_ships = ((avg_hal+200)/2) * (((game.game_map.width + 48) / 2) / ((len(game.players)+2)/2)) * 0.012057 #max number of ships

endgame_time = False # boolean for if it is time for ships to crash at the shipyard

    
#helper function for deciding which bots get to move, returns size of the cycle, zero if no cycle
def cycle_size(node):
    logging.info(node.ship.id)
    curr = node
    seen = set()
    i = 0
    while True:
        if type(curr.dependent_on) != type(curr):
            return 0
        if curr.moved == True:
            return 0
        if curr.dependent_on is node:
            return i+1
        if curr in seen:
            return 0
        seen.add(curr)
        curr = curr.dependent_on
        i += 1

#returns a shuffled list. Does not shuffle the list in place like random.shuffle
def shuf(original):
    return random.sample(original, len(original))

#returns true if the space is occupied by an enemy or a freindly ship that is collecting
def occupied_by_immovable(pos):
    cell = game_map[pos]
    if not cell.is_occupied:
        return False
    if not me.has_ship(cell.ship.id):
        return True
    if cell.ship.id in ship_status:
        if not ship_status[cell.ship.id] == 'collecting':
            return False
        else:
            return True
    return False

def aStar(source, target, exp = True):
    if occupied_by_immovable(target):
        return None # A* doesn't work if the target is occupied by an immovable, so it just gives up to save time
    closedSet = set()
    openSet = set()
    openSet.add(source)
    cameFrom = Came_From_Dict()
    gScore = Score_Dict()
    gScore[source] = 0
    fScore = Score_Dict()
    fScore[source] = game_map.calculate_distance(source, target)
    
    
    while len(openSet) > 0:
        curr = None
        for elem in openSet:
            if curr is None or fScore[elem] < fScore[curr]:
                curr = elem
        
        if curr == target:
            return path(cameFrom, curr)
            
        openSet.remove(curr)
        closedSet.add(curr)
        
        for card in shuf(Direction.get_all_cardinals()):
            elem = game_map.normalize(curr.directional_offset(card))
            
            if elem in closedSet or occupied_by_immovable(elem):
                continue
            
            
            tentative_gScore = gScore[curr] + 1
                
            if elem not in openSet:
                openSet.add(elem)
            elif tentative_gScore >= gScore[elem]:
                continue
            cameFrom[elem] = curr
            gScore[elem] = tentative_gScore
            fScore[elem] = gScore[elem] + game_map.calculate_distance(elem, target)
            

# helper function for A*
def path(cameFrom, currP):
    totPath = []
    while bool(cameFrom[currP]):
        totPath.insert(0, currP)
        currP = cameFrom[currP]
    return totPath

def able_to_move(ship):
    return ship.halite_amount >= game_map[ship.position].halite_amount/constants.MOVE_COST_RATIO

# exp tells me if this ship is exploring
def get_move(ship, exp = True):
    if able_to_move(ship):

        if paths[ship.id][0] == ship.position: # the zeroth element of the path is the next place a ship wants to go
            paths[ship.id].pop(0)
    
        #troll case - an enemy ship is on my shipyard
        if len(paths[ship.id]) == 1 and paths[ship.id][0] == me.shipyard.position\
        and game_map[me.shipyard.position].is_occupied and not me.has_ship(game_map[me.shipyard.position].ship.id):
            
            move = positional_difference(ship.position, paths[ship.id][0])
            return move
        
        # reconstructing the path if it has become impassable
        if occupied_by_immovable(paths[ship.id][0]):
            for i in range(len(paths[ship.id])): 
                if not occupied_by_immovable(paths[ship.id][i]):
                    break
            temp = aStar(ship.position, paths[ship.id][i], exp)
            if temp is None: 
                return nav(ship, paths[ship.id][-1]) # if A* didn't work, fall back on nav()

            paths[ship.id][0:i+1] = temp
        
        move = positional_difference(ship.position, paths[ship.id][0])
        
        if move is None:
            move = Direction.Still
    else:
        move = Direction.Still
    return move

# returns the direction that will get you from start_pos to end_pos
def positional_difference(start_pos, end_pos):
    out = None
    for card in Direction.get_all_cardinals():
        if game_map.normalize(start_pos.directional_offset(card)) == end_pos:
            out = card
            break
    return out

# helper function for get_dest
    # greatly favors closeness over halite amount
def scoreD(shipPos, cellPos):
    temp = game_map.calculate_distance(shipPos, cellPos)
    temp = temp * temp
    temp = temp * temp #in place of temp^4 b/c slighly faster
    return (game_map[cellPos].halite_amount) - (2*temp)
                    

# searches in a radius around the ship's position for the most appealing destination
def get_dest(shipPos, d = int(game.game_map.width*expand_factor)):
    dest = None
    destScore = float('inf')*-1
    for i in range(1, d): #looking around the ship for a destination
        for j in range(-1*i, i+1):
            for c in range(min(i-j+1, 2)):
                if c == 0:
                    k = i - abs(j)
                else:
                    k = abs(j) - i
                pos = game_map.normalize(shipPos.directional_offset((j, k)))
                if game_map[pos].halite_amount > (dont_consider) and (dest is None or scoreD(shipPos, pos) > destScore)\
                  and pos not in ship_dest.values():
                    dest = pos
                    destScore = scoreD(shipPos, pos)
    return dest


# my own version of naive navigate
    # ret stands for returning
def nav(ship, dest, ret = False):
    ms = shuf(game_map.get_unsafe_moves(ship.position, dest))
    fin = None
    for elem in ms:
        temp_ship = game_map[game_map.normalize(ship.position.directional_offset(elem))].ship
        if temp_ship is None or (me.has_ship(temp_ship.id) and\
          not ship_status[temp_ship.id] == "collecting") or endgame_time :
            fin = elem
            break

    #troll case - enemy on my shipyard
    if fin is None and ret and game_map.calculate_distance(ship.position, me.shipyard.position) == 1:
        return ms[0]

    if fin is None:
        return Direction.Still
    return fin

# returns the distance of my second farthest ship
    # helpful for determining when its time for endgame
def second_farthest_ship_distance():
    best = 0
    out = 0
    for ship in me.get_ships():
        tentative_distance = game_map.calculate_distance(ship.position, me.shipyard.position)
        if tentative_distance > best:
            out = best
            best = tentative_distance
        elif tentative_distance > out:
            out = tentative_distance

    return out

# sets up dependancies and anti-dependacies in the graph
    # a node is dependent on another if the other is currently occupying its destination
    # a node is anti-dependant on another if they both want to go to the same destination
def build_graph(endgame = False):
    for node in nodes:
        if node.move == Direction.Still:
            pass
        elif game_map[node.dest].is_occupied and (node.dest != me.shipyard.position or not endgame):
            for d in nodes:
                if game_map[node.dest].ship.id == d.ship.id:
                    if d.move != Direction.Still:
                        node.make_depenendent_on(d)
                    else:
                        node.dependent_on = 'imp'
                    break
    

    for node in nodes:
        if node.move == Direction.Still and node.moved == False:
            command_queue.append(node.ship.move(node.move))
            node.moved = True

    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            if nodes[i].dest == nodes[j].dest and (nodes[i].dest != me.shipyard.position or not endgame):
                nodes[i].make_anti_dependant(nodes[j])


#topologically sorts the graph
def topo_sort():
    frontier = list() # list b/c set wans't working, but no runtime downside of list
    for node in nodes:
        if node.dependent_on is None and node.moved == False:
            frontier.append(node)

    while len(frontier) > 0:
        node = frontier.pop(0)
        if not (node.dependent_on is None and node.moved == False):
            continue
        
        best = node
        for elem in node.anti_dependants:
            if elem.dependant_chain_length() > best.dependant_chain_length():
                best = elem # decides which anti-dependant should go based on how many bots depend on it moving
        if best.moved == False:
            command_queue.append(best.ship.move(best.move))
            game_map[best.ship.position].mark_unsafe(None)
            game_map[best.dest].mark_unsafe(best.ship)
            best.moved = True

            for dependant in best.dependants:
                dependant.dependent_on = None
                frontier.append(dependant)
        
        for elem in best.anti_dependants:
            if elem.moved == False:
                command_queue.append(elem.ship.move(Direction.Still))
                elem.moved = True
            try:
                frontier.remove(elem)
            except ValueError:
                pass


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

while True:

    # sets new criteria on collection for the rest of the game
    if game.turn_number > 60:
        not_done = end_game_not_done
    
    nodes = []
    game.update_frame()
    me = game.me
    game_map = game.game_map

    command_queue = []
    
    # determines if its endgame time
    if endgame_time == False and constants.MAX_TURNS - game.turn_number <= second_farthest_ship_distance() + 3:
        endgame_time = True

    # removes ships that are no longer with us
    temp = []
    for Id in ship_dest:
        if Id not in [elem.id for elem in me.get_ships()]:
            temp.append(Id) 
    for Id in temp:
        ship_dest.pop(Id)

        
    if endgame_time:
        for ship in me.get_ships():

            if ship.position == me.shipyard.position:
                move = Direction.Still
                nodes.append(Node(ship, move))
            elif game_map.calculate_distance(ship.position, me.shipyard.position) > 1:
                move = nav(ship, me.shipyard.position)
                nodes.append(Node(ship, move))
            else: #kamicaze @ shipyard
                move = positional_difference(ship.position, me.shipyard.position)
                if move is None:
                    move = Direction.Still
                nodes.append(Node(ship, move))


        build_graph(True) # "True" b/c its endgame time
        
        topo_sort()

        game.end_turn(command_queue)

        continue
        
    for ship in me.get_ships():
        if ship.position == me.shipyard.position:
            ship_status[ship.id] = "exploring" # default value is "exploring"
            if ship.id in paths:
                paths.pop(ship.id)
            
        if ship.id not in ship_status:
            ship_status[ship.id] = "exploring"
        
            
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~            

        if ship_status[ship.id] == "exploring":
            if ship.id not in ship_dest:
                ship_dest[ship.id] = get_dest(ship.position)
                while ship_dest[ship.id] is None:
                    ship_dest.pop(ship.id)
                    stop_collection /= 2 # lowers the bar if no destinations fit the bill
                    dont_consider /= 2
                    ship_dest[ship.id] = get_dest(ship.position)
            if ship.position == ship_dest[ship.id]:
                ship_status[ship.id] = "collecting"
                paths.pop(ship.id)
            else:
                move = None
                if ship.id not in paths:
                    pat = aStar(ship.position, ship_dest[ship.id])
                    if pat is not None:
                        paths[ship.id] = pat
                        move = get_move(ship)
                    else: # when A* doesn't work
                        if able_to_move(ship):
                            move = nav(ship, ship_dest[ship.id])
                        else:
                            move = Direction.Still
                if move is None:
                    move = get_move(ship)
                    
                d = Node(ship, move)
                nodes.append(d)
                
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~          
        
        if ship_status[ship.id] == "collecting":
            if game_map[ship.position].halite_amount < stop_collection or ship.is_full:
                ship_dest.pop(ship.id)
                if ship.halite_amount < constants.MAX_HALITE* not_done: # ships keep exploring if not very full
                    ship_status[ship.id] = "exploring"
                    ship_dest[ship.id] = get_dest(ship.position, second_search_radius)
                    if ship_dest[ship.id] is None:
                        ship_status[ship.id] = "returning" # if no destinations fit the bill, ship heads home
                        ship_dest.pop(ship.id)
                    else:
                        pat = aStar(ship.position, ship_dest[ship.id])
                        if pat is not None:
                            paths[ship.id] = pat
                            move = get_move(ship)
                        else: # when A* doesn't work
                            paths.pop(ship.id)
                            if able_to_move(ship):
                                move = nav(ship, ship_dest[ship.id])
                            else:
                                move = Direction.Still

                        d = Node(ship, move)
                        nodes.append(d)
                else:
                    ship_status[ship.id] = "returning"

            else:
                d = Node(ship, Direction.Still)
                nodes.append(d)
                    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        if ship_status[ship.id] == "returning":
            move = None
            if ship.id not in paths:
                pat = aStar(ship.position, me.shipyard.position, False)
                if pat is not None:
                    paths[ship.id] = pat
                    move = get_move(ship, False)
                else: # when A* doesn't work
                    if able_to_move(ship):
                        move = nav(ship, me.shipyard.position, True)
                    else:
                        move = Direction.Still
            if move is None:
                move = get_move(ship, False)
            
            d = Node(ship, move)
            nodes.append(d)

    
    build_graph()
    
    topo_sort()

    # this loop deals with all of the cycles in the graph, including swapping b/c swapping is a cylce
    for node in nodes:
        if cycle_size(node) > 0:
            curr = node
            for _ in range(cycle_size(node)):
                if curr.moved == False:
                    command_queue.append(curr.ship.move(curr.move))
                    curr.moved = True
                    curr = curr.dependent_on


    if ((game.turn_number <= constants.MAX_TURNS - stop_spawn_point) and len(me.get_ships()) < max_ships)\
        and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied :
        command_queue.append(me.shipyard.spawn())

    game.end_turn(command_queue)
