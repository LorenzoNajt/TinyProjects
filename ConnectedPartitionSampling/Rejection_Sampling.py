# -*- coding: utf-8 -*-
"""
Created on Mon Nov 30 05:08:31 2020

@author: lnajt
"""

import networkx as nx
import copy
import random

def rejection_sample(graph):
    J = []
    I = []
    for e in graph.edges():
        c = random.uniform(0,1)
        if c > .5 :
            J.append(e)
        else:
            I.append(e)

    graph.graph["coloring"] = {x : x for x in graph.nodes()}

    for e in J:
        graph = update_coloring(graph, e)

    coloring = graph.graph["coloring"]
    for e in I:
        if coloring[e[0]] == coloring[e[1]]:
            return False
    return [J, coloring]


def test_rejection_sample(graph, goal = 1):

    samples = []
    sample_colors = []
    number = 0

    while number < goal:
        new = rejection_sample(graph)

        if new != False:
            number += 1
            samples.append(new)
            sample_colors.append(graph.graph["coloring"])

    print("Got ", number, " samples")

    return samples

def estimate_ratio(graph, trials = 100000):
    number = 0
    for i in range(trials):
        new = rejection_sample(graph)
        if new != False:
            number += 1
    return number, trials, number/trials


input_graph = nx.grid_graph([3,3,3])
#
sample = test_rejection_sample(input_graph,1)
print(estimate_ratio(input_graph, 10000))