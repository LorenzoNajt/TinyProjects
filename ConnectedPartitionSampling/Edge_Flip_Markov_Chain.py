# -*- coding: utf-8 -*-
"""
Created on Mon Dec  7 17:41:46 2020

@author: lnajt
"""


import networkx as nx
import copy
import random
import numpy as np
import math
#import mpmath
import time
import matplotlib.pyplot as plt
import gc
from heapq import nsmallest
from scipy import sparse
import scipy as sc
from EnumeratingConnectedPartitions import viz
from numba import jit

@jit
def binom(n, k):
    return math.factorial(n) // math.factorial(k) // math.factorial(n - k)

def update_coloring(graph, edge):
    #Here we add edge to the set of non-cut edges, meaning that the two endpoints are now definately in the same connected compoennt. WE update the coloring to reflect that.
    coloring = graph.graph["coloring"]
    a = coloring[edge[0]]
    b = coloring[edge[1]]
    if a == b:
        return graph
        #If already in the same component, do nothing.
    else:
        #Update the component coloring by the smallest label.
        if a < b:
            for x in graph.nodes():
                if coloring[x] == b:
                    coloring[x] = a
        else:
            for x in graph.nodes():
                if coloring[x] == a:
                    coloring[x] = b
        graph.graph["num_colors"] += -1
    return graph

def component(graph, component_superset, node, edge_subset):
    # Return the set of nodes of graph that are in the same connected component
    # as node , using edges edge_subset. Given color_component as extra information
    # which is a set of nodes containing the component.
    
    known_component =set( [node])
    frontier = set([node])
    component_superset.remove(node)

    while frontier:

        new_frontier = set()
        remaining_nodes = set()
        for z in component_superset:
            connected = False
            for w in frontier:
                if (z,w) in edge_subset or (w,z) in edge_subset:
                    known_component.add(z)
                    new_frontier.add(z)
                    connected = True
            if connected == False:
                remaining_nodes.add(z)
        frontier = new_frontier
        component_superset = remaining_nodes
    return known_component

def coloring_split(graph, non_cut_edges, edge):

    #This removes edge from the coloring -- if that was the bridge between the component of that coloring, it assigns an unused color to one of the components.

    coloring = graph.graph["coloring"]
    a = coloring[edge[0]]
    b = coloring[edge[1]]
    #We know a == b...
    if a != b:
        print("something went wrong!")
        
    color_component = [x for x in graph.nodes() if coloring[x] == a]

    color_subgraph_edge_list = []
    for f in non_cut_edges:
        # Note that edge is not in this set
        if coloring[f[1]] == a:
            color_subgraph_edge_list.append(f)

    b_component = component(graph, color_component, edge[1], color_subgraph_edge_list)


    if edge[0] in b_component:
        #This was the case that e was not a bridge
        return graph

    # Now, in the case that e was a bridge, we need to reassign the colors. 
    # First we find a color not used by the other components.

    possible_colors = set(graph.nodes())
    for used_color in coloring.values():
        if used_color in possible_colors:
            possible_colors.remove(used_color)

    unused_color = list(possible_colors)[0]


    #We let component with edge[0] keep its color, and reassign compoennt with edge[1]
    

    for y in b_component:
        coloring[y] = unused_color
    graph.graph["num_colors"] += 1
    
    graph.graph["coloring"] = coloring
    return graph



def contradictions(graph, cut_edges):

    coloring = graph.graph["coloring"]
    # We use the coloring as a dynamically preprocessed calculation
    # of the span of the set of cut edges.
    
    contradictions = 0
    for e in cut_edges:
        if coloring[e[0]] == coloring[e[1]]:
            contradictions += 1
    
    # Can you just update this dynamically?
    # Well - you need to know all the edges whose status might have flipped.
    # At mixing this is likely very small compared to the total number of edges
    # but doesn't seem like a huge advantage.
            
    
    return contradictions



