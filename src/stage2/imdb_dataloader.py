"""
Dataloader for rnn_cnn_imdb and BiGRU
We will also call this file when loading test data
"""
import os
import glob
import io

'''
Code provided to get the IMDB dataset required for the functions
rnn_cnn_imdb.py, BiGRU.py
'''

from torchtext import data


class IMDB(data.Dataset):
    name = 'imdb'
    dirname = 'aclImdb'

    def __init__(self, path, text_field, label_field, **kwargs):
        fields = [('text', text_field), ('label', label_field)]
        examples = []

        for label in ['pos', 'neg']:
            for fname in glob.iglob(os.path.join(path, label, '*.txt')):
                with io.open(fname, 'r', encoding="utf-8") as f:
                    text = f.readline()
                examples.append(data.Example.fromlist([text, label], fields))

        super(IMDB, self).__init__(examples, fields, **kwargs)

    @classmethod
    def splits(cls, text_field, label_field, root='../../data',
               train=None, test=None, validation=None, **kwargs):
        return super(IMDB, cls).splits(
            root=root, text_field=text_field, label_field=label_field,
            train=train, validation=validation, test=test, **kwargs)
