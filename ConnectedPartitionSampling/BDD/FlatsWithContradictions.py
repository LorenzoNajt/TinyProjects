# -*- coding: utf-8 -*-
"""
Created on Wed Sep 30 21:51:26 2020

@author: lnajt

An implementation of Kawahara et al. Frontier search algorithm specialized to flats.

Adapted from Kawahara et al.

Notational changes

Kawahara:
    
    i -> layer
    x -> arc_type
    
    
    
A note on the data structures:
    
    node.virtual_components[v][w] is a dictionary that tells you if is connected. (Needs to be maintained as symmetric and transitive closed.)
    to w -- it is only maintained and guaranteed correct for the particular 
    Frontier set that is relevant! The rest is just junk, but allocated in
    memory anyway.

    node.virtual_discomponent[v][w] -- maintains whether v cannot be connected to w. Symmetric, but not transitive. If v~w (connected) and w ~_a u then v ~_a u ... in other words, is propagated by the connected components 

========

Regarding 'the contradictions' : allowing in some edges that violate the
connected/anti_connected relations. Allowing in all contradictions gives 
all subsets -- which has a trivial BDD.

The hope is that one can interpolate between no contradictions and unlimited
contradictions in order to find a BDD from which one can do rejection sampling
to get a uniform partition.

The problem with this is that the current way of identified nodes does not 
seem to collapse nodes that define equal functions -- for instance, if you allow
unlimited contradictions, you end up with more than E nodes...

I'm not sure this is fixable -- the identity nodes remember the anti-connected/
connected data about the Frontier... and allowing some number of contradictions
allows flexibility there, but that flexibility has to be directly incorporated
I think.
"""
import time
import networkx as nx
import copy
from matplotlib import pyplot as plt
import random
import gc
#from memory_profiler import profile
import pickle 
class BDD_node:
    
    def __init__(self, layer, graph, order = 0):
        self.virtual_components = { x : {y : False for y in graph.nodes()} for x in graph.nodes()}
        for x in graph.nodes():
            self.virtual_components[x][x] = True
        self.virtual_discomponent = { x : {y : False for y in graph.nodes()} for x in graph.nodes()}
        self.layer = layer
        self.order = order # for plotting
        self.graph = graph
        self.arc = {} # stores the two arcs out
        self.number_of_contradictions =  0 # used for the relaxation
        self.current_subgraph = [] ## Just  used for debugging to store the current 
        ## set of edges. Only meaningful when we don't identify identical nodes.
        
def copy_BDD_node(node):
    # copies the things necessary for the BDD algorithm
    new_node = BDD_node(node.layer, node.graph, node.order)
    for x in node.graph.nodes():
        for y in node.graph.nodes():
            new_node.virtual_components[x][y] = node.virtual_components[x][y]
            new_node.virtual_discomponent[x][y] = node.virtual_discomponent[x][y]
    new_node.number_of_contradictions = node.number_of_contradictions
    
    return new_node  

def flats(graph, edge_list):
    
    """
    Parameters
    ----------
    graph : graph
        DESCRIPTION.
    edge_list : list
        DESCRIPTION.
    Returns The BDD
    -------
    None.

    """
    
    
    root = BDD_node("root", graph)

    m = len(edge_list)
    N = [set( [root])]  # change to layer nodes or something
    for i in range(1, m+1):
        N.append( set() )
    # N is an auxiliary function that will create track of the layers
    for x in graph.nodes():
        root.virtual_components[x][x] = True
    
    BDD = nx.DiGraph()
    BDD.graph["layers"] = m
    BDD.graph["indexing"] = {}
    BDD.graph["layer_widths"] = {}
    BDD.add_node(root)
    BDD.nodes[root]["display_data"] = 'R'
    BDD.nodes[root]["order"] = 0
    BDD.nodes[root]["layer"] = -1
    BDD.graph["indexing"][(-1, 0)] = root
    BDD.graph["layer_widths"][-1] = 1
    for i in [0,1]:
        BDD.add_node(i)
        BDD.nodes[i]["display_data"] = i
        BDD.nodes[i]["order"] = i
        BDD.nodes[i]["layer"] = m-1
        BDD.graph["indexing"][(m-1,i)] = i
    BDD.graph["layer_widths"][m-1] = 2
    
    ## Create Frontier Sets
    frontiers = [] 
    for i in range(m+1):
        left_subgraph = graph.edge_subgraph(edge_list[:i])
        right_subgraph = graph.edge_subgraph(edge_list[i:])
        frontier_set = set ( left_subgraph.nodes() ).intersection( set( right_subgraph.nodes()))
        frontiers.append(frontier_set)
    ##
    for layer in range(m): 
        layer_ref = layer + 1 # just to comport with the reference
        order = 0
        gc.collect()
        for current_node in N[layer]:
            for arc_type in [0,1]: # choice of whether or not to include the edge
                node_new = make_new_node(current_node, edge_list, frontiers, layer_ref, arc_type) # returns a new node or a 0/1-terminal
                if not ( node_new == 1) and not ( node_new == 0):
                    found_duplicate = False
                    for node_other in N[layer+1]:
                        if identical(node_new, node_other, frontiers[layer_ref], graph):
                            del node_new
                            
                            node_new = node_other
                            found_duplicate = True
                            BDD.add_edge(current_node, node_new)


                    if found_duplicate == False:
                        N[layer+1].add( node_new) # add node to ith layer
                        BDD.add_node(node_new) # add the new node to BDD
                        
                        BDD.nodes[node_new]["display_data"] = BDD.nodes[current_node]["display_data"]+ str(arc_type)
                        BDD.nodes[node_new]["order"] = order
                        order += 1
                        BDD.nodes[node_new]["layer"] = layer
                        BDD.graph["indexing"][ ( layer, order - 1)] = node_new
                        BDD.add_edge(current_node, node_new)
                if node_new == 1 or node_new == 0:
                    BDD.add_edge(current_node, node_new)
                current_node.arc[arc_type] = node_new #set the x pointer of node to node_new

        if layer != m - 1:
            BDD.graph["layer_widths"][layer] = order
    return BDD