def step(graph, cut_edges, non_cut_edges, temperature, fugacity):

    coin = random.uniform(0,1)


    if coin < 1/2:
        return non_cut_edges, cut_edges

    # current_contradictions = contradictions(graph, cut_edges)
    current_contradictions = graph.graph["contradictions"]
    # if current_contradictions != contradictions(graph, cut_edges):
    #    print("misalignmnent occurred")
    current_edge_cuts = len(cut_edges)
    current_num_colors = graph.graph["num_colors"]
    # original_cut_edges = copy.copy(cut_edges)
    original_coloring = copy.copy(graph.graph["coloring"])
    original_num_colors = graph.graph["num_colors"]
    e = random.choice(graph.graph["ordered_edges"])

    if e in non_cut_edges:
        add_edge = False
        non_cut_edges.remove(e)
        cut_edges.add(e)
        graph = coloring_split(graph, non_cut_edges, e)
    else:
        add_edge = True
        non_cut_edges.add(e)
        cut_edges.remove(e)
        graph = update_coloring(graph, e)

    new_contradictions = contradictions(graph, cut_edges)
    new_edge_cuts = len(cut_edges)

    coin = random.uniform(0,1)

    if (temperature**(new_contradictions - current_contradictions))* (fugacity**(new_edge_cuts - current_edge_cuts)) <= coin:        
        if add_edge == True:
            non_cut_edges.remove(e)
            cut_edges.add(e)
            # graph = coloring_split(graph, non_cut_edges, e)
        if add_edge == False:
            non_cut_edges.add(e)
            cut_edges.remove(e)
            # graph = update_coloring(graph, e)
            # graph = update_coloring(graph, e)
        graph.graph["coloring"] = original_coloring
        graph.graph["num_colors"] = original_num_colors
        if current_num_colors != graph.graph["num_colors"]:
            print('dif')
            graph.graph["num_colors"] = current_num_colors
        return non_cut_edges, cut_edges
    else:
        graph.graph["contradictions"] = new_contradictions
        # if graph.graph["contradictions"] != contradictions(graph, cut_edges):
        #    print("misalignmnent occurred _ edgeC")
        return non_cut_edges, cut_edges

def is_connected_subgraph(graph, set_of_nodes, node):
    
    size_of_set = len(set_of_nodes)
    known_component =set( [node])
    frontier = set([node])
    component_superset = set_of_nodes
    component_superset.remove(node)

    while frontier:

        new_frontier = set()
        remaining_nodes = set()
        for z in component_superset:
            connected = False
            for w in frontier:
                if z in graph.neighbors(w):
                    known_component.add(z)
                    new_frontier.add(z)
                    connected = True
            if connected == False:
                remaining_nodes.add(z)
        frontier = new_frontier
        component_superset = remaining_nodes
    return len(known_component) == size_of_set


def flip_node(graph, proposed_node, old_color, new_color, non_cut_edges, cut_edges):
    proposed_node_neighbors = graph.neighbors(proposed_node)    
    for z in proposed_node_neighbors:
        if graph.graph["coloring"][z] == old_color:
            if (proposed_node, z) in graph.graph["ordered_edges"]:
                # We want to keep the set of ordered edges the same,
                # so that the edge flip chain works correctly.
                cut_edges.add( (proposed_node,z) )
            elif (z, proposed_node) in graph.graph["ordered_edges"]:
                cut_edges.add( (z,proposed_node) )
            if (proposed_node, z) in non_cut_edges:
                non_cut_edges.remove( (proposed_node, z))
            if (z, proposed_node) in non_cut_edges:
                non_cut_edges.remove( (z, proposed_node))
        if graph.graph["coloring"][z] == new_color:
            if (proposed_node, z) in graph.graph["ordered_edges"]:
                non_cut_edges.add( (proposed_node,z) )
            elif (z, proposed_node) in graph.graph["ordered_edges"]:
                non_cut_edges.add( (z,proposed_node) )
            if (proposed_node, z) in cut_edges:
                cut_edges.remove( (proposed_node, z))
            if (z, proposed_node) in cut_edges:
                cut_edges.remove( (z, proposed_node))
    return non_cut_edges, cut_edges

