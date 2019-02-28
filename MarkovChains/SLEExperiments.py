# -*- coding: utf-8 -*-
"""
Created on Mon Feb 18 20:47:44 2019

@author: Temporary
"""

#What we'll do is simulate the Markov chain on the intersection with the disc.
#Then we can compute the explicit mapping out fomulas...

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import random
import multiprocessing as mp
import cProfile
import re
import scipy.stats
def dist(v, w):
    return np.linalg.norm(np.array(v) - np.array(w))


def face_contained_in_disc(coord, r):
    # given the center of the 1x1 face, determine if it is contained in the open unit disc.
    for a in [-.5, .5]:
        for b in [-.5, .5]:
            if np.linalg.norm([coord[0] + a, coord[1] + b]) >= r:
                return False
    return True


def edges_of_dual_face(coord):
    # takes in the center of the dual face as an array of coordinates, and returns the 4 edges.
    vertices = []
    for a in [-.5, .5]:
        for b in [-.5, .5]:
            vertices.append( (coord[0]+ a + (coord[1] + b)*1j))
    edges = set([])
    for x in vertices:
        for y in vertices:
            if dist(x,y) == 1:
                edges.add(frozenset([x,y]))
    a = coord[0]
    b = coord[1]
    edges = [((a + .5, b + .5), (a - .5, b+ .5)), ((a - .5, b + .5), (a - .5, b - .5)), ( ( a - .5, b - .5), (a + .5, b - .5)), ( ( a + .5, b - .5), (a + .5 , b + .5)) ]
    int_edges = [tuple([tuple([int(x) for x in a]) for a in e]) for e in edges]

    return vertices, int_edges


def create_disc_graph(r):
    # Creates the graph representing the intersection of $\mathbb{Z}^2$ with a disc of radius r

    grid = nx.grid_graph([4*r, 4*r])
    dual_grid = nx.grid_graph([4*r, 4*r])
    relabels = {}
    for v in grid.nodes():
        grid.node[v]["coord"]= [ v[0]/r - 2, v[1]/r - 2]
        dual_grid.node[v]["coord"] = [ ( v[0]+ .5)/r - 2, (v[1] + .5)/r - 2]
        relabels[v]= str(grid.node[v]["coord"])
    #
    # Actually don't, because it is useful to have integral names
    intersection_nodes = [v for v in grid.nodes() if np.linalg.norm(grid.node[v]["coord"]) < 1]
    intersection_faces = [v for v in dual_grid.nodes() if face_contained_in_disc(dual_grid.node[v]["coord"])]
    # Now this gives exactly the dual verites whose facesare in the unit disc.

    disc_graph = nx.subgraph(grid, intersection_nodes)
    dual_disc_graph = nx.subgraph(dual_grid, intersection_faces)

    # Now we need to add code so that each dualface can report its edges

    disc_graph.graph["dual"] = dual_disc_graph
    minus_one = list(disc_graph.nodes())[0]
    plus_one = list(disc_graph.nodes())[0]
    for v in disc_graph.nodes():
        if dist(disc_graph.node[v]["coord"], [-1,0]) < dist(disc_graph.node[minus_one]["coord"], [-1,0]):
            minus_one = v
        if dist(disc_graph.node[v]["coord"], [1,0]) < dist(disc_graph.node[plus_one]["coord"], [1,0]):
            plus_one = v
    print(disc_graph.node[plus_one]["coord"], disc_graph.node[minus_one]["coord"])
    disc_graph.graph["plus_one"] = plus_one
    disc_graph.graph["minus_one"] = minus_one
    disc_graph.graph["scale"] = r
    # These two are the nearest points on the graph to $-1$ and $+1$.
    return disc_graph


