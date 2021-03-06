# -*- coding: utf-8 -*-
#
# File : examples/timeserie_prediction/switch_attractor_esn
# Description : NARMA 30 prediction with ESN.
# Date : 26th of January, 2018
#
# This file is part of EchoTorch.  EchoTorch is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Nils Schaetti <nils.schaetti@unine.ch>

# Imports
import torch.utils.data
import dataset
import echotorch.nn as etnn
from torch.autograd import Variable
import echotorch.utils
import torchlanguage.transforms as transforms
import matplotlib.pyplot as plt
import tools.functions
import tools.settings
import numpy as np
from sklearn.metrics import recall_score, f1_score

# Experiment settings
spectral_radius = 0.95
input_sparsity = 0.1
w_sparsity = 0.2
input_scaling = 0.5
leak_rate = 0.1
n_samples = 20

# Argument
args = tools.functions.argument_parser_training_model()

# Transformer
transformer = transforms.Compose([
    transforms.RemoveLines(),
    transforms.GloveVector(model=tools.settings.lang_models[args.lang])
])

# Results
parameter_averages = np.zeros((4, 4))
parameter_max = np.zeros((4, 4))

# For each reservoir size
for index1, reservoir_size in enumerate([400, 500, 600, 700]):
    # For each number of layer
    for index2, n_layer in enumerate(np.arange(1, 5)):
        # Log
        print(u"Testing Stacked-ESN with {} layers of size {}".format(n_layer, reservoir_size))

        # For each sample
        for n in range(n_samples):
            # Create W matrix
            w = etnn.StackedESN.generate_ws(n_layer, reservoir_size, w_sparsity)

            # Sample average
            single_sample_average = np.array([])

            #  For each problem
            for problem in np.arange(1, 3):
                # Truth and prediction
                y_true = np.array([])
                y_pred = np.array([])

                # Author identification training dataset
                pan18loader_training = torch.utils.data.DataLoader(
                    dataset.AuthorIdentificationDataset(root="./data/", download=True, transform=transformer, problem=problem, lang=args.lang),
                    batch_size=1, shuffle=True
                )

                # Author identification test dataset
                pan18loader_test = torch.utils.data.DataLoader(
                    dataset.AuthorIdentificationDataset(root="./data/", download=True, transform=transformer, problem=problem, train=False, lang=args.lang),
                    batch_size=1, shuffle=True
                )

                # Authors
                author_to_idx = dict()
                for idx, author in enumerate(pan18loader_training.dataset.authors):
                    author_to_idx[author] = idx
                # end for

                # Number of authors
                n_authors = len(author_to_idx)

                # Leaky rates
                if n_layer == 1:
                    leaky_rates = leak_rate
                else:
                    leaky_rates = np.linspace(1.0, leak_rate, n_layer).tolist()
                # end if

                # ESN cell
                esn = etnn.StackedESN(
                    input_dim=transformer.transforms[1].input_dim,
                    hidden_dim=[reservoir_size] * n_layer,
                    output_dim=n_authors,
                    spectral_radius=spectral_radius,
                    sparsity=input_sparsity,
                    input_scaling=input_scaling,
                    w_sparsity=w_sparsity,
                    learning_algo='inv',
                    leaky_rate=leaky_rates
                )

                # Get training data for this fold
                for i, data in enumerate(pan18loader_training):
                    # Inputs and labels
                    inputs, labels = data

                    # Create time labels
                    author_id = author_to_idx[labels[0]]
                    tag_vector = torch.zeros(1, inputs.size(1), n_authors)
                    tag_vector[0, :, author_id] = 1.0

                    # To variable
                    inputs, time_labels = Variable(inputs), Variable(tag_vector)

                    # Accumulate xTx and xTy
                    hidden_states = esn(inputs, time_labels)
                # end for

                # Finalize training
                esn.finalize()

                # Counters
                successes = 0.0
                count = 0.0

                # Get test data
                for i, data in enumerate(pan18loader_test):
                    # Inputs and labels
                    inputs, labels = data

                    # Author id
                    author_id = author_to_idx[labels[0]]

                    # To variable
                    inputs, label = Variable(inputs), Variable(torch.LongTensor([author_id]))

                    # Predict
                    y_predicted = esn(inputs)

                    # Normalized
                    y_predicted -= torch.min(y_predicted)
                    y_predicted /= torch.max(y_predicted) - torch.min(y_predicted)

                    # Sum to one
                    sums = torch.sum(y_predicted, dim=2)
                    for t in range(y_predicted.size(1)):
                        y_predicted[0, t, :] = y_predicted[0, t, :] / sums[0, t]
                    # end for

                    # Max average through time
                    y_predicted = echotorch.utils.max_average_through_time(y_predicted, dim=1)

                    # Add to array
                    y_true = np.append(y_true, int(label[0]))
                    y_pred = np.append(y_pred, int(y_predicted[0]))
                # end for

                # F1
                sample_f1_score = f1_score(y_true, y_pred, average='macro')

                # Save result
                single_sample_average = np.append(single_sample_average, [sample_f1_score])

                # Reset ESN
                esn.reset()
            # end for

            # Save results
            samples_f1_score = np.average(single_sample_average)

            # Save results
            parameter_averages[index1, index2] += samples_f1_score
            if samples_f1_score > parameter_max[index1, index2]:
                parameter_max[index1, index2] = samples_f1_score
            # end if
        # end for

        # Division
        parameter_averages[index1, index2] /= n_samples

        # Show result
        print(u"\tMacro average F1 score for reservoir size {} and {} layers : {} (max {})".format(
            reservoir_size,
            n_layer,
            parameter_averages[index1, index2],
            parameter_max[index1, index2]
        ))
    # end for
# end for