def potts_step(graph, cut_edges, non_cut_edges, temperature, fugacity):
    '''
    Optimizations:
        
        Use the geometric skips technique:
            1. Calculate set of (node, color) pairs that pass the first
            connectivity test
            2. This should dynamically updatable?
            
    '''
    
    
    proposed_node = random.choice(list(graph.nodes()))
    proposed_color = random.choice(list(graph.nodes()))
    #print(proposed_node, proposed_color)
    old_color = graph.graph["coloring"][proposed_node]
    current_contradictions = graph.graph["contradictions"]
    # current_contradictions =  contradictions(graph, cut_edges)
    current_edge_cuts = len(cut_edges)
    old_num_colors = graph.graph["num_colors"]
    old_num_colors = len( set ( [graph.graph["coloring"][x] for x in graph.nodes()]))
                         
    # If there is a block of proposed_color, it must be adjacent to proposed_node
    
    color_block = set ( [ y for y in graph.nodes() if graph.graph["coloring"][y] == proposed_color])
    if color_block:
        proposed_node_neighbors = graph.neighbors(proposed_node)
        for z in proposed_node_neighbors:
            if z in color_block:
                break
        else:
            # proposal is not a connected partition, so reject.
            return non_cut_edges, cut_edges
        
    # Set color proposal
    
    graph.graph["coloring"][proposed_node] = proposed_color
    
    # Next, check that the old_color block is still connected
    color_block = [ y for y in graph.nodes() if graph.graph["coloring"][y] == old_color]
    
    if color_block != []:
        a_node = color_block[0]
        is_connected = is_connected_subgraph(graph, color_block, a_node)
        if not is_connected:
            # proposal is not connected, so reject 
            graph.graph["coloring"][proposed_node] = old_color
            return non_cut_edges, cut_edges

    # proposal was accepted. Thus far it would give a uniform connected coloring.
    
    
    # Now we move to the Metropolis-Hasting's steps

    # first, update the edge cut sets:
    non_cut_edges, cut_edges = flip_node(graph, proposed_node, old_color, proposed_color, non_cut_edges, cut_edges)
        
    # Update the  number of colors used
    
    # new_num_colors = graph.graph["num_colors"]
    new_num_colors = len( set ( graph.graph["coloring"].values()))
    
    # calculate the parameters and do MH:
    
    new_contradictions = graph.graph["contradictions"] # contradictions(graph, cut_edges)
    # This may be constant ? 
    
    new_edge_cuts = len(cut_edges)

    # Calculate ratio that reweights according to the coloring options
    # We want to weight by f(P) = math.comb(N, num_colors)^{-1}
    
    N = len(graph.nodes())
    old_energy = binom(N, old_num_colors)**(-1)
    new_energy = binom(N, new_num_colors)**(-1)
    coloring_ratio = min(1,  new_energy / old_energy) # old_energy / new_energy #
 
    #
    coin = random.uniform(0,1)
    # print(coloring_ratio)
    #if (temperature**(new_contradictions - current_contradictions))* (fugacity**(new_edge_cuts - current_edge_cuts))*coloring_ratio >= coin:    
    if coin >= coloring_ratio:    
        # Rejection.
        
        #Now reset the changes:
        graph.graph["coloring"][proposed_node] = old_color     
        non_cut_edges, cut_edges  = flip_node(graph, proposed_node, proposed_color, old_color, non_cut_edges, cut_edges)
        return non_cut_edges, cut_edges
    else:
        # acceptance
        graph.graph["contradictions"] = new_contradictions
        return non_cut_edges, cut_edges


def parallel_tempering(graph, steps, temperatures, temperature_weights, fugacities, fugacities_weights):
    graph.graph["ordered_edges"] = list(graph.edges())
    graph.graph["coloring"] = {x : x for x in graph.nodes()}
    graph.graph["num_colors"] = len(graph.nodes())
    cut_edges = set( graph.graph["ordered_edges"])
    non_cut_edges = set([])
    graph.graph["contradictions"] = 0    
    for i in range(10 * len(graph.edges()) * int(math.log( len(graph.edges())))):
        non_cut_edges, cut_edges = step(graph, cut_edges, non_cut_edges, 1, 1)
    
    
    sample = False
    num_found = 0
    contradictions_histogram = {x : 0 for x in range(len(graph.edges()) + 1)}
    
    current_temperature = temperatures[0]
    current_fugacity = fugacities[0]
    
    for i in range(steps):
        
        coin = random.random()
        if coin < .5:
            non_cut_edges, cut_edges = step(graph, cut_edges, non_cut_edges, temperature, fugacity)
            non_cut_edges, cut_edges = potts_step(graph, cut_edges, non_cut_edges, temperature, fugacity)
        else:
            # pick a new temperature and fugacy ... ?
            return
        num_contradictions = graph.graph["contradictions"] 
        contradictions_histogram[num_contradictions] += 1
        if num_contradictions == 0:
            num_found += 1
            sample = [copy.copy(cut_edges),copy.copy(non_cut_edges), copy.copy(graph.graph["coloring"])]

    #plt.bar(list(contradictions_histogram.keys()), contradictions_histogram.values())
    #plt.show()
    print("found this many samples:" , num_found)

