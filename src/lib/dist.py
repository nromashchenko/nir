#!/usr/bin/env python3

from subprocess import call
import os
from Bio import SeqIO
from collections import Counter
from typing import Mapping, List
import functools

from .config import Config
from .iof import make_sure_exists


class SampleMap:
    def __init__(self):
        self.mapping = dict()

    @staticmethod
    def kmerize(config: Config, sample_files: List[str]):
        sample_map = SampleMap()
        sample_map.mapping = dict()
        kmer_size = config.dist.kmer_size

        kmer_output_dir = make_sure_exists(
            os.path.join(config.workon, config.current_index,
                         "kmers." + str(kmer_size))
        )

        sample_map.mapping = kmerize_samples(sample_files,
                                             kmer_output_dir,
                                             kmer_size,
                                             config.temp.njobs)
        return sample_map


    @staticmethod
    def reload(config: Config, labels: List[str]):
        kmers_dir = make_sure_exists(
            os.path.join(config.workon, config.current_index,
                         "kmers." + str(config.dist.kmer_size))
        )
        sample_map = SampleMap()
        for label in labels:
            sample_map.mapping[label] = os.path.join(kmers_dir,
                                                     label + '.counter')

        return sample_map

    def __getitem__(self, sample_name: str) -> str:
        return self.mapping[sample_name]

    def labels(self):
        return self.mapping.keys()

    def paths(self):
        return self.mapping.values()


class LoadApply:
    def __init__(self, func):
        self.func = func

    def __call__(self, x_kmer_file, y_kmer_file):
        xcounter = load_kmer_index(x_kmer_file)
        ycounter = load_kmer_index(y_kmer_file)
        return self.func(xcounter, ycounter)


def jellyfish_count(sample_file: str, kmer_size: int, tables_count: int,
                    hash_size: str, thread_num: int, output_file: str):
    call(["jellyfish", "count",
          "-C",
          "-m", str(kmer_size),
          "-c", str(tables_count),
          "-s", hash_size,
          "-t", str(thread_num),
          "-o", output_file,
          sample_file
          ])


def jellyfish_dump(index_file: str, output_file: str):
    call(["jellyfish", "dump",
          index_file,
          "-o", output_file
          ])


@functools.lru_cache(maxsize=32)
def load_kmer_index(counter_file: str) -> Counter:
    # print("Loading", counter_file)
    counter = Counter()
    seqs = SeqIO.parse(open(counter_file), "fasta")
    for seq_record in seqs:
        count, sequence = seq_record.id, str(seq_record.seq)
        counter[sequence] = int(count)

    return counter


def kmerize_samples(sample_files: list, tempdir: str,
                    kmer_size: int, njobs: int) -> Mapping:

    mapping = dict()
    for sample_file in sample_files:
        shortname = os.path.split(sample_file)[1]
        sample_name, _ = os.path.splitext(shortname)
        output_jf_file = os.path.join(tempdir, sample_name + ".jf")

        if not os.path.exists(output_jf_file):
            # Jellyfish count
            tables_count = 10
            hash_size = "100M"
            thread_num = njobs
            jellyfish_count(sample_file, kmer_size, tables_count, hash_size,
                            thread_num, output_jf_file)

        output_counter_file = os.path.join(tempdir, sample_name + ".counter")
        if not os.path.exists(output_counter_file):
            # Jellyfish dump
            jellyfish_dump(output_jf_file, output_counter_file)

        mapping[sample_name] = output_counter_file

    return mapping


if __name__ == "__main__":
    pass