def make_new_node(current_node, edge_list, frontiers, layer_ref, arc_type, contradiction_limit = 1):
    """
    Parameters
    ----------
    current_node : TYPE
        DESCRIPTION.
    edge_list : TYPE
        DESCRIPTION.
    frontiers : set
        the list of frontier sets
    layer : number
        the current layer
    arc_type : TYPE
        DESCRIPTION.

    Returns
    -------
    This populates the new nodes info, nand does checks to see if it should 
    return 0 or 1 instead.

    """
    edge = edge_list[layer_ref - 1]
    
    v = edge[0]
    w = edge[1]
    
    '''
    if arc_type == 0:
        if current_node.virtual_components[v][w] == True:
            # v and w are connected, so must have
            # the edge between them.
            return 0

    if arc_type == 1:
        if current_node.virtual_discomponent[v][w] == True:
            # v and w are not connected, so adding
            # an edge between them would be a contradiction
            return 0
    '''
    
    current_node_copy = copy_BDD_node(current_node)
    update_node_info(current_node_copy, edge_list, frontiers, layer_ref, arc_type)
    
    if current_node_copy.virtual_discomponent[v][w] == True and current_node_copy.virtual_components[v][w] == True:
        current_node_copy.number_of_contradictions += 1
    
    if current_node_copy.number_of_contradictions > contradiction_limit:
        return 0
    
    if layer_ref - 1== len(edge_list) - 1:
    # this was the last edge, and we found no contradictions
        return 1
    
    return current_node_copy



def update_node_info(node, edge_list, frontiers, layer_ref, arc_type):
    """
    

    Parameters
    ----------
    node : TYPE
        DESCRIPTION.
    edge_list : TYPE
        DESCRIPTION.
    frontiers : TYPE
        DESCRIPTION.
    layer_ref : TYPE
        DESCRIPTION.
    arc_type : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    
    edge = edge_list[layer_ref - 1]
    v = edge[0]
    w = edge[1]

    if arc_type == 0:
        
        
        for m,n in [(v,w), (w,v)]:
        
            component_m = [ t  for t in node.virtual_components.keys() if node.virtual_components[m][t] == True]
            component_n = [ t  for t in node.virtual_components.keys() if node.virtual_components[n][t] == True]
            for x in component_m:
                for y in component_n:
                    node.virtual_discomponent[x][y] = True
                    node.virtual_discomponent[y][x] = True
            
        
    if arc_type == 1:
        node.current_subgraph.append(edge)
        
        
        


        # Extending Connectivity:
        
        merge_set = dict({})
        v_component = node.virtual_components[v]
        w_component = node.virtual_components[w]            
        for x in node.virtual_components.keys():
            merge_set[x] =  v_component[x] or w_component[x]
            
        for t in node.virtual_components.keys():
            node.virtual_components[v][t] = merge_set[t]
            node.virtual_components[w][t] = merge_set[t]

        ## Symmetrize
        for t in node.virtual_components.keys():
            for u in node.virtual_components.keys():
                if node.virtual_components[u][t] == True:
                    node.virtual_components[t][u] = True
    
    
        ## Now take the transitive closure!
        merged_component = [ t  for t in node.virtual_components.keys() if node.virtual_components[v][t] == True]
        
        for x in merged_component:
            for y in merged_component:
                node.virtual_components[x][y] = True
        
        
        
        ## Now use the extended connectivity to update the anti-connectedness.
        
        for t in node.virtual_components.keys():
            anti_connected = False
            for x in merged_component:
                if node.virtual_discomponent[t][x] == True or node.virtual_discomponent[x][t] == True:
                    # need to make sure it is symmetric
                    anti_connected = True
            if anti_connected == True:
                for x in merged_component:
                    node.virtual_discomponent[t][x] = True
                    node.virtual_discomponent[x][t] = True
        
    return 

def identical(node_1, node_2, frontier, graph):
    """
   
    Parameters
    ----------
    node_1 : BDD node
        DESCRIPTION.
    node_2 : BDD node
        DESCRIPTION.
    frontier : TYPE
        DESCRIPTION.

    Returns a boolean
    -------
    Returns True if R(node_1) == R(node_2), where
