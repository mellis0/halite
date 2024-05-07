# Intro

This is the code for my halite bot. This is from the 2018 halite challenge. My Halite username is mattatl. For an introduction to the game of Halite and its rules, please see the official Halite webpage.

# Strategy
	My strategy is based on expanding a "dead zone" around my shipyard. By "dead zone", I mean an area where there is very little to no halite. It costs very little halite for my ships to move over this dead zone. The distance of a cell from my shipyard is the most important factor in determining destinations for my ships. In practice, this makes my ships expand the dead zone perimeter on every move. However, on lower halite maps, the ships don't need to expand the dead zone perimeter because the entire map is more or less a dead zone, so they will search for halite farther out earlier in the game. I do not use drop-offs in my strategy because they are very expensive, halite-wise. As for collisions, I will never run into one of my own ships (except for during the endgame). I will never hit a stationary enemy ship, but my ship and an enemy ship might move to the same cell on the same turn and collide with each other. This is better than staying clear of enemy ships because I do not want to willingly give them territory. Plus, if our ships collide, they lose a ship too. 

	My endgame consists of all my ships heading back to my shipyard. The endgame starts three moves before the second farthest ship from my shipyard needs the rest of the game to get back to my shipyard. I consider the second farthest ship so that I am less likely to consider an extreme case. During the endgame, my ships stop for nothing. This means they don't stop for friendly ships that don't have enough halite to move, and they don't stop for enemy ships that are in their way.



	Because of the way the game is set up, I couldn't modify the ship class to give the ships more instance variables, so I had to use dictionaries to keep track of variables pertaining to individual ship objects. This was the right choice for me because it allows me to keep track of data from previous turns. If I had to recalculate all my variables every turn, I would time out.

	I used A* to efficiently calculate the optimal path from a ship to its destination. naive_navigate was not the right choice because it is extremely prone to deadlock. A* is also much better at routing around obstacles. naive_navigate just waits for obstacles to go away.

	I used sets for their constant time "contains" method. This is very useful in functions like A*, which needs to check if a value has been previously evaluated on every iteration.

	I implemented hashing functions for both my "Node" class and the "Position" class in the hlt. The __hash__ function is useful because I can add objects with the __hash__ function to sets and dictionaries. Sets and dictionaries have the benefits I mentioned above.

	I store my paths for my ships as stacks of positions. The position at the zeroth index is the position where a ship will move next, and the last position in the stack is a ship's destination. Whenever a ship moves, its path's zeroth index is popped. This stack prevented me from recalculating every ship's path on every turn, which would have been very expensive time-wise.

	I used a graph to represent the moves my ships wanted to make and what was stopping them from making those moves. This graph let me handle swapping, and it also allowed me to move a ship to a position that another ship was just on. In short, the graph acts as the basis for determining the most efficient set of moves for any given turn.

	I used topological sort to decide which ships get to move during a turn. The ships that depend on nothing get to move, then the ships that depend on them gets to move, and so on. This was a good choice for me because it allows me to maximize the number of ships that move in a single turn.

	I used lists to keep track of elements and their order. This is useful for comparing every element in a list to every other element because I can just exclude indices that have already been processed.
