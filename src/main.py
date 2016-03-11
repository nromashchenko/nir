import itertools
import random
from collections import Counter

import iof
from metrics import jaccard, JSD
from subsampling import *

#import scipy
#from scipy import stats

def kmer_generator(string, k):
    kmer = string[:k]

    for i in range(len(string) - k):
        kmer = kmer[1:] + string[i + k]
        yield kmer


def hasher(string_set, k):
    table = {}
    for string in string_set:
        for kmer in kmer_generator(string, k):
            if kmer in table:
                table[kmer] = table[kmer] + 1
            else:
                table[kmer] = 1

    return table


def distance_matrix(data, k, jk_size, distance):
    tables = {}
    [tables.update({sample: hasher(data[sample], k)}) for sample in data.keys()]

    result = [tables.keys()]
    for key1 in tables:
        table1 = tables[key1].copy()
        values = [distance(table1, tables[key2].copy()) for key2 in tables]
        result.append([key1] + values)

    return result


def jackknifed_distance(table1, table2, subset_size):
    values = [jaccard(set(x), set(y)) for x, y in zipped_jackknife(table1, table2, subset_size)]
    print(str(scipy.stats.bayes_mvs(values)))


if __name__ == "__main__":
    
    from time import time
    start = time()

    random.seed(42)
    k = 200
    jackknife_subset_size = 1000
    filename = 'data/seqs.fna'
    data = iof.read_fasta(filename)
    #dmatrix = distance_matrix(data, k, jackknife_subset_size, JSD)
    dmatrix = distance_matrix(data, k, jackknife_subset_size, jaccard)
    iof.write_distance_matrix(dmatrix, 'jaccard_matrix.txt')
    #iof.write_distance_matrix(dmatrix, 'jsd_matrix.txt')

    #table1 = {1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7}
    #print('\n'.join(str(t) for t in jackknifed(table1, 2)))
    #table2 = {2:2, 5:5, 4:4, 7:7, 6:6, 3:3}
    #print('\n'.join(str(x) for x in jackknifed(table1, 2)))
    #print(JSD(table1, table2))

    end = time()
    print("Time: " + str(end - start))

