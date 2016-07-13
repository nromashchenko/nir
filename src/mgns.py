#!/usr/bin/env python3

import click
import os
import pickle
from bunch import Bunch
import json

import testing
import distance as mdist
import lib.prebuild as pre
import lib.iof as iof
import lib.vptree as vptree


class Config(Bunch):
    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)
        self.temp = Bunch()
        self.temp.config_path = '.mgns.config'

    def load(self, workon: str):
        self.workon = iof.make_sure_exists(workon)
        if iof.exists(self.temp.config_path):
            with open(self.temp.config_path) as data_file:
                loaded_dict = json.load(data_file)
                self.update(loaded_dict)

    def save(self):
        config_path = self.temp.config_path
        del self.temp

        with open(config_path, "w") as f:
            print("", json.dumps(self), file=f)


pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option('--workon', default='./.mgns/')
@click.option('--force', '-f', is_flag=True,
              help='Force overwrite output directory')
@click.option('--quiet', '-q', is_flag=True, help='Be quiet')
@pass_config
def cli(config, workon, force, quiet):
    config.load(workon)
    config.temp.force = force
    config.temp.quiet = quiet


@cli.command()
@click.argument('input_dirs', type=click.Path(exists=True), nargs=-1,
                required=True)
@click.option('--single-file', '-f', is_flag=True,
              help='A single file containing reads for all samples')
@click.option('--kmer_size', '-k', type=int, help='K-mer size',
              default=50, required=True)
@click.option('--distance', '-d', type=click.Choice(mdist.distances.keys()),
              default='jsd', help='A distance metric')
@pass_config
def dist(config, input_dirs, single_file, kmer_size, distance):
    if single_file:
        input_file = input_dirs[0]
        input_dir = pre.split(config, input_file)
        input_dirs = [input_dir]
    else:
        input_dirs = [iof.normalize(d) for d in input_dirs]

    mdist.run(config, input_dirs, kmer_size, distance)
    config.save()


@cli.command()
@click.option('--pwmatrix', '-m', type=click.Path(exists=True),
              help='A distance matrix file', required=True)
@click.option('--test-size', type=float, default=0.0)
@click.option('--coord-system', '-c', type=click.Path(exists=True),
              required=True)
@click.option('--distance', '-d', type=click.Choice(mdist.distances.keys()),
              default='jsd', help='A distance metric')
@pass_config
def build(config, pwmatrix, test_size, coord_system, distance):
    input_file = pwmatrix
    labels, pwmatrix = iof.read_distance_matrix(input_file)
    cs_system = iof.read_coords(coord_system)
    vptree.dist(config, cs_system, labels, pwmatrix,
                test_size, distance)


@cli.command()
@click.argument('input_dirs', type=click.Path(exists=True), nargs=-1,
                required=True)
@click.option('--single-file', '-f', is_flag=True,
              help='A single file containing reads for all samples')
@click.option('--max-samples', '-n', type=int,
              help='Max count of samples to analyze')
@click.option('--min', type=int, default=109,
              help='Minimum read length')
@click.option('--cut', type=int, default=208)
@click.option('--threshold', type=int, default=5000,
              help='Required read count per sample')
@pass_config
def filter(config, input_dirs, single_file, max_samples,
           min, cut, threshold):
    if config.temp.force:
        iof.clear_dir(config.workon)

    filtered_dirs = pre.filter_reads(config, input_dirs,
                                     min, None, cut, threshold)

    if max_samples:
        if single_file:
            raise NotImplementedError(
                "--single-file is not implemented yet")
        else:
            pre.rarefy(config, filtered_dirs, max_samples)


@cli.command()
@click.option('--dist', '-d', type=click.Choice(mdist.distances.keys()),
              default='jsd')
@click.option('--unifrac-file', '-f', type=click.Path(exists=True),
              required=True)
@pass_config
def test(config, dist, unifrac_file):
    dist_tree_file = os.path.join(config.workon,
                                  dist + '_tree.p')
    dist_train_file = os.path.join(config.workon,
                                   dist + '_train.p')

    with open(dist_tree_file, 'rb') as treef:
        dist_tree = pickle.load(treef)

    with open(dist_train_file, 'rb') as trainf:
        train_labels = pickle.load(trainf)

    labels, pwmatrix = iof.read_distance_matrix(unifrac_file)
    k_values = range(3, len(train_labels))

    testing.dist(config, dist_tree, train_labels, labels,
                 pwmatrix, k_values, 'dist.txt')
    testing.baseline(config, dist_tree, train_labels,
                     labels, pwmatrix, k_values)


@cli.command()
@pass_config
def learn(config):
    # TODO:
    # 1. make sure there is proper qiime output files
    # 2. make sure there is a pwmatrix file
    # 3. run a network

    raise NotImplementedError("Not implemented yet")


@cli.command()
@pass_config
def search(config):
    # TODO:
    # 1. make sure there is a pwmatrix file (result of nns build)
    # 2. make sure there is a result from nns learn (k value)
    # 2. run vptree.py (search)
    raise NotImplementedError("Not implemented yet")


@cli.command()
@click.argument('name', type=str, required=True)
@pass_config
def init(config: Config, name: str):
    index_path = os.path.join(config.workon, name)
    iof.make_sure_exists(index_path)


@cli.command()
@click.argument('name', type=str, required=True)
@pass_config
def use(config: Config, name: str):
    index_path = os.path.join(config.workon, name)
    if not iof.exists(index_path):
        print('No such index:', name)

    config.current_index = index_path
    config.flush()


if __name__ == "__main__":
    pass