def integral_disc(r):
    # Takes in r (should be an integer, and returns the integral points in the disc of radius r + .5
    grid = nx.grid_graph([4 * r, 4 * r])
    dual_grid = nx.grid_graph([4 * r, 4 * r])
    relabels = {}
    dual_relabels = {}
    for v in grid.nodes():
        grid.node[v]["coord"] = (v[0] - 2*r, v[1] - 2*r)
        dual_grid.node[v]["coord"] = ((v[0] + .5) - 2*r, (v[1] + .5) - 2*r)
        relabels[v] = grid.node[v]["coord"]
        dual_relabels[v] = dual_grid.node[v]["coord"]
    grid = nx.relabel_nodes(grid, relabels)
    dual_grid = nx.relabel_nodes(dual_grid, dual_relabels)
    intersection_nodes = [v for v in grid.nodes() if np.linalg.norm(grid.node[v]["coord"]) < r + .5]
    intersection_faces = [v for v in dual_grid.nodes() if face_contained_in_disc(dual_grid.node[v]["coord"], r + .5)]
    # Now this gives exactly the dual verites whose facesare in the unit disc.

    disc_graph = nx.subgraph(grid, intersection_nodes)
    dual_disc_graph = nx.subgraph(dual_grid, intersection_faces)

    # Now we need to add code so that each dualface can report its edges

    disc_graph.graph["plus_one"] = (r, 0)
    disc_graph.graph["minus_one"] = (-r,0)
    disc_graph.graph["scale"] = r + .5
    # These two are the nearest points on the graph to $-1$ and $+1$.

    # This is a little funny in the integral case... so we set the disc to size r + .5

    for face in dual_disc_graph.nodes():

        vertices, edges = edges_of_dual_face(dual_disc_graph.node[face]["coord"])
        dual_disc_graph.node[face]["vertices"] = set(vertices)
        dual_disc_graph.node[face]["edges"] = edges

    disc_graph.graph["dual"] = dual_disc_graph

    return disc_graph


def viz(T, path):
    k = 20

    for x in T.nodes():
        if x in path:
            T.node[x]["col"] = 0
        else:
            T.node[x]["col"] = 1
    values = [T.node[x]["col"] for x in T.nodes()]

    nx.draw(T, pos=nx.get_node_attributes(T, 'coord'), node_size = 1, width = 2, cmap=plt.get_cmap('jet'),  node_color=values)

def viz_edge(T, edge_path):
    k = 20

    values = [1 - int((x in edge_path) or ((x[1], x[0]) in edge_path)) for x in T.edges()]

    nx.draw(T, pos=nx.get_node_attributes(T, 'coord'), node_size = 1, width = 1, cmap=plt.get_cmap('jet'),  edge_color=values)


def map_up(point, r):
    # This takes the point and scale it down by r + .5 (we are using integral disc for the markov chain)
    # This sends a point to the upperhalf plane via the map $g(z) = i ( 1+ z)/(1 - z)$
    # In this, -1 is sent to 0, and 1 is sent to infinity. So these are the marked points.
    complex_point = (point[0] + point[1]*1j)/(r + .5)
    new_value = 1j * (1 + complex_point)/(1 - complex_point)
    return [new_value.real, new_value.imag]

def test_create_and_map():
    disc = integral_disc(20)
    path = initial_path(disc)
    viz(disc, path)

    for v in disc.nodes():
        disc.node[v]["coord"]=  map_up(disc.node[v]["coord"])

    viz(disc)
    # THere are some serious distortions here!This is going to be an issue probably, b
    # ut maybe we can avoid it by choosing discs that are near to the origin.


def initial_path(disc_graph):
    path = [disc_graph.graph["minus_one"]]
    current = path[0]
    i = 0
    while (current != disc_graph.graph["plus_one"]) and (i <= 3*disc_graph.graph["scale"]):
        new = (current[0] + 1, current[1])
        current = new
        path.append(new)
        i += 1
    return path


def check_self_avoiding(path):
    # Returns true if the path is self avoiding
    i = 0
    length = len(path)
    while i <= length - 1:
        for x in path[i + 1 : length]:
            if x == path[i]:
                return False
        i += 1
    return True

def convert_node_sequence_to_edge(path):
    # For analysis and visualization, it will be better to use the edges
    edge_path = []
    length = len(path)
    for i in range(length - 1):
        edge_path.append((path[i], path[i+1]))
    return edge_path


def try_add_faces(path, vertices, edges):
    # cases depending on the size of the intersection -- a little sloppier but will be faster?
    # Algorithm -- walk down path until interect vertics of the edges...
    # delete the edges from *edges* as you walk down the path,
    # then past in teh remaining edges in the appropriate pace.

    # Note -- on a square  think self avoiding is all we need to check after a proposal,
    # but on a graph with higher degree faces, you will need to check that this swap doesn't disconnect the walk.

    # Disconnects can still happen here... e.g. adding a blcok in the long hallway. But this code takes care of that
    # situation, since that will break self avoiding -- it makes changes to the path as a function fo time
    square = nx.Graph()
    square.add_edges_from(edges)
    length = len(path)

    i = 0
    while path[i] not in vertices:
        i += 1
        if i == length:
            return False
            #return False
            # This is the case when the face is disjoint.
    j = i + 1
    if j >= length:
        # This is the case that i is the endpoint of the path, i.e. that the path touches the face at the end
        return False
    old_path_through_square = set([])
    while ((j < length) and (path[j] in vertices)):
        # It might be ht ecase that exist_node is the last point of the path
        old_path_through_square.add(path[j])
        j += 1

    exit_node = path[j-1]
    if exit_node == path[i]:
        # This is the case of a corner touching
        return False

    new_path = []
    for t in range(i):
        new_path.append(path[t])

    if i == 0:
        # Exception when the block is at the head
        t = -1

    current = path[t+1]
    last = current
    while current != exit_node:
        new_path.append(current)
        neighs = set(square.neighbors(current))
        for x in old_path_through_square:
            if x in neighs:
                neighs.remove(x)
        if last in neighs:
            neighs.remove(last)
        last = current
        if len(neighs) == 0:
            current = exit_node
        else:
            current = list(neighs)[0]
    for m in range(j - 1, length):
        new_path.append(path[m])

    return new_path


