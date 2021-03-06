# -*- coding: utf-8 -*-
#

# Imports
from torch.utils.data.dataset import Dataset
import urllib
import os
import zipfile
import json
import codecs


# TIRA Author identification data set
class TIRAAuthorIdentificationDataset(Dataset):
    """
    TIRA Author identification data set
    """

    # Constructor
    def __init__(self, root, problem_name, transform, train, encoding):
        """
        Constructor
        :param root:
        :param problem_name:
        """
        # Properties
        self.root = root
        self.problem_name = problem_name
        self.transform = transform
        self.authors = list()
        self.last_text = ""
        self.n_authors = 0
        self.train = train
        self.encoding = encoding

        # List of text
        self.texts = list()

        # Generate data set
        self._load()
    # end if

    ##############################################
    # Static
    ##############################################

    # Get collection info
    @staticmethod
    def collection_infos(root):
        """
        Get collection info
        :return:
        """
        return json.load(open(os.path.join(root, "collection-info.json"), 'r'))
    # end colelction_infos

    ##############################################
    # OVERRIDE
    ##############################################

    # Length
    def __len__(self):
        """
        Length
        :return:
        """
        return len(self.texts)
    # end __len__

    # Get item
    def __getitem__(self, item):
        """
        Get item
        :param item:
        :return:
        """
        # Current file
        text_path, author_name = self.texts[item]
        self.last_text = text_path[text_path.rfind('/')+1:]

        # Read text
        text_content = codecs.open(text_path, 'r', encoding=self.encoding).read()

        # Transformed
        transformed = self.transform(text_content)

        # Unsqueeze
        transformed = transformed.squeeze(0)

        # Transform
        if self.transform is not None:
            return transformed, author_name
        else:
            return text_content, author_name
        # end if
    # end __getitem__

    ################################################
    # PRIVATE
    ################################################

    # Load dataset
    def _load(self):
        """
        Load the dataset
        :return:
        """
        # Load problem info
        problem_info = json.load(open(os.path.join(self.root, self.problem_name, "problem-info.json")))

        # Info
        unknown_folder = problem_info['unknown-folder']
        candidate_authors = problem_info['candidate-authors']

        # Load texts
        if self.train:
            self.n_authors = len(candidate_authors)

            # Load candidate texts
            for candidate_author in candidate_authors:
                # Author name
                author_name = candidate_author['author-name']

                # Add  to authors
                if author_name not in self.authors:
                    self.authors.append(author_name)
                # end if

                # For each text
                for file_path in os.listdir(os.path.join(self.root, self.problem_name, author_name)):
                    # Add with author name
                    self.texts.append((os.path.join(self.root, self.problem_name, author_name, file_path), author_name))
                # end for
            # end for
        else:
            # For each test files
            for unknown_file in os.listdir(os.path.join(self.root, self.problem_name, unknown_folder)):
                # Add with author name
                self.texts.append((os.path.join(self.root, self.problem_name, unknown_folder, unknown_file), ""))
            # end for
        # end if
    # end _load

# end TIRAAuthorIdentificationDataset
