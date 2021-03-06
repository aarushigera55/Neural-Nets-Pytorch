#!/usr/bin/env python3
"""
rnn_cnn_imdb.py
"""

import numpy as np

import torch
import torch.nn as tnn
import torch.optim as topti

from torchtext import data
from torchtext.vocab import GloVe
from src.stage2.imdb_dataloader import IMDB

# Class for creating the neural network.
class NetworkLstm(tnn.Module):

    def __init__(self):
        super(NetworkLstm, self).__init__()

        self.lstm = tnn.LSTM(input_size=50, hidden_size=100, num_layers=1, batch_first=True)
        self.fc1 = tnn.Linear(in_features=100, out_features=64)
        self.fc2 = tnn.Linear(in_features=64, out_features=1)

    def forward(self, input, length):
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        h0 = torch.zeros(1, input.size(0), 100).to(device)
        c0 = torch.zeros(1, input.size(0), 100).to(device)

        output, (hn, cn) = self.lstm(input, (h0, c0))

        output = torch.nn.functional.relu(self.fc1(output[:, -1, :]))
        output = self.fc2(output)

        return output.squeeze()


# Class for creating the neural network.
class NetworkCnn(tnn.Module):

    def __init__(self):
        super(NetworkCnn, self).__init__()
        """
        TODO:
        Create and initialise weights and biases for the layers.
        """
        self.conv1 = tnn.Conv1d(in_channels=50, kernel_size=8, padding=5, out_channels=50)
        self.conv2 = tnn.Conv1d(in_channels=50, kernel_size=8, padding=5, out_channels=50)
        self.conv3 = tnn.Conv1d(in_channels=50, kernel_size=8, padding=5, out_channels=50)

        self.maxpool1 = tnn.MaxPool1d(4)
        self.maxpool2 = tnn.MaxPool1d(4)
        self.maxpool3 = tnn.AdaptiveMaxPool1d(1)

        self.fc1 = tnn.Linear(50, 1)

    def forward(self, input, length):
        x = torch.transpose(input, 1, 2)

        x = torch.relu(self.conv1(x))
        x = self.maxpool1(x)

        x = torch.relu(self.conv2(x))
        x = self.maxpool2(x)

        x = torch.relu(self.conv3(x))
        x = self.maxpool3(x)

        x = self.fc1(x.squeeze())
        return x.squeeze()


def lossFunc():
    return tnn.BCEWithLogitsLoss()


def measures(outputs, labels):
    # Convert to numpy
    outputs = np.round(torch.sigmoid(outputs).cpu().numpy())
    labels = labels.cpu().numpy()

    true_positive = np.sum(np.logical_and(labels == 1, outputs == 1))
    false_positive = np.sum(np.logical_and(labels == 0, outputs == 1))
    false_negative = np.sum(np.logical_and(labels == 1, outputs == 0))
    true_negative = np.sum(np.logical_and(labels == 0, outputs == 0))

    return true_positive, true_negative, false_positive, false_negative


def main():
    # Use a GPU if available, as it should be faster.
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print("Using device: " + str(device))

    textField = data.Field(lower=True, include_lengths=True, batch_first=True)
    labelField = data.Field(sequential=False)

    train, dev = IMDB.splits(textField, labelField, train="train", validation="dev")

    textField.build_vocab(train, dev, vectors=GloVe(name="6B", dim=50))
    labelField.build_vocab(train, dev)

    trainLoader, testLoader = data.BucketIterator.splits((train, dev), shuffle=True, batch_size=64,
                                                         sort_key=lambda x: len(x.text), sort_within_batch=True)

    # Create an instance of the network in memory (potentially GPU memory). Can change to NetworkCnn during development.
    net = NetworkCnn().to(device)

    criterion = lossFunc()
    optimiser = topti.Adam(net.parameters(), lr=0.001)  # Minimise the loss using the Adam algorithm.

    for epoch in range(10):
        running_loss = 0

        for i, batch in enumerate(trainLoader):
            # Get a batch and potentially send it to GPU memory.
            inputs, length, labels = textField.vocab.vectors[batch.text[0]].to(device), batch.text[1].to(
                device), batch.label.type(torch.FloatTensor).to(device)

            labels -= 1
            optimiser.zero_grad()

            # Forward pass through the network.
            output = net(inputs, length)

            loss = criterion(output, labels)

            # Calculate gradients.
            loss.backward()

            # Minimise the loss according to the gradient.
            optimiser.step()

            running_loss += loss.item()

            if i % 32 == 31:
                print("Epoch: %2d, Batch: %4d, Loss: %.3f" % (epoch + 1, i + 1, running_loss / 32))
                running_loss = 0

    true_pos, true_neg, false_pos, false_neg = 0, 0, 0, 0

    # Evaluate network on the test dataset.  We aren't calculating gradients, so disable autograd to speed up
    # computations and reduce memory usage.
    with torch.no_grad():
        for batch in testLoader:
            inputs, length, labels = textField.vocab.vectors[batch.text[0]].to(device), batch.text[1].to(
                device), batch.label.type(torch.FloatTensor).to(device)

            labels -= 1

            outputs = net(inputs, length)

            tp_batch, tn_batch, fp_batch, fn_batch = measures(outputs, labels)
            true_pos += tp_batch
            true_neg += tn_batch
            false_pos += fp_batch
            false_neg += fn_batch

    accuracy = 100 * (true_pos + true_neg) / len(dev)
    matthews = MCC(true_pos, true_neg, false_pos, false_neg)

    print("Classification accuracy: %.2f%%\n"
          "Matthews Correlation Coefficient: %.2f" % (accuracy, matthews))


# Matthews Correlation Coefficient calculation.
def MCC(tp, tn, fp, fn):
    numerator = tp * tn - fp * fn
    denominator = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5

    with np.errstate(divide="ignore", invalid="ignore"):
        return np.divide(numerator, denominator)


if __name__ == '__main__':
    main()