def propose_step(disc, path):
    dual = disc.graph["dual"]
    face = random.choice(list(dual.nodes()))

    new_path = try_add_faces(path, dual.node[face]["vertices"], dual.node[face]["edges"])

    while new_path is False:
        face = random.choice(list(dual.nodes()))
        new_path = try_add_faces(path, dual.node[face]["vertices"], dual.node[face]["edges"])
    if check_self_avoiding(new_path):
        path = new_path

    return path

def SLE_step(disc,path):
    mu = 2.63815853
    new_path = propose_step(disc, path)
    if new_path == path:
        return new_path
    coin = random.uniform(0,1)
    if coin < mu**(len(path) - len(new_path)):
        return new_path
    return path

def run_steps(disc, path, steps):
    for i in range(steps):
        try:
            path = SLE_step(disc, path)
        except:
            print("failed")
    return path

def test_run(disc):
    path = initial_path(disc)


    for i in range(10000):
        try:
            path = SLE_step(disc, path)
        except:
            print("failed")
    edge_path = convert_node_sequence_to_edge(path)
    viz_edge(disc, edge_path)

def in_disc(translate, rad, disc, path):
    #Checks if the sampled path is in $x + aD$ in $\mathbb{H}$.
    points = [ map_up(x, disc.graph["scale"]) for x in path]
    for p in points:
        if dist(p, translate) < rad:
            return True
    return False


def make_sample(disc, num_steps, output, x ):

    path = initial_path(disc)
    sample_path = run_steps(disc, path, num_steps)
    output.put((x,sample_path))


def estimate_probabilities(disc, radius, num_samples, num_steps):

    #Todo -- rewrite this to pool processors better, currently will wait on the slowest thread per chunk.

    count = 0
    output = mp.Queue()

    chunks_size = 25
    num_chunks = num_samples / chunks_size

    total_results = []

    for i in range(int(num_chunks) + 1):
        print("on chunk", i)
        processes = [mp.Process(target=make_sample, args=(disc, num_steps, output,x)) for x in range(chunks_size)]
        for p in processes:
            p.start()

        for p in processes:
            p.join()

        results = [output.get() for p in processes]
        total_results += results

    num_samples = len(total_results)

    for sample_path in total_results:
        if in_disc([1,0], radius, disc, sample_path[1]):
            count += 1

    right_prob = count / num_samples

    count = 0
    for sample_path in total_results:
        if in_disc([-1,0], radius, disc, sample_path[1]):
            count += 1

    left_prob = count / num_samples

    return [right_prob, left_prob], total_results


def hyp_test(true, estimate, num_samples):
    stat = np.abs( np.sqrt(num_samples) * ( estimate - true)  / ( np.sqrt( true * ( 1 - true))))
    return scipy.stats.norm.cdf(-1 * stat)

def do_test():

    experimental_results = []
    for r in range(5, 6):
        radius = .818610421572298  # (The radius for the half disc ... this value makes the RV Bernoulii(1/2)
        desired_error = .1
        true_mean = 1 - (1 - radius ** 2) ** (5 / 8)
        true_variance = true_mean*(1 - true_mean)
        var_times_accuracy_sq = true_variance * ( 1 / desired_error)**2
        desired_confidence = .05
        # Want
        num_samples = round(var_times_accuracy_sq / desired_confidence) + 1
        num_samples = 20
        print("need", num_samples)
        num_steps = 1 * (r ** 4)
        num_steps = 100
        disc = integral_disc(r)
        prob, samples = estimate_probabilities(disc, radius, num_samples, num_steps)
        print("for r", r)
        print("correct value",  1-(1-radius**2)**(5/8))
        # https://arxiv.org/pdf/math/0112246.pdf
        print("estimated probabiltiy", prob)
        result_vector = [r, prob, samples]
        experimental_results.append(result_vector)
    print("results:")
    for x in experimental_results:
        print("r: ", x[0], " estimation: ", x[1], "prob of seeing an estimate:",
              hyp_test(true_mean, x[1][0],num_samples))

    # With r = 30, steps = 100,000 got 14/40.
    # With r = 20, ideal radius, desired_error = .05, desired_confidence = .1, and 1001 samples at 20000 steps, got: .3636