@njit
def run_markov_chain(graph, steps = 100, temperature = .5, fugacity = 1, burn_in = False, start_at_min_part = True):
    '''
    Optimizations todo:
        move everything we call out of networkx objects
        e.g. have networkx prepare the adjacency and incidence graphs and incidence dictionary
        then, move the corresponding to calculations to cython optimized code.
    
    '''
    #Return a sample as [Cutedges, non_cutedges, coloring]

    graph.graph["ordered_edges"] = list(graph.edges())
    
    if start_at_min_part == True:
        graph.graph["coloring"] = {} #{x : x for x in graph.nodes()}
        for x in graph.nodes():
            graph.graph["coloring"][x] = x
        graph.graph["num_colors"] = len(graph.nodes())
        cut_edges = set( graph.graph["ordered_edges"])
        non_cut_edges = set([])
    else:
        # Start at max partition
        a_node = list(graph.nodes())[0]
        graph.graph["coloring"] = {x : a_node for x in graph.nodes()}
        graph.graph["num_colors"] = 1
        non_cut_edges = set( graph.graph["ordered_edges"])
        cut_edges = set([])
        #viz(graph, non_cut_edges, graph.graph["coloring"], "init")
    graph.graph["contradictions"] = 0
    
    # cut_edges = set ([x for x in edges if np.random.binomial(1,.5) == 1])
    # non_cut_edges = set ( [ x for x in edges if x not in cut_edges])
    # If you do this you need to update the coloring
    
    if burn_in == True: 
        print ( "burn in for", int(10 * len(graph.edges()) * int(math.log( len(graph.edges())))) )
        for i in range(10 * len(graph.edges()) * int(math.log( len(graph.edges())))):
            non_cut_edges, cut_edges = step(graph, cut_edges, non_cut_edges, 1, 1)
        # A burn in. We should replace this with a step that produces a random 
        # sample and updates the coloroing.
        # Do this to avoid over counting the number of successes from earlier
        # parts of the run.
        print("burn in done")
    
    sample = False
    num_found = 0
    
    contradictions_histogram = {x : 0 for x in range(len(graph.edges()) + 1)}
    
    for i in range(steps):
        non_cut_edges, cut_edges = step(graph, cut_edges, non_cut_edges, temperature, fugacity)
        #non_cut_edges, cut_edges = potts_step(graph, cut_edges, non_cut_edges, temperature, fugacity)
        
        # viz(graph, non_cut_edges, graph.graph["coloring"], "test")
        
        num_contradictions = graph.graph["contradictions"] # contradictions(graph, cut_edges) 
        contradictions_histogram[num_contradictions] += 1
        if num_contradictions == 0:
            num_found += 1
            sample = [copy.copy(cut_edges),copy.copy(non_cut_edges), copy.copy(graph.graph["coloring"])]
            #print(graph.graph["num_colors"])
            #print(len( set(graph.graph["coloring"].values())))
            #print('found one')
    print(contradictions_histogram)
    #plt.bar(list(contradictions_histogram.keys()), contradictions_histogram.values())
    #plt.show()
    print("found this many samples:" , num_found)

    return sample


def test_grid_graph(size = 10, MC_steps = 10000, MC_temperature = .8, fugacities = [1], burn_in = False, start_at_min_part = True):
    print("reminder -- need to understand the potts step on the contradictory ones")

    for fugacity in fugacities:
        graph = nx.grid_graph([size, size])
        print("Running on n = ", str(size), " with numsteps:", MC_steps ," and temperature: " , MC_temperature, "and fugacity: ", 
        str(fugacity))
        sample = run_markov_chain(graph, MC_steps, MC_temperature, fugacity, burn_in, start_at_min_part = start_at_min_part)
        name = "markov_chain_ on n = " + str(size) + "with_fugacity" + str(fugacity) + "temp_" + str(MC_temperature) + "_steps_" +str(MC_steps) +"___"
        #print(name)
        if sample != False:
            viz(graph, sample[1], sample[2], name)
        else:
            print("no sample found")
            
if __name__ == '__main__':

    test_grid_graph(10, 10000, .9, [1], burn_in = False, start_at_min_part = True)

#test_grid_graph(10, 10000, .6, [1], burn_in = True, start_at_min_part = False)