R(n) is the set of edges sets corresponding to paths from n to 1. 

    """
    # frontier= graph.nodes() # Just for debugging

    for vertex_1 in frontier:
        for vertex_2 in frontier:

            if node_1.virtual_components[vertex_1][vertex_2] != node_2.virtual_components[vertex_1][vertex_2]:
                return False
            if node_1.virtual_discomponent[vertex_1][vertex_2] != node_2.virtual_discomponent[vertex_1][vertex_2]:
                return False
    if node_1.number_of_contradictions != node_2.number_of_contradictions:
        return False
    return True

def count_accepting_paths(BDD):
    """
    Parameters
    ----------
    BDD : BDD Object
        The BDD encoding the function in question

    Returns
    -------
    integer
        Number of paths from root to 1. The number of elements in the set system
        defined by the BDD.

    """
    BDD.nodes[0]["count"] = 0
    BDD.nodes[1]["count"] = 1
    m = BDD.graph["layers"]
    for i in range(m-2, -2,-1):
        for j in range(BDD.graph["layer_widths"][i]):
            current_node = BDD.graph["indexing"][(i,j)]
            left_child = current_node.arc[0]
            right_child = current_node.arc[1]
            BDD.nodes[current_node]["count"] = BDD.nodes[left_child]["count"]  + BDD.nodes[right_child]["count"] 
        
    return BDD.nodes[BDD.graph["indexing"][(-1, 0)]]["count"]


def enumerate_accepting_paths(BDD):
    """
    

    Parameters
    ----------
    BDD : TYPE
        DESCRIPTION.

    Returns
    -------
    list
        returns the list of succesful paths.

    """

    BDD.nodes[0]["set"] = set()
    BDD.nodes[1]["set"] = set(['T'])
    m = BDD.graph["layers"]
    for i in range(m-2, -2,-1):
        for j in range(BDD.graph["layer_widths"][i]):
            current_node = BDD.graph["indexing"][(i,j)]
            left_child = current_node.arc[0]
            right_child = current_node.arc[1]
            BDD.nodes[current_node]["set"] = set()
            for c in [0,1]:
                child = [left_child, right_child][c]
                for x in BDD.nodes[child]["set"]:
                    BDD.nodes[current_node]["set"].add( str(c) + x)
    
    return BDD.nodes[BDD.graph["indexing"][(-1, 0)]]["set"]

for scale in range(1,6):
    left_dim = scale
    right_dim = scale
    
    dimensions = [left_dim, right_dim]
    #dimensions = [2,2,2]
    print("working on: ", dimensions)
    graph = nx.grid_graph(dimensions)

    edge_list = list( graph.edges())
    
    # random.shuffle(edge_list)
    # A random order is *much* worse!
    
    m = len(edge_list)
    

    
    BDD = flats(graph, edge_list)
    
    display_labels = { x : BDD.nodes[x]["display_data"] for x in BDD.nodes()}
    
    display_coordinates = { x : (BDD.nodes[x]["order"]*1000 ,m - BDD.nodes[x]["layer"]) for x in BDD.nodes()}
    
    display_coordinates[0] = ( .3,m - BDD.nodes[0]["layer"] )
    display_coordinates[1] = ( .6,m - BDD.nodes[0]["layer"] )
    
    #("dimensions: ", dimensions)
    print("size of BDD", len(BDD))
    print("number of flats", count_accepting_paths(BDD))    

    BDD_name = str(dimensions) + ".p"       

    #pickle.dump( BDD, open( BDD_name, "wb"))
    #del BDD
    gc.collect()