def test():
    r = 8
    radius = .818610421572298  # (The radius for the half disc ... this value makes the RV Bernoulii(1/2)
    desired_error = .1
    true_mean = 1 - (1 - radius ** 2) ** (5 / 8)
    true_variance = true_mean*(1 - true_mean)
    var_times_accuracy_sq = true_variance * ( 1 / desired_error)**2
    desired_confidence = .05
    # Want
    num_samples = round(var_times_accuracy_sq / desired_confidence) + 1

    num_samples = 1
    print("need", num_samples)
    num_steps = 10000
    disc = integral_disc(r)
    path = initial_path(disc)
    sample_path = run_steps(disc, path, num_steps)

def profile():
    disc = integral_disc(8)
    path = initial_path(disc)
    p = cProfile.run('run_steps(disc, path, num_steps)')
    cProfile.run('propose_step(disc,path)')
    dual = disc.graph["dual"]
    face = random.choice(list(dual.nodes()))

    cProfile.run('try_add_faces(path, dual.node[face]["vertices"], dual.node[face]["edges"])')
def save(experimental_results):

    with open(str(experimental_results[0][1]), 'w') as f:
        for item in experimental_results:
            f.write("%s\n" % item)

def open_file():
    name = "FirstTrial"
    with open(name) as f:
        content = f.readlines()
    data = [eval(x) for x in content]
    return data

def stats_sanity_check():
    for size in [4000,5000,6000]:
        vals = []
        for i in range(3000):

            flips = scipy.stats.bernoulli.rvs(.45, size = size)
            vals.append(hyp_test(.5, np.mean(flips), size))
        print(np.max(vals))


def top_bot_more(disc, sample_path):

    new_graph = disc.copy()

    for x in sample_path:
        new_graph.remove_node(x)

    components = list(nx.connected_components(new_graph))
    y_values = []
    for comp in components:
        value = 0
        for x in comp:
            value += x[1]
        y_values.append(value)

    if y_values[0] > y_values[1]:
        #Then comp[0] is the top
        if len(components[0]) > len(components[1]):
            return 1
        else:
            return -1

    if y_values[1] > y_values[0]:
        #Them comp[1] is the top
        if len(components[1]) > len(components[0]):
            return 1
        else:
            return -1
    print("the exceptional thing happened")
    return 0

def more_tests():
    #This is just for first data -- beacuse I lost it
    data = open_file()


    for r in [4,5,6,7,8]:
        total_results = []
        radius = .818610421572298  # (The radius for the half disc ... this value makes the RV Bernoulii(1/2)
        disc = integral_disc(r)

        for x in data[r - 4 ][2]:
            try:
                total_results.append(x[1])
            except:
                print(x)

        sample_path = total_results[100]
        #viz_edge(disc, convert_node_sequence_to_edge(sample_path))

        for v in disc.nodes():
            disc.node[v]["coord"] = map_up(disc.node[v]["coord"],r)

        #viz_edge(disc, convert_node_sequence_to_edge(sample_path))

        count = 0
        num_samples = len(total_results)
        for sample_path in total_results:
            if in_disc([1,0], radius, disc, sample_path):
                count += 1

        right_prob = count / len(total_results)

        count = 0
        for sample_path in total_results:
            if in_disc([-1,0], radius, disc, sample_path):
                count += 1



        left_prob = count / len(total_results)

        count = 0
        for sample_path in total_results:
            count += top_bot_more(disc, sample_path)

        top_bot_stat = .5 * (count / len(total_results)) + .5
        #To make it a Bernoulli


        """print("r:", r, "left side estimate", left_prob, "(", 2*hyp_test(.5, left_prob,num_samples), ")",
              "right side estimate", right_prob, "(",
              2*hyp_test(.5, right_prob, num_samples), ")")"""
        print("r:", r, "top_bot", top_bot_stat, "(", 2*hyp_test(.5, top_bot_stat, num_samples), ")